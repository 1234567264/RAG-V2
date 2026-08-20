# -*- coding: utf-8 -*-
"""
regenerar_consultas.py
----------------------
Regenera las 50 consultas de prueba (5 categorías x 10 diseños) desde
data/images_normalized/ con mappings correctos.

Genera:
  data/consultas/cXX_categoria.{jpg|jpeg|png}
  evaluation/consultas_hito2.csv
"""

import os
import random

import numpy as np
from PIL import Image, ImageEnhance

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
IMG_SRC = os.path.join(BASE_DIR, "data", "images_normalized")
OUT_DIR = os.path.join(BASE_DIR, "data", "consultas")
MANIFEST = os.path.join(BASE_DIR, "evaluation", "consultas_hito2.csv")

SEED = 42
# 10 diseños del banco — IDs exactos de images_normalized
DISENOS = [f"AIM-P001-{i:03d}" for i in range(1, 11)]


def _buscar_fuente(id_base):
    for ext in (".jpg", ".jpeg", ".png"):
        ruta = os.path.join(IMG_SRC, id_base + ext)
        if os.path.exists(ruta):
            return ruta
    return None


def contenido_box(arr, thr=0.15):
    h, w = arr.shape[:2]
    a = arr.astype(np.float32)
    rowstd = a.std(axis=(1, 2))
    colstd = a.std(axis=(0, 2))
    ys = np.where(rowstd > thr * rowstd.max())[0]
    xs = np.where(colstd > thr * colstd.max())[0]
    y1, y2 = (int(ys.min()), int(ys.max())) if len(ys) else (0, h)
    x1, x2 = (int(xs.min()), int(xs.max())) if len(xs) else (0, w)
    m = 5
    return (max(0, x1 - m), max(0, y1 - m), min(w, x2 + m), min(h, y2 + m))


def recolor(im, hue=60, sat=1.6, bri=1.15):
    im = ImageEnhance.Color(im).enhance(sat)
    im = ImageEnhance.Brightness(im).enhance(bri)
    arr = np.asarray(im.convert("RGB"))
    if hue:
        arr_hsv = np.asarray(im.convert("HSV"), dtype=np.int16)
        arr_hsv[:, :, 0] = (arr_hsv[:, :, 0] + hue) % 180
        im = Image.fromarray(arr_hsv.astype(np.uint8), "HSV").convert("RGB")
    return im


def recorte_central(im, frac=0.55):
    w, h = im.size
    nw, nh = int(w * frac), int(h * frac)
    x1, y1 = (w - nw) // 2, (h - nh) // 2
    return im.crop((x1, y1, x1 + nw, y1 + nh))


def persona(im_shirt):
    from PIL import ImageDraw
    rng = random.Random(SEED)
    SIZE = 320
    try:
        import cv2
        arr = np.asarray(im_shirt.convert("RGB"))
        h, w = arr.shape[:2]
        M = cv2.getRotationMatrix2D((w / 2, h / 2), rng.uniform(-7, 7), 0.95)
        warped = cv2.warpAffine(arr, M, (w, h), borderValue=(220, 220, 220))
        camisa = Image.fromarray(warped)
    except Exception:
        camisa = im_shirt

    canvas = Image.new("RGB", (SIZE, SIZE))
    d = ImageDraw.Draw(canvas)
    for y in range(SIZE):
        t = y / SIZE
        color = (int(120 + 60 * t), int(150 + 40 * t), int(190 + 20 * t))
        d.line([(0, y), (SIZE, y)], fill=color)
    for y in range(int(SIZE * 0.82), SIZE):
        d.line([(0, y), (SIZE, y)], fill=(60, 55, 50))

    cx = SIZE // 2
    torso = (cx - 85, 95, cx + 85, 275)
    cabeza = (cx - 35, 35, cx + 35, 110)
    brazo_i = (cx - 110, 110, cx - 85, 245)
    brazo_d = (cx + 85, 110, cx + 110, 245)
    piernas = (cx - 70, 275, cx + 70, SIZE)
    piel = (235, 195, 160)

    d.ellipse(cabeza, fill=piel)
    d.rectangle(brazo_i, fill=piel)
    d.rectangle(brazo_d, fill=piel)
    d.rectangle(piernas, fill=(40, 60, 110))
    camisa = camisa.resize((170, 180), Image.LANCZOS)
    mascara = Image.new("L", camisa.size, 0)
    dm = ImageDraw.Draw(mascara)
    dm.rounded_rectangle([(0, 0), (170, 180)], radius=22, fill=255)
    canvas.paste(camisa, (torso[0], torso[1]), mascara)
    d.ellipse((torso[0] + 10, 95, torso[2] - 10, 120), fill=piel)
    return canvas


def main():
    random.seed(SEED)
    os.makedirs(OUT_DIR, exist_ok=True)

    fuentes = []
    for id_base in DISENOS:
        ruta = _buscar_fuente(id_base)
        if ruta is not None:
            fuentes.append((id_base, ruta))
        else:
            print(f"SKIP: {id_base} not found in {IMG_SRC}")

    print(f"Fuentes encontradas: {len(fuentes)}/{len(DISENOS)}")
    if len(fuentes) < 10:
        print("ERROR: se necesitan al menos 10 fuentes")
        return 1

    filas = []
    for i, (id_base, ruta) in enumerate(fuentes, start=1):
        im = Image.open(ruta).convert("RGB")

        versiones = {
            "exacta": (im, "jpg"),
            "sin_marco": (im.crop(contenido_box(np.asarray(im))), "jpg"),
            "recoloreada": (recolor(im), "jpeg"),
            "recortada": (recorte_central(im), "jpg"),
            "persona": (persona(im.crop(contenido_box(np.asarray(im)))), "jpeg"),
        }
        for cat, (vim, ext) in versiones.items():
            archivo = f"c{i:02d}_{cat}.{ext}"
            vim.convert("RGB").save(os.path.join(OUT_DIR, archivo), "JPEG", quality=92)
            filas.append((archivo, cat, id_base))
            print(f"OK  {archivo}  ->  {id_base}")

    with open(MANIFEST, "w", encoding="utf-8") as f:
        f.write("consulta,categoria,ruta_imagen,id_correcto\n")
        for archivo, cat, cid in filas:
            f.write(f"{archivo},{cat},data/consultas/{archivo},{cid}\n")

    print(f"\nListo: {len(filas)} consultas en {OUT_DIR}")
    print(f"Manifiesto: {MANIFEST}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
