# -*- coding: utf-8 -*-
"""
generar_consultas_prueba.py
---------------------------
SALA 3 - Hito 2: infraestructura de la PRUEBA INTEGRADA COMÚN (50 consultas).

Genera evaluation/consultas_hito2.csv con las consultas DERIVABLES del banco
sin inventar imágenes:

  - 10 EXACTAS   : la misma imagen del catálogo (data/images_final/).
  - 10 SIN MARCO : la versión normalizada del mismo diseño
                   (data/images_normalized/): es literalmente la misma
                   camiseta sin marco/cabecera/pie/logo (entregable Sala 1).

Las 30 consultas restantes requieren imágenes que no se pueden derivar
automáticamente del banco y las entregan las otras salas:

  - 10 RECOLOREADAS   : Sala 4 (conjunto de prueba de modelos).
  - 10 RECORTADAS     : Sala 4.
  - 10 MOCKUP/PERSONA : Sala 2 (consultas con fotos reales).

Esas filas se agregan al MISMO CSV (mismas columnas) y
scripts/compare_hito1_hito2.py las toma automáticamente.

Columnas del CSV:
    consulta, categoria, ruta_imagen, id_correcto

Uso:
    python scripts/generar_consultas_prueba.py            # 20 consultas (10+10)
    python scripts/generar_consultas_prueba.py --n 10     # cantidad por categoría
"""

import argparse
import csv
import os
import random
import sys

import pandas as pd

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
PRODUCTS_CSV = os.path.join(BASE_DIR, "data", "products.csv")
IMAGES_FINAL = os.path.join(BASE_DIR, "data", "images_final")
IMAGES_NORM = os.path.join(BASE_DIR, "data", "images_normalized")
SALIDA_CSV = os.path.join(BASE_DIR, "evaluation", "consultas_hito2.csv")
README_DIR = os.path.join(BASE_DIR, "evaluation", "consultas_hito2")

SEMILLA = 42


def _elegir_ids(n):
    """Selecciona n IDs del catálogo que existan en ambas carpetas (final y normalizada)."""
    df = pd.read_csv(PRODUCTS_CSV, encoding="utf-8")
    candidatos = []
    for _, row in df.iterrows():
        base_id = os.path.splitext(row["imagen"])[0]
        if os.path.exists(os.path.join(IMAGES_FINAL, row["imagen"])) and \
           os.path.exists(os.path.join(IMAGES_NORM, base_id + ".jpg")):
            candidatos.append((row["id"], row["imagen"], base_id + ".jpg"))
    rng = random.Random(SEMILLA)
    rng.shuffle(candidatos)
    if len(candidatos) < n:
        print(f"AVISO: solo hay {len(candidatos)} ids con ambas versiones (se pedían {n})")
    return candidatos[:n]


def main():
    parser = argparse.ArgumentParser(description="Sala 3 - Consultas de la prueba integrada")
    parser.add_argument("--n", type=int, default=10,
                        help="Consultas por categoría derivable (default 10)")
    args = parser.parse_args()

    if not os.path.exists(PRODUCTS_CSV):
        sys.exit("No existe data/products.csv (ejecutar primero scripts/consolidar.py)")

    elegidos = _elegir_ids(args.n)
    filas = []

    # ── 10 EXACTAS: la misma imagen del banco ──
    for i, (pid, archivo, _) in enumerate(elegidos, start=1):
        filas.append({
            "consulta": f"exacta_{i:02d}_{archivo}",
            "categoria": "exacta",
            "ruta_imagen": os.path.join("data", "images_final", archivo).replace("\\", "/"),
            "id_correcto": pid,
        })

    # ── 10 SIN MARCO: la normalizada del mismo diseño (mismo id) ──
    for i, (pid, _, norm) in enumerate(elegidos, start=1):
        filas.append({
            "consulta": f"sin_marco_{i:02d}_{norm}",
            "categoria": "sin_marco",
            "ruta_imagen": os.path.join("data", "images_normalized", norm).replace("\\", "/"),
            "id_correcto": pid,
        })

    with open(SALIDA_CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["consulta", "categoria", "ruta_imagen", "id_correcto"])
        w.writeheader()
        w.writerows(filas)

    # ── documentar las categorías pendientes (Sala 4 / Sala 2) ──
    os.makedirs(README_DIR, exist_ok=True)
    with open(os.path.join(README_DIR, "README.md"), "w", encoding="utf-8") as f:
        f.write("# Prueba integrada común del Hito 2 (50 consultas)\n\n")
        f.write("Este directorio y `evaluation/consultas_hito2.csv` son la PRUEBA\n")
        f.write("INTEGRADA del Hito 2 (TRABAJO.md: 'Pruebas obligatorias para TODAS\n")
        f.write("las salas'). Cada consulta tiene previamente identificado el diseño\n")
        f.write("correcto (`id_correcto`).\n\n")
        f.write("## Estado generado por scripts/generar_consultas_prueba.py\n\n")
        f.write("| Categoría | Cantidad | Quién aporta | Estado |\n")
        f.write("|---|---|---|---|\n")
        f.write(f"| exacta | {args.n} | derivada del banco (images_final) | listo |\n")
        f.write(f"| sin_marco | {args.n} | derivada de Sala 1 (images_normalized) | listo |\n")
        f.write("| recoloreada | 10 | Sala 4 (conjunto de prueba) | pendiente |\n")
        f.write("| recortada | 10 | Sala 4 (conjunto de prueba) | pendiente |\n")
        f.write("| mockup_persona | 10 | Sala 2 (fotos reales) | pendiente |\n\n")
        f.write("## Cómo agregar las consultas pendientes\n\n")
        f.write("Añadir filas al CSV `evaluation/consultas_hito2.csv` con el mismo\n")
        f.write("formato (o reemplazar el archivo completo):\n\n")
        f.write("```\nconsulta,categoria,ruta_imagen,id_correcto\n")
        f.write("rec_01.png,recoloreada,evaluation/consultas_hito2/recoloreadas/rec_01.png,AIM-P001-001\n")
        f.write("```\n\n")
        f.write("Las imágenes pueden vivir en `evaluation/consultas_hito2/` "
                "(subcarpetas `recoloreadas/`, `recortadas/`, `mockups/`).\n")
        f.write("scripts/compare_hito1_hito2.py toma automáticamente todas las filas\n")
        f.write("cuyo archivo exista y omite las demás.\n")

    total = len(filas)
    print("=" * 60)
    print("SALA 3 / HITO 2 - CONSULTAS DE LA PRUEBA INTEGRADA")
    print("=" * 60)
    print(f"exactas      : {args.n} (data/images_final/)")
    print(f"sin_marco    : {args.n} (data/images_normalized/)")
    print(f"recoloreadas : pendiente (Sala 4)")
    print(f"recortadas   : pendiente (Sala 4)")
    print(f"mockup/persona: pendiente (Sala 2)")
    print(f"Total listas : {total} de 50")
    print(f"CSV          : {SALIDA_CSV}")
    print(f"Instrucciones: {os.path.join(README_DIR, 'README.md')}")
    print("=" * 60)


if __name__ == "__main__":
    main()
