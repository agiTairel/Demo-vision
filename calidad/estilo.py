"""Estilos comunes de la app (paleta agro de Tairel)."""

CSS = """
<link href="https://fonts.googleapis.com/css2?family=Figtree:wght@400;500;600;700;800&family=Archivo:wdth,wght@62..125,600..900&display=swap" rel="stylesheet">
<style>
:root{
  --suelo:#fbfbf6; --blanco:#ffffff; --panel:#eef3e6; --panel-linea:#d3dcc5;
  --linea:#e2e6d8; --linea-2:#cbd3c0; --linea-3:#eaede3;
  --tinta:#1f2a1f; --tinta-2:#4a5648; --tinta-3:#566354;
  --hoja:#2f7d32; --hoja-suave:#e2efd8; --trigo:#e2ac24;
  --ok:#2a7230; --mal:#b3361f; --aviso:#9a6a00; --info:#25689f; --rojo:#c23a22;
  --f:'Figtree',system-ui,sans-serif;
  --f-cifra:'Archivo','Arial Narrow',sans-serif;
}
html, body, [class*="css"], .stMarkdown, button, input, label, p, li { font-family:var(--f) !important; }
.stApp{background:var(--suelo);}
#MainMenu, footer, header[data-testid="stHeader"] {visibility:hidden; height:0;}
.block-container{padding-top:1rem; padding-bottom:3rem; max-width:760px;}
.cifra{font-family:var(--f-cifra) !important;font-stretch:76%;font-weight:800;}
.hero{background:linear-gradient(135deg,#1f5e22 0%,var(--hoja) 55%,#4f9a3a 100%);
  color:#fff;border-radius:22px;padding:22px 22px 20px;margin:6px 0 18px;position:relative;overflow:hidden;}
.hero:after{content:"";position:absolute;right:-40px;top:-40px;width:170px;height:170px;border-radius:50%;
  background:radial-gradient(circle,rgba(226,172,36,.6),rgba(226,172,36,0) 70%);}
.hero h1{font-size:1.65rem;line-height:1.15;margin:0 0 6px;font-weight:800;color:#fff;}
.hero p{margin:0;opacity:.94;font-size:1rem;}
.chip{display:inline-block;background:rgba(255,255,255,.18);border-radius:999px;padding:3px 10px;
  font-size:.78rem;font-weight:700;letter-spacing:.03em;margin-bottom:10px;}
.paso{font-weight:800;color:var(--hoja);font-size:1.05rem;margin:14px 0 4px;}
.paso span{display:inline-flex;width:24px;height:24px;border-radius:50%;background:var(--trigo);color:var(--tinta);
  align-items:center;justify-content:center;font-size:.85rem;margin-right:8px;}
.tarjeta{background:var(--blanco);border:1px solid var(--linea);border-radius:18px;padding:16px 18px;margin:10px 0;color:var(--tinta);}
.veredicto{border-radius:18px;padding:18px;color:#fff;margin:10px 0 6px;}
.veredicto .cat{font-family:var(--f-cifra) !important;font-stretch:76%;font-size:2.2rem;font-weight:800;line-height:1.05;}
.veredicto .prod{opacity:.95;font-weight:600;margin-top:2px;}
.veredicto .dest{margin-top:10px;background:rgba(255,255,255,.2);display:inline-block;border-radius:999px;
  padding:4px 12px;font-weight:700;font-size:.9rem;}
.kpis{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin:10px 0;}
.kpi{background:var(--blanco);border:1px solid var(--linea);border-radius:16px;padding:12px 10px;text-align:center;}
.kpi .v{font-family:var(--f-cifra) !important;font-stretch:76%;font-weight:800;font-size:1.9rem;color:var(--hoja);line-height:1.05;}
.kpi .l{font-size:.78rem;color:var(--tinta-3);font-weight:600;margin-top:2px;}
.kpi .s{font-size:.8rem;color:var(--tinta);font-weight:700;}
.barra{height:10px;border-radius:999px;background:var(--linea-3);overflow:hidden;margin:6px 0 2px;}
.barra > div{height:100%;border-radius:999px;background:linear-gradient(90deg,var(--trigo),var(--hoja));}
.h3{font-weight:800;color:var(--tinta);font-size:1.02rem;margin-bottom:8px;}
.defecto{border-left:5px solid var(--linea-2);padding:8px 12px;margin:8px 0;background:var(--panel);border-radius:0 12px 12px 0;color:var(--tinta);}
.defecto .t{font-weight:800;color:var(--tinta);}
.defecto .m{font-size:.82rem;color:var(--tinta-3);}
.sev{font-size:.72rem;font-weight:800;text-transform:uppercase;border-radius:999px;padding:2px 8px;color:#fff;margin-left:6px;}
.paleta{display:flex;height:34px;border-radius:10px;overflow:hidden;margin:8px 0 4px;border:1px solid var(--linea);}
.nota{font-size:.78rem;color:var(--tinta-3);}
.aviso{background:#fbf3dc;border:1px solid #ecd28a;color:var(--tinta);border-radius:14px;padding:10px 14px;font-size:.9rem;margin:8px 0;}
.cta{background:linear-gradient(135deg,var(--tinta) 0%,#244a26 60%,var(--hoja) 100%);color:#fff;border-radius:22px;padding:22px;margin:22px 0 10px;}
.cta h3{color:#fff;margin:0 0 8px;font-weight:800;font-size:1.3rem;}
.cta ul{margin:8px 0 0 0;padding-left:18px;} .cta li{margin:4px 0;color:#fff;}
.cta li::marker{color:var(--trigo);}
.pie{text-align:center;color:var(--tinta-3);font-size:.78rem;margin-top:24px;}
div.stButton > button[kind="primary"], a[data-testid="stBaseLinkButton-primary"]{background:var(--hoja);border-color:var(--hoja);color:#fff;border-radius:14px;
  font-weight:800;padding:.65rem 1rem;font-size:1.05rem;}
div.stButton > button[kind="primary"]:hover{background:var(--ok);border-color:var(--ok);}
div.stButton > button{border-radius:12px;font-weight:700;border-color:var(--linea-2);}
[data-testid="stFileUploaderDropzone"]{border-radius:16px;border:2px dashed var(--linea-2);background:var(--panel);}
img{border-radius:14px;}
</style>
"""
