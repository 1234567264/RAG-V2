# -*- coding: utf-8 -*-
"""
precomputar_descriptores.py
---------------------------
Precomputa los descriptores visuales avanzados del catalogo para que el motor
de api/search_engine_hito2.py no tenga que recalcularlos en cada consulta.

Entrada:
    data/products.csv                 (orden fila por fila)
    data/images_normalized/           (UNICA carpeta de imagenes usada)

Salida:
    data/descriptores.json   {
        "version": 2,
        "fuente": "images_normalized",
        "ids": [...],
        "descriptores": [ {color_dominante, gama, patron, marco, franjas}, ... ]
    }

NOTA: NO se leen imagenes de otra carpeta de data (ni images_final/ ni
images_original/). Si un producto no resuelve en images_normalized/ se
marca como error, no se sustituye por otra carpeta.

Uso:
    python scripts/precomputar_descriptores.py
    python scripts/precomputar_descriptores.py --solo clip --limite 100
"""

import argparse
import csv
import json
import os
import sys
import time

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, BASE_DIR)

from api.descriptores_visuales import descriptores_de_bgr, leer_bgr_desde_ruta  # noqa: E402

DATA_DIR = os.path.join(BASE_DIR, "data")
CSV_PATH = os.path.join(DATA_DIR, "products.csv")
IMAGES_NORM = os.path.join(DATA_DIR, "images_normalized")
SALIDA = os.path.join(DATA_DIR, "descriptores.json")


def resolver_ruta(fila):
    """Ruta de la imagen del producto. SOLO se busca en images_normalized/
    (nombre exacto del CSV o su equivalente <id>.jpg)."""
    for nombre in (fila.get("imagen", ""), str(fila.get("id", "")) + ".jpg"):
        ruta = os.path.join(IMAGES_NORM, nombre)
        if os.path.exists(ruta):
            return ruta
    return None


def main():
    parser = argparse.ArgumentParser(description="Precomputar descriptores visuales del catalogo")
    parser.add_argument("--limite", type=int, default=None,
                        help="Procesar solo las primeras N filas (pruebas)")
    args = parser.parse_args()

    if not os.path.exists(CSV_PATH):
        sys.exit(f"No existe {CSV_PATH} (ejecutar primero scripts/consolidar.py)")

    with open(CSV_PATH, "r", encoding="utf-8") as f:
        filas = list(csv.DictReader(f))
    if args.limite:
        filas = filas[:args.limite]

    print("=" * 60)
    print("PRECOMPUTO DE DESCRIPTORES VISUALES AVANZADOS")
    print("=" * 60)
    print(f"CSV           : {CSV_PATH}")
    print(f"Imagenes      : {IMAGES_NORM} (UNICA carpeta de busqueda)")
    print(f"Registros     : {len(filas)}")
    print(f"Salida        : {SALIDA}")

    ids = []
    descriptores = []
    errores = 0
    t0 = time.perf_counter()

    for i, fila in enumerate(filas, start=1):
        ruta = resolver_ruta(fila)
        pid = fila.get("id", "")
        if ruta is None:
            print(f"  [{i}/{len(filas)}] SIN IMAGEN: {pid}")
            errores += 1
            continue
        bgr = leer_bgr_desde_ruta(ruta)
        desc = descriptores_de_bgr(bgr) if bgr is not None else None
        if desc is None:
            print(f"  [{i}/{len(filas)}] NO PROCESABLE: {pid}")
            errores += 1
            continue
        ids.append(pid)
        descriptores.append(desc)
        if i % 100 == 0 or i == len(filas):
            print(f"  [{i}/{len(filas)}] ok={len(ids)} errores={errores}")

    datos = {
        "version": 2,
        "fuente": "images_normalized",
        "generado": time.strftime("%Y-%m-%d %H:%M:%S"),
        "ids": ids,
        "descriptores": descriptores,
    }
    with open(SALIDA, "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False)

    seg = time.perf_counter() - t0
    print("=" * 60)
    print(f"Descriptores : {len(ids)}  (errores: {errores})")
    print(f"Tiempo       : {seg:.1f}s")
    print(f"Guardado en  : {SALIDA}")
    print("=" * 60)


if __name__ == "__main__":
    main()
