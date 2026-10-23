/*
 * motor.js — Motor de previsión que se ejecuta en el navegador.
 *
 * Reproduce exactamente las fórmulas de scripts/comun.py y aplica los
 * coeficientes entrenados en scripts/2_entrenar_modelo.py (window.MODELO).
 * Una simulación completa (52 semanas, todos los submodelos) tarda < 1 ms,
 * por eso los sliders recalculan en tiempo real.
 *
 * Funciona en navegador (window.Motor) y en Node (module.exports) para las pruebas.
 */
(function (root) {
  'use strict';

  // ---- Constantes (idénticas a comun.py) ---------------------------------
  const UMBRAL_CALOR = 26.0;
  const ENERGIA_REF = 120.0;
  const T0 = Date.UTC(2022, 0, 1);
  const DIA = 86400000;

  // Perfil de la "ola de calor" del simulador por semana ISO (jun-ago)
  const PERFIL_OLA = { 25: 0.3, 26: 0.6, 27: 0.85, 28: 1, 29: 1, 30: 1, 31: 1, 32: 0.85, 33: 0.6, 34: 0.3 };

  const PALANCAS_CERO = { calor: 0, lluvia: 0, energia: 0, mp: 0, promo: 0, gasoleo: 0, precio: 0, plaga: 0 };
  // Palanca de escenario (demo Tairel, no está en comun.py): % de cosecha perdida por plagas y enfermedades
  // detectadas en las fotos de los campos. IV gama: más merma en campo; congelado: menos rendimiento
  // de campaña; cereal: menos grano que vender.
  // Palanca de escenario (no está en comun.py): precio de venta. Cuánto volumen se pierde al subirlo
  // depende del negocio; la cooperativa vende todo el grano al precio de lonja (elasticidad 0).
  const ELASTICIDAD_PRECIO = { ivgama: -0.9, congelado: -0.7, cereal: 0 };
  const CATEGORIAS = ['materia_prima', 'energia', 'mano_obra', 'transporte', 'envases', 'mermas'];

  // ---- Utilidades de calendario --------------------------------------------
  function ms(iso) { return Date.parse(iso + 'T00:00:00Z'); }
  function diaDelAnio(iso) {
    const d = new Date(ms(iso));
    return Math.round((d - Date.UTC(d.getUTCFullYear(), 0, 1)) / DIA) + 1;
  }
  function anios(iso) { return (ms(iso) - T0) / DIA / 365.25; }
  function semanaISO(iso) {
    const d = new Date(ms(iso));
    const dia = (d.getUTCDay() + 6) % 7;
    d.setUTCDate(d.getUTCDate() - dia + 3);
    const primerJueves = new Date(Date.UTC(d.getUTCFullYear(), 0, 4));
    return 1 + Math.round(((d - primerJueves) / DIA - 3 + ((primerJueves.getUTCDay() + 6) % 7)) / 7);
  }

  // ---- Clima normal (idéntico a comun.py) ----------------------------------
  const tempClima = (doy) => 14.8 - 9.5 * Math.cos(2 * Math.PI * (doy - 20) / 365.25);
  const lluviaClima = (doy) => 7.7 * (1 + 0.45 * Math.cos(2 * Math.PI * (doy - 110) / 365.25));
  const pesoVerano = (doy) => Math.max(0, Math.cos(2 * Math.PI * (doy - 200) / 365.25));

  /*
   * Construye las features de las semanas de `ex` (arrays de igual longitud),
   * usando `ex.cola` (25 semanas previas) para las medias móviles de 26 semanas.
   * ex = { doy, t, temp, lluvia, energia, gasoleo, promo, cola: {doy, temp, lluvia} }
   */
  function construirFeatures(ex) {
    const n = ex.doy.length, c = ex.cola, nc = c.doy.length;
    const tempAll = c.temp.concat(ex.temp);
    const llAll = c.lluvia.concat(ex.lluvia);
    const doyAll = c.doy.concat(ex.doy);
    const calorAll = tempAll.map((x) => Math.max(0, x - UMBRAL_CALOR));
    const out = new Array(n);
    for (let i = 0; i < n; i++) {
      const j = i + nc;
      const desde = Math.max(0, j - 25);
      let sl = 0, slc = 0, sc = 0;
      for (let k = desde; k <= j; k++) { sl += llAll[k]; slc += lluviaClima(doyAll[k]); sc += calorAll[k]; }
      const doy = ex.doy[i];
      const ang = 2 * Math.PI * doy / 365.25;
      const temp = ex.temp[i];
      const anom = temp - tempClima(doy);
      const f = {
        const: 1, t: ex.t[i],
        anomT: anom, anomT_ver: anom * pesoVerano(doy), wver: pesoVerano(doy),
        calor: Math.max(0, temp - UMBRAL_CALOR), tpos: Math.max(0, temp - 15),
        seq: Math.min(0.7, Math.max(-0.6, 1 - sl / slc)),
        calor26: sc / (j - desde + 1),
        logE: Math.log(ex.energia[i] / ENERGIA_REF),
        diesel: ex.gasoleo[i], promo: ex.promo[i],
      };
      for (let k = 1; k <= 4; k++) { f['s' + k] = Math.sin(k * ang); f['c' + k] = Math.cos(k * ang); }
      out[i] = f;
    }
    return out;
  }

  function aplicar(modelo, f) {
    let y = 0;
    for (let k = 0; k < modelo.feats.length; k++) y += modelo.coef[k] * f[modelo.feats[k]];
    return y;
  }

  function operativas(f, q, vend, merma) {
    const vp = q / (1 - merma);
    return Object.assign({}, f, {
      q: q, vend: vend, vp: vp, vp_tpos: vp * f.tpos, vp_calor: vp * f.calor, q_calor: q * f.calor,
    });
  }

  // ---- Exógenas ------------------------------------------------------------
  function colaDe(M, desde, hasta) {
    const h = M.exog_hist;
    return {
      doy: h.fecha.slice(desde, hasta).map(diaDelAnio),
      temp: h.temp.slice(desde, hasta),
      lluvia: h.lluvia.slice(desde, hasta),
    };
  }

  /* Exógenas de las 52 semanas de previsión bajo unas palancas */
  function exogPrevision(M, est, pal) {
    const b = M.exog_base, nh = M.exog_hist.fecha.length;
    const doy = b.fecha.map(diaDelAnio);
    const promo = est.p.promo_base.slice();
    for (let k = 0; k < Math.round(pal.promo); k++) promo[est.ordenPromo[k]] = 1;
    return {
      fecha: b.fecha, doy: doy, t: b.fecha.map(anios),
      temp: doy.map((d, i) => tempClima(d) + pal.calor * (PERFIL_OLA[est.semanas[i]] || 0)),
      lluvia: doy.map((d) => lluviaClima(d) * (1 + pal.lluvia / 100)),
      energia: b.energia.map((x) => x * (1 + pal.energia / 100)),
      gasoleo: b.gasoleo.map((x) => x * (1 + pal.gasoleo / 100)),
      promo: promo,
      cola: colaDe(M, nh - 25, nh),
    };
  }

  /* Exógenas reales del último año (para comparar con la previsión) */
  function exogUltimoAnio(M, est) {
    const h = M.exog_hist, nh = h.fecha.length, n = M.meta.horizonte;
    const fechas = h.fecha.slice(nh - n);
    return {
      fecha: fechas, doy: fechas.map(diaDelAnio), t: fechas.map(anios),
      temp: h.temp.slice(nh - n), lluvia: h.lluvia.slice(nh - n),
      energia: h.energia.slice(nh - n), gasoleo: h.gasoleo.slice(nh - n),
      promo: est.p.promo_hist.slice(est.p.promo_hist.length - n),
      cola: colaDe(M, nh - n - 25, nh - n),
    };
  }

  /*
   * Simulación de 52 semanas.
   * opts.sinLimites: no aplica capacidad ni stock (para calibrar el estado base)
   */
  function simular(est, ex, pal, opts) {
    opts = opts || {};
    const p = est.p, m = p.modelos, neg = p.negocio, n = ex.doy.length;
    const F = construirFeatures(ex);
    const fmp = 1 + (pal.mp || 0) / 100;
    const fpv = 1 + (pal.precio || 0) / 100, fdem = Math.pow(fpv, ELASTICIDAD_PRECIO[neg] || 0);
    const fpl = Math.min(0.9, Math.max(0, (pal.plaga || 0) / 100));
    const r = {
      demanda: new Array(n), vend: new Array(n), q: new Array(n), pv: new Array(n), pmp: new Array(n),
      merma: new Array(n), ventas: new Array(n), coste: new Array(n), stock: null,
      cat: {}, rend: new Array(n),
    };
    CATEGORIAS.forEach((c) => { r.cat[c] = new Array(n); });

    // 1) Demanda, precios y merma
    for (let i = 0; i < n; i++) {
      const f = F[i];
      r.demanda[i] = Math.exp(aplicar(m.vol, f)) * fdem;
      r.pv[i] = Math.exp(aplicar(m.pv, f)) * fpv;
      // Congelado: las hectáreas contratadas se pagan igual, así que el kilo útil sale más caro
      r.pmp[i] = Math.exp(aplicar(m.pmp, f)) * fmp / (neg === 'congelado' ? 1 - fpl : 1);
      r.merma[i] = Math.min(0.4, Math.max(0.002, aplicar(m.merma, f) + (neg === 'ivgama' ? 0.5 * fpl : 0)));
      if (m.rend) r.rend[i] = Math.exp(aplicar(m.rend, f)) * (neg === 'congelado' ? 1 - fpl : 1);
    }

    // 2) Volumen servido según el tipo de negocio
    if (neg === 'ivgama') {
      const cap = opts.sinLimites ? Infinity : est.capacidad;
      for (let i = 0; i < n; i++) { r.vend[i] = Math.min(r.demanda[i], cap); r.q[i] = r.vend[i]; }
    } else if (neg === 'congelado') {
      // Producción de campaña = plan (fijado al empezar el año) x rendimiento según el clima
      let S = opts.sinLimites ? Infinity : est.stock0;
      r.stock = new Array(n);
      for (let i = 0; i < n; i++) {
        r.q[i] = opts.sinLimites ? 0 : est.plan[i] * r.rend[i];
        const disp = S + r.q[i];
        r.vend[i] = Math.min(r.demanda[i], disp);
        S = disp - r.vend[i];
        r.stock[i] = S;
      }
    } else {
      for (let i = 0; i < n; i++) { r.vend[i] = r.demanda[i] * (1 - fpl); r.q[i] = r.vend[i]; }
    }

    // 3) Costes
    let tv = 0, tc = 0, tt = 0;
    const tot = {}; CATEGORIAS.forEach((c) => { tot[c] = 0; });
    for (let i = 0; i < n; i++) {
      const q = r.q[i], v = r.vend[i], mm = r.merma[i];
      const g = operativas(F[i], q, v, mm);
      const c = {
        materia_prima: p.rf * q * r.pmp[i] * 1000,
        mermas: p.rf * q * mm / (1 - mm) * r.pmp[i] * 1000 * (1 + p.k_proc),
        energia: Math.max(0, aplicar(m.energia, g)) * ex.energia[i],
        mano_obra: Math.max(0, aplicar(m.mano_obra, g)),
        transporte: v * Math.max(0, aplicar(m.transporte, g)),
        envases: v * Math.max(0, aplicar(m.envases, g)),
      };
      let ci = 0;
      CATEGORIAS.forEach((k) => { r.cat[k][i] = c[k]; tot[k] += c[k]; ci += c[k]; });
      r.coste[i] = ci;
      r.ventas[i] = v * r.pv[i] * 1000;
      tv += r.ventas[i]; tc += ci; tt += v;
    }
    // Congelado: la materia prima y las mermas se compran en campaña y van a stock.
    // Para el margen se imputan a lo vendido con el coste medio de la campaña (coste de ventas).
    if (neg === 'congelado' && !opts.sinLimites) {
      const sumQ = r.q.reduce((a, b) => a + b, 0) || 1;
      r.compras = { materia_prima: r.cat.materia_prima.slice(), mermas: r.cat.mermas.slice() };
      ['materia_prima', 'mermas'].forEach((k) => {
        const u = tot[k] / sumQ;
        tot[k] = 0;
        for (let i = 0; i < n; i++) {
          const nuevo = r.vend[i] * u;
          r.coste[i] += nuevo - r.cat[k][i];
          r.cat[k][i] = nuevo; tot[k] += nuevo;
        }
      });
      tc = r.coste.reduce((a, b) => a + b, 0);
    }
    r.tot = {
      ventas: tv, coste: tc, margen: tv - tc, margenPct: tv > 0 ? (tv - tc) / tv * 100 : 0,
      vol: tt, demanda: r.demanda.reduce((a, b) => a + b, 0), cat: tot,
      mermaMedia: r.merma.reduce((a, b, i) => a + b * r.q[i], 0) / Math.max(1, r.q.reduce((a, b) => a + b, 0)),
      pmpMedio: r.pmp.reduce((a, b, i) => a + b * r.q[i], 0) / Math.max(1, r.q.reduce((a, b) => a + b, 0)),
    };
    return r;
  }

  /* Prepara un producto: capacidad, plan de campaña, stock inicial y orden de promos */
  function preparar(M, pid) {
    const p = M.productos[pid];
    const est = { M: M, pid: pid, p: p, semanas: M.exog_base.fecha.map(semanaISO) };
    est.ordenPromo = [];
    const ex0 = exogPrevision(M, Object.assign(est, { ordenPromo: [] }), PALANCAS_CERO);
    const r0 = simular(est, ex0, PALANCAS_CERO, { sinLimites: true });
    // Semanas candidatas a promo extra: las de mayor demanda sin promo ya prevista
    est.ordenPromo = r0.demanda.map((d, i) => [d, i]).filter((x) => !p.promo_base[x[1]])
      .sort((a, b) => b[0] - a[0]).map((x) => x[1]);

    if (p.negocio === 'ivgama') {
      const maxHist = Math.max.apply(null, p.hist_vol);
      const maxBase = Math.max.apply(null, r0.demanda);
      est.capacidad = Math.ceil(Math.max(maxHist * 1.03, maxBase * 1.05) / 10) * 10;
    }
    if (p.negocio === 'congelado') {
      const D = r0.demanda, perfil = p.perfil_campana;
      const denom = perfil.reduce((a, x, i) => a + x * r0.rend[i], 0);
      const k = D.reduce((a, b) => a + b, 0) / denom;
      est.plan = perfil.map((x) => x * k);
      est.seguridad = 3 * D.reduce((a, b) => a + b, 0) / D.length;
      let cum = 0, minCum = 0;
      for (let i = 0; i < D.length; i++) { cum += est.plan[i] * r0.rend[i] - D[i]; minCum = Math.min(minCum, cum); }
      est.stock0 = 1.3 * est.seguridad - minCum;
    }
    est.base = simular(est, exogPrevision(M, est, PALANCAS_CERO), PALANCAS_CERO);
    return est;
  }

  function correr(est, pal) {
    return simular(est, exogPrevision(est.M, est, pal), pal);
  }

  // ---- Explicación: valores de Shapley -------------------------------------
  /* Reparte de forma exacta un cambio entre varios factores (todas las combinaciones). */
  function shapley(nombres, valor) {
    const n = nombres.length, cache = new Map();
    const v = (mask) => { if (!cache.has(mask)) cache.set(mask, valor(mask)); return cache.get(mask); };
    const fact = [1]; for (let i = 1; i <= n; i++) fact[i] = fact[i - 1] * i;
    const phi = {};
    nombres.forEach((nm, i) => {
      let s = 0;
      for (let mask = 0; mask < (1 << n); mask++) {
        if (mask & (1 << i)) continue;
        let k = 0; for (let b = mask; b; b >>= 1) k += b & 1;
        s += fact[k] * fact[n - k - 1] / fact[n] * (v(mask | (1 << i)) - v(mask));
      }
      phi[nm] = s;
    });
    return phi;
  }

  /* ¿Qué palancas mueven el margen (y las ventas) respecto a la previsión base? */
  function explicarEscenario(est, pal) {
    const activas = Object.keys(PALANCAS_CERO).filter((k) => Math.abs(pal[k]) > 1e-9);
    if (!activas.length) return null;
    const res = {};
    const valor = (mask) => {
      const q = Object.assign({}, PALANCAS_CERO);
      activas.forEach((k, i) => { if (mask & (1 << i)) q[k] = pal[k]; });
      const key = JSON.stringify(q);
      if (!res[key]) res[key] = correr(est, q).tot;
      return res[key];
    };
    return {
      margen: shapley(activas, (mk) => valor(mk).margen),
      ventas: shapley(activas, (mk) => valor(mk).ventas),
    };
  }

  /* ¿Por qué la previsión base difiere del último año real? (en ventas €) */
  function explicarFrenteAnioAnterior(est) {
    const M = est.M, fc = exogPrevision(M, est, PALANCAS_CERO), ly = exogUltimoAnio(M, est);
    const grupos = {
      tendencia: ['t'], temperatura: ['temp', 'colaTemp'], lluvia: ['lluvia', 'colaLluvia'],
      energia: ['energia'], promociones: ['promo'],
    };
    const nombres = Object.keys(grupos);
    const mezcla = (mask) => {
      const ex = { doy: fc.doy, t: fc.t, temp: fc.temp, lluvia: fc.lluvia, energia: fc.energia,
        gasoleo: fc.gasoleo, promo: fc.promo, cola: { doy: fc.cola.doy, temp: fc.cola.temp, lluvia: fc.cola.lluvia } };
      const usarLY = (g) => !(mask & (1 << nombres.indexOf(g)));
      if (usarLY('tendencia')) ex.t = ly.t;
      if (usarLY('temperatura')) { ex.temp = ly.temp; ex.cola.temp = ly.cola.temp; }
      if (usarLY('lluvia')) { ex.lluvia = ly.lluvia; ex.cola.lluvia = ly.cola.lluvia; ex.cola.doy = ly.cola.doy; }
      if (usarLY('energia')) ex.energia = ly.energia;
      if (usarLY('promociones')) ex.promo = ly.promo;
      return simular(est, ex, PALANCAS_CERO).tot.ventas;
    };
    const phi = shapley(nombres, mezcla);
    const ajusteLY = mezcla(0);
    phi.otros = ajusteLY - est.p.ultimo_anio.ventas;     // lo que el modelo no explica del año pasado
    return { phi: phi, ventasLY: est.p.ultimo_anio.ventas, ventasBase: est.base.tot.ventas };
  }

  const Motor = {
    PALANCAS_CERO, CATEGORIAS, PERFIL_OLA, ELASTICIDAD_PRECIO,
    diaDelAnio, semanaISO, anios, tempClima, lluviaClima,
    construirFeatures, operativas, aplicar, exogPrevision, exogUltimoAnio,
    simular, preparar, correr, shapley, explicarEscenario, explicarFrenteAnioAnterior,
  };
  if (typeof module !== 'undefined' && module.exports) module.exports = Motor;
  else root.Motor = Motor;
})(typeof window !== 'undefined' ? window : globalThis);
