"""Catálogo de productos de la demo.

Selección pensada para el público del evento: los productos más habituales
del sector hortofrutícola y cerealista navarro (Grupo AN y similares).
Cada producto lleva los criterios que el modelo debe vigilar.
"""

PRODUCTOS = {
    "auto": {
        "nombre": "Detectar automáticamente",
        "icono": "🔍",
        "criterios": (
            "Identifica primero el producto y aplica los criterios de calidad "
            "comerciales habituales para ese producto."
        ),
    },
    "tomate": {
        "nombre": "Tomate",
        "icono": "🍅",
        "criterios": (
            "Color y uniformidad de maduración (verde, pintón, rojo), firmeza aparente, "
            "grietas radiales o concéntricas, podredumbre apical (blossom end rot), "
            "golpes y magulladuras, manchas o daños por plagas, deformaciones, "
            "estado del cáliz. Referencia: normas de comercialización UE (Extra, I, II)."
        ),
    },
    "brocoli": {
        "nombre": "Brócoli",
        "icono": "🥦",
        "criterios": (
            "Compacidad de la pella, color verde uniforme, amarilleamiento de floretes "
            "(senescencia), floretes abiertos o en flor, manchas negras o pardas, "
            "podredumbre, daños por insectos, corte del tallo limpio, tamaño de la pella."
        ),
    },
    "pimiento": {
        "nombre": "Pimiento",
        "icono": "🫑",
        "criterios": (
            "Color y brillo uniformes, firmeza, quemaduras de sol (golpe de sol), "
            "podredumbre apical, arrugas o deshidratación, grietas, daños por plagas, "
            "forma típica de la variedad, estado del pedúnculo. Si es tipo piquillo, "
            "valora su aptitud para conserva (asado y pelado)."
        ),
    },
    "melocoton": {
        "nombre": "Melocotón / nectarina",
        "icono": "🍑",
        "criterios": (
            "Color de fondo y chapa, madurez, golpes y magulladuras, podredumbre "
            "(monilia), heridas, rajado de hueso, daños de granizo, roces de piel, "
            "calibre aparente. Referencia: normas de comercialización UE."
        ),
    },
    "lechuga": {
        "nombre": "Lechuga / hoja (IV gama)",
        "icono": "🥬",
        "criterios": (
            "Turgencia y frescura, color, pardeamiento de bordes (tip burn), "
            "pardeamiento en cortes, hojas amarillas o necrosadas, podredumbre, "
            "presencia de insectos o cuerpos extraños, aptitud para IV gama."
        ),
    },
    "cereal": {
        "nombre": "Cereal en grano (trigo, maíz, cebada)",
        "icono": "🌾",
        "criterios": (
            "Homogeneidad del grano, granos partidos, granos germinados, granos "
            "atacados por insectos, presencia de hongos o granos con micotoxinas "
            "aparentes (ennegrecidos, rosados), impurezas y materias extrañas "
            "(piedras, paja, semillas de malas hierbas), color y brillo."
        ),
    },
}

CATEGORIAS = ["Extra", "I", "II", "Destrío", "No evaluable"]

COLOR_CATEGORIA = {
    "Extra": "#1a8f4c",
    "I": "#0168cb",
    "II": "#e0a100",
    "Destrío": "#c62828",
    "No evaluable": "#6b6b6b",
}

TEXTO_CATEGORIA = {
    "Extra": "Calidad Extra",
    "I": "Categoría I",
    "II": "Categoría II",
    "Destrío": "Destrío",
    "No evaluable": "No evaluable",
}
