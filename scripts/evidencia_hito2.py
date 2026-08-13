# -*- coding: utf-8 -*-
"""
evidencia_hito2.py (Sala 2 - Hito 2)
------------------------------------
Genera la evidencia para el informe:
  1. Metricas de "coherencia del Top 5": fraccion de resultados que comparten
     la misma familia de diseno (prefijo AIM-PXXX) con el diseno correcto.
  2. Montajes antes/despues para consultas representativas
     (consulta original | consulta preparada | mejor resultado Hito 2).

Salidas:
    data/evidencia_coherencia_hito2.txt
    data/montajes/*.png

Uso (desde la raiz del repositorio, con la venv activa):
    python scripts/evidencia_hito2.py
"""

import os
import sys

import numpy as np
import pandas as pd
from PIL import Image, ImageDraw, ImageFont

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, BASE_DIR)

from api.preprocesar_consulta import preparar_consulta  # noqa: E402

CONSULTAS = os.path.join(BASE_DIR, "data", "consultas")
IMGS = os.path.join(BASE_DIR, "data", "images_final")
RES_CSV = os.path.join(BASE_DIR, "data", "resultados_hito2.csv")
MONT_OUT = os.path.join(BASE_DIR, "data", "montajes")
EVIDENCIA_TXT = os.path.join(BASE_DIR, "data", "evidencia_coherencia_hito2.txt")

EJEMPLOS = [
    # ids correctos verificados por hash perceptual (cXX = AIM-P001-XXX en
    # orden): c01=AIM-P001-013, c03=AIM-P001-015, c04=AIM-P001-016,
    # c07=AIM-P001-003. NO usar PATRONES antiguos (AIM-P001-001/-025/-040/...).
    ("c01_recoloreado.jpeg", "recoloreada", "AIM-P001-013"),
    ("c04_recorte.jpg", "recortada", "AIM-P001-016"),
    ("c03_sin_marco.jpg", "sin_marco", "AIM-P001-015"),
    ("c01_cuerpo.jpeg", "persona", "AIM-P001-013"),
    ("c07_recoloreado.jpeg", "recoloreada", "AIM-P001-003"),
]


def _font(tamano):
    try:
        return ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", tamano)
    except Exception:
        return ImageFont.load_default()


def familia(cid):
    return cid.split("-")[0] + "-" + cid.split("-")[1]


def main():
    res = pd.read_csv(RES_CSV)
    res["familia"] = res["correcto_id"].apply(familia)
    res["t5o"] = res["top5_original"].str.split("|")
    res["t5p"] = res["top5_procesada"].str.split("|")
    res["coh_o"] = res.apply(lambda r: np.mean([familia(x) == r["familia"] for x in r["t5o"]]), axis=1)
    res["coh_p"] = res.apply(lambda r: np.mean([familia(x) == r["familia"] for x in r["t5p"]]), axis=1)

    lineas = []
    lineas.append("COHERENCIA DEL TOP 5 (proporcion de resultados de la misma familia de diseno)")
    lineas.append("")
    lineas.append(f"{'Categoria':<14}{'Hito 1':>10}{'Hito 2':>10}")
    for cat, g in res.groupby("categoria"):
        lineas.append(f"{cat:<14}{100*g['coh_o'].mean():>9.0f}%{100*g['coh_p'].mean():>10.0f}%")
    lineas.append(f"{'TOTAL':<14}{100*res['coh_o'].mean():>9.0f}%{100*res['coh_p'].mean():>10.0f}%")
    texto = "\n".join(lineas)
    print(texto)
    with open(EVIDENCIA_TXT, "w", encoding="utf-8") as f:
        f.write(texto)

    os.makedirs(MONT_OUT, exist_ok=True)

    for archivo, cat, correcto in EJEMPLOS:
        fila = res[res["archivo"] == archivo].iloc[0]
        consulta = Image.open(os.path.join(CONSULTAS, archivo)).convert("RGB")
        preparada = preparar_consulta(consulta)["procesada"]
        top1_proc = fila["top1_procesada"]
        img_db = os.path.join(IMGS, top1_proc + ".jpg")
        ancho = 90
        piezas = [
            consulta.resize((ancho, ancho), Image.LANCZOS),
            preparada.resize((ancho, ancho), Image.LANCZOS),
        ]
        if os.path.exists(img_db):
            piezas.append(Image.open(img_db).resize((ancho, ancho), Image.LANCZOS))
        else:
            piezas.append(Image.new("RGB", (ancho, ancho), (200, 200, 200)))

        lienzo = Image.new("RGB", (ancho * 3 + 40, ancho + 34), (255, 255, 255))
        d = ImageDraw.Draw(lienzo)
        d.text((5, 4), f"{archivo} | {cat} | correcto={correcto}", font=_font(11), fill=(0, 0, 0))
        lienzo.paste(piezas[0], (10, 20))
        d.text((10, ancho + 24), "consulta", font=_font(11), fill=(0, 0, 0))
        lienzo.paste(piezas[1], (ancho + 20, 20))
        d.text((ancho + 20, ancho + 24), "preparada", font=_font(11), fill=(0, 0, 0))
        lienzo.paste(piezas[2], (2 * ancho + 30, 20))
        d.text((2 * ancho + 30, ancho + 24), f"Top1 H2: {top1_proc}", font=_font(11), fill=(0, 0, 0))

        out = os.path.join(MONT_OUT, os.path.splitext(archivo)[0] + ".png")
        lienzo.save(out)
        print("montaje:", out)


if __name__ == "__main__":
    main()
