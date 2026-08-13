# -*- coding: utf-8 -*-
"""
generar_embeddings.py
---------------------
SALA 4 - Hito 1: Generación de embeddings visuales con CLIP.

Lee `data/products.csv` SIGUIENDO SU ORDEN (fila por fila), abre la imagen
correspondiente para cada producto, genera su embedding con el modelo
`openai/clip-vit-base-patch32` y guarda el ID del producto en la posición
exacta del array, manteniendo la correspondencia posicional obligatoria:

    Posición 0 del embedding -> AIM-P001-001
    Posición 1 del embedding -> AIM-P001-002
    ...

Requisitos del hito:
  * Procesamiento por lotes (batch_size = 16).
  * Normalización L2 de todos los vectores antes de guardarlos.
  * Únicamente dos archivos de salida:
      data/embeddings.npy   (matriz float32, N x 512)
      data/ids.npy          (IDs en el mismo orden que los embeddings)

Uso:
    python generar_embeddings.py
"""

import csv
import os
import time

import numpy as np
import torch
from PIL import Image
from transformers import CLIPModel, CLIPProcessor

# ----------------------------------------------------------------------
# CONFIGURACIÓN DE RUTAS (estructura única acordada para el Hito 1)
# ----------------------------------------------------------------------
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA_DIR = os.path.join(BASE_DIR, "data")
CSV_PATH = os.path.join(DATA_DIR, "products.csv")
# Banco único sobre el que se construye el índice: las imágenes NORMALIZADAS
# de Sala 1 (sin marco, sin texto externo), las mismas que muestra la interfaz
# y sobre las que el motor Hito 2 ya calcula sus descriptores visuales.
IMAGES_DIR = os.path.join(DATA_DIR, "images_normalized")

EMBEDDINGS_PATH = os.path.join(DATA_DIR, "embeddings.npy")
IDS_PATH = os.path.join(DATA_DIR, "ids.npy")

MODEL_NAME = "openai/clip-vit-base-patch32"
BATCH_SIZE = 16


def leer_productos_csv():
    """Devuelve la lista de filas del CSV conservando el orden exacto del archivo."""
    if not os.path.exists(CSV_PATH):
        raise FileNotFoundError(
            f"No se encontró data/products.csv en: {CSV_PATH}. "
            "Primero debe ejecutarse la Sala 1 (consolidar.py / main.py)."
        )
    with open(CSV_PATH, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        columnas_requeridas = ["id", "imagen"]
        for col in columnas_requeridas:
            if col not in reader.fieldnames:
                raise ValueError(
                    f"El CSV no tiene la columna requerida '{col}'. "
                    f"Columnas encontradas: {reader.fieldnames}"
                )
        return list(reader)


def resolver_ruta_imagen(fila):
    """
    Devuelve la ruta de la imagen en data/images_normalized/.
    La normalización de Sala 1 convierte TODO a .jpg con el mismo ID, así que
    si el nombre exacto del CSV no existe (p. ej. AIM-P001-005.png) se busca
    el equivalente <id>.jpg (como en generar_indices_comparativos.py).
    Devuelve None si no hay ningún archivo.
    """
    ruta = os.path.join(IMAGES_DIR, fila["imagen"])
    if os.path.exists(ruta):
        return ruta
    for candidata in (
        os.path.join(IMAGES_DIR, fila["id"] + ".jpg"),
        os.path.join(IMAGES_DIR, fila["id"] + ".png"),
        os.path.join(IMAGES_DIR, os.path.splitext(fila["imagen"])[0] + ".jpg"),
    ):
        if os.path.exists(candidata):
            return candidata
    return None


def main():
    inicio_total = time.perf_counter()

    print(f"Cargando modelo CLIP '{MODEL_NAME}'...")
    model = CLIPModel.from_pretrained(MODEL_NAME)
    processor = CLIPProcessor.from_pretrained(MODEL_NAME)
    model.eval()

    filas = leer_productos_csv()
    total_csv = len(filas)
    dimensiones = model.config.projection_dim

    embeddings = np.zeros((total_csv, dimensiones), dtype=np.float32)
    ids = np.empty(total_csv, dtype=object)
    errores = 0

    for inicio in range(0, total_csv, BATCH_SIZE):
        lote = filas[inicio:inicio + BATCH_SIZE]

        indices_lote = []
        imagenes_lote = []

        for pos, fila in enumerate(lote):
            idx = inicio + pos
            product_id = fila["id"]
            ids[idx] = product_id

            ruta_imagen = resolver_ruta_imagen(fila)
            if ruta_imagen is None:
                print(f"  [ERROR] Imagen no encontrada para {product_id}: "
                      f"{fila['imagen']} ni equivalentes en {IMAGES_DIR}")
                errores += 1
                continue

            try:
                imagen = Image.open(ruta_imagen).convert("RGB")
            except Exception as e:
                print(f"  [ERROR] No se pudo abrir {fila['imagen']}: {e}")
                errores += 1
                continue

            indices_lote.append(idx)
            imagenes_lote.append(imagen)

        if not imagenes_lote:
            continue

        inputs = processor(images=imagenes_lote, return_tensors="pt")

        with torch.no_grad():
            features = model.get_image_features(**inputs)

        # Compatibilidad entre versiones de transformers: si devuelve un objeto
        # estructurado, extraer el tensor de embeddings de imagen.
        if hasattr(features, "pooler_output"):
            features = features.pooler_output
        elif hasattr(features, "image_embeds"):
            features = features.image_embeds

        # Normalización L2 obligatoria
        features = features / features.norm(p=2, dim=-1, keepdim=True)

        lote_embeddings = features.cpu().numpy().astype(np.float32)
        for idx_original, vector in zip(indices_lote, lote_embeddings):
            embeddings[idx_original] = vector

    # Guardar únicamente las rutas estándar del Hito 1
    os.makedirs(DATA_DIR, exist_ok=True)
    np.save(EMBEDDINGS_PATH, embeddings)
    np.save(IDS_PATH, ids)

    generados = int(np.count_nonzero(np.linalg.norm(embeddings, axis=1)))
    tiempo_total = time.perf_counter() - inicio_total

    print(f"Tiempo total de procesamiento: {tiempo_total:.2f}s")
    print(f"Archivos generados: {EMBEDDINGS_PATH}, {IDS_PATH}")

    # --- Reporte numérico y de estado obligatorio ---
    print()
    print(f"Productos en CSV: {total_csv}")
    print(f"Embeddings generados: {generados}")
    print(f"IDs guardados: {len(ids)}")
    print(f"Dimensiones: {dimensiones}")
    print(f"Errores: {errores}")


if __name__ == "__main__":
    main()
