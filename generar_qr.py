"""Genera el QR de la última diapositiva con los colores y el icono de Tairel.

    python generar_qr.py https://demo.taireldata.com

Crea qr_demo.png (para la diapositiva y para imprimir en el stand).
"""

import sys
from pathlib import Path

import qrcode
from PIL import Image, ImageDraw
from qrcode.constants import ERROR_CORRECT_H

RAIZ = Path(__file__).parent


def main(url: str, salida: str = "qr_demo.png") -> None:
    qr = qrcode.QRCode(error_correction=ERROR_CORRECT_H, box_size=24, border=3)
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#0054a4", back_color="white").convert("RGBA")

    icono = RAIZ / "assets" / "icono.png"
    if icono.exists():  # la corrección H tolera tapar el centro
        lado = img.size[0] // 5
        ic = Image.open(icono).convert("RGBA").resize((lado, lado))
        marco = Image.new("RGBA", (lado + 24, lado + 24), (0, 0, 0, 0))
        ImageDraw.Draw(marco).rounded_rectangle([0, 0, lado + 23, lado + 23], radius=36, fill="white")
        marco.paste(ic, (12, 12), ic)
        pos = ((img.size[0] - marco.size[0]) // 2, (img.size[1] - marco.size[1]) // 2)
        img.paste(marco, pos, marco)

    img.convert("RGB").save(salida)
    print(f"QR guardado en {salida} -> {url}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit("Uso: python generar_qr.py <url-de-la-demo>")
    main(sys.argv[1])
