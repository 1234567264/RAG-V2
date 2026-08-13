# -*- coding: utf-8 -*-
"""
buscar_por_imagen.py
--------------------
SALA 4 - Hito 1: Búsqueda visual por similitud de embeddings.

Carga el índice único generado por `generar_embeddings.py`
(data/embeddings.npy + data/ids.npy), genera el embedding de la imagen de
consulta con `openai/clip-vit-base-patch32` y devuelve los 5 productos más
cercanos en el espacio vectorial del modelo.

Sobre el "score de similitud":
-------------------------------
El score es una medida de CERCANÍA MATEMÁTICA entre dos vectores dentro del
espacio vectorial aprendido por el modelo CLIP (similitud coseno, rango de
-1 a 1). NO es un porcentaje de coincidencia, ni una confianza, ni una
probabilidad de que sea el mismo diseño. Un score alto indica que el modelo
representa ambas imágenes de forma muy parecida; no garantiza que el diseño
sea idéntico.

Uso:
    python buscar_por_imagen.py <imagen> [<imagen2> ...]

Pruebas con imágenes EXTERNAS (fuera de la biblioteca base), con las 3
categorías pedidas: muy parecida, colores diferentes y no relacionada:

    python buscar_por_imagen.py --test-externo \
        test/muy_parecida.jpg \
        test/colores_diferentes.jpg \
        test/no_relacionada.jpg
"""

import argparse
import os
import sys
import time

import numpy as np
import torch
from PIL import Image
from transformers import CLIPModel, CLIPProcessor

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA_DIR = os.path.join(BASE_DIR, "data")
EMBEDDINGS_PATH = os.path.join(DATA_DIR, "embeddings.npy")
IDS_PATH = os.path.join(DATA_DIR, "ids.npy")

MODEL_NAME = "openai/clip-vit-base-patch32"
TOP_K = 5

_model = None
_processor = None
_embeddings = None
_ids = None
_nombres_imagenes = {}

EXPLICACION_SCORE = (
    "El score de similitud mide la cercanía matemática entre dos vectores en el "
    "espacio vectorial del modelo CLIP (similitud coseno). No es un porcentaje "
    "de coincidencia ni una probabilidad de que sea el mismo diseño."
)


def get_model():
    global _model, _processor
    if _model is None:
        _model = CLIPModel.from_pretrained(MODEL_NAME)
        _processor = CLIPProcessor.from_pretrained(MODEL_NAME)
        _model.eval()
    return _model, _processor


def cargar_indice():
    global _embeddings, _ids, _nombres_imagenes
    if _embeddings is not None:
        return _embeddings, _ids

    if not os.path.exists(EMBEDDINGS_PATH):
        print(f"Error: No se encontró el índice de embeddings en: {EMBEDDINGS_PATH}")
        print("Ejecuta primero: python generar_embeddings.py")
        sys.exit(1)

    if not os.path.exists(IDS_PATH):
        print(f"Error: No se encontró el archivo de IDs en: {IDS_PATH}")
        print("Ejecuta primero: python generar_embeddings.py")
        sys.exit(1)

    _embeddings = np.load(EMBEDDINGS_PATH).astype(np.float32)
    _ids = np.load(IDS_PATH, allow_pickle=True)

    if _embeddings.shape[0] != len(_ids):
        print(
            f"Error de correspondencia: {_embeddings.shape[0]} embeddings vs "
            f"{len(_ids)} IDs. Regenera el índice con generar_embeddings.py"
        )
        sys.exit(1)

    csv_path = os.path.join(DATA_DIR, "products.csv")
    if os.path.exists(csv_path):
        import csv as csv_mod
        with open(csv_path, "r", encoding="utf-8") as f:
            for fila in csv_mod.DictReader(f):
                _nombres_imagenes[fila["id"]] = fila["imagen"]

    return _embeddings, _ids


def generar_embedding(ruta_imagen):
    """Genera el embedding normalizado L2 de una imagen."""
    model, processor = get_model()
    imagen = Image.open(ruta_imagen).convert("RGB")
    inputs = processor(images=imagen, return_tensors="pt")
    with torch.no_grad():
        features = model.get_image_features(**inputs)
    if hasattr(features, "pooler_output"):
        features = features.pooler_output
    elif hasattr(features, "image_embeds"):
        features = features.image_embeds
    features = features / features.norm(p=2, dim=-1, keepdim=True)
    return features.cpu().numpy().flatten().astype(np.float32)


def buscar_similares(ruta_imagen, top_k=TOP_K):
    """Devuelve los top_k productos más similares: [{id, imagen, score}, ...]."""
    embeddings, ids = cargar_indice()
    vector = generar_embedding(ruta_imagen)

    scores = np.dot(embeddings, vector)
    top_indices = np.argsort(scores)[::-1][:top_k]

    resultados = []
    for idx in top_indices:
        product_id = str(ids[idx])
        resultados.append({
            "id": product_id,
            "imagen": _nombres_imagenes.get(product_id, f"{product_id} (sin archivo)"),
            "score": round(float(scores[idx]), 4),
        })
    return resultados


def mostrar_resultados(ruta_imagen, resultados):
    nombre = os.path.basename(ruta_imagen)
    print(f"\n--- Top {len(resultados)} para '{nombre}' ---")
    for rank, r in enumerate(resultados, 1):
        print(f"{rank}. {r['id']} ({r['imagen']}) | score de similitud: {r['score']:.4f}")


def test_externo(rutas):
    """Prueba con imágenes externas: muy parecida, colores diferentes, no relacionada."""
    if len(rutas) < 3:
        print("El modo --test-externo requiere al menos 3 imágenes:")
        print("  1) muy parecida   2) colores diferentes   3) no relacionada")
        sys.exit(1)

    etiquetas = [
        "Muy parecida (fuera de la biblioteca)",
        "Colores diferentes",
        "No relacionada",
    ]

    print(EXPLICACION_SCORE)
    print(f"\n=== PRUEBA CON IMÁGENES EXTERNAS ({len(rutas)} consultas) ===")

    inicio = time.perf_counter()
    for etiqueta, ruta in zip(etiquetas, rutas):
        if not os.path.exists(ruta):
            print(f"\n[SKIP] No existe la imagen: {ruta}")
            continue
        print(f"\n>>> {etiqueta}: {os.path.basename(ruta)}")
        t0 = time.perf_counter()
        resultados = buscar_similares(ruta)
        mostrar_resultados(ruta, resultados)
        print(f"    Tiempo de consulta: {time.perf_counter() - t0:.2f}s")

    print(f"\nTiempo total de procesamiento (pruebas externas): {time.perf_counter() - inicio:.2f}s")


def main():
    parser = argparse.ArgumentParser(
        description="Búsqueda visual por similitud de embeddings (Sala 4)."
    )
    parser.add_argument(
        "imagenes",
        nargs="+",
        help="Una o más imágenes a consultar.",
    )
    parser.add_argument(
        "--test-externo",
        action="store_true",
        help="Prueba con imágenes externas (muy parecida, colores diferentes, no relacionada).",
    )
    args = parser.parse_args()

    print(f"Modelo: {MODEL_NAME}")

    if args.test_externo:
        test_externo(args.imagenes)
        return

    print(EXPLICACION_SCORE)
    inicio = time.perf_counter()
    for ruta in args.imagenes:
        if not os.path.exists(ruta):
            print(f"Error: La imagen no existe: {ruta}")
            continue
        resultados = buscar_similares(ruta)
        mostrar_resultados(ruta, resultados)
    print(f"\nTiempo total de procesamiento: {time.perf_counter() - inicio:.2f}s")


if __name__ == "__main__":
    main()
