# -*- coding: utf-8 -*-
"""
generar_indices_comparativos.py
-------------------------------
SALA 4 - Comparación de modelos y embeddings.

Genera de forma independiente los tres índices de embeddings comparados a
partir de `data/products.csv` (mismo orden de fila), las imágenes NORMALIZADAS
del Hito 2 (Sala 1) en `data/images_normalized/` y los IDs ya existentes en
`data/ids.npy`:

    data/embeddings_clip.npy       CLIP     (openai/clip-vit-base-patch32,          N x 512)
    data/embeddings_openclip.npy   OpenCLIP (laion/CLIP-ViT-B-32-laion2B-s34B-b79K, N x 512)
    data/embeddings_siglip.npy     SigLIP   (google/siglip-base-patch16-224,        N x 768)

Propiedades obligatorias (igual que en el Hito 1):
    * Procesamiento por lotes (batch_size = 16).
    * Normalización L2 de todos los vectores antes de guardarlos.
    * Alineación posicional con data/ids.npy (posición 0 -> primer ID del CSV).

El tiempo de generación de cada modelo se registra de forma incremental en
`data/tiempos.csv` (columnas `consulta,tiempo_segundos`, filas con prefijo
`generacion_<clave>`). Los 3 checkpoints ya están en el cache de HuggingFace,
por lo que el script funciona sin conexión.

Uso:
    python scripts/generar_indices_comparativos.py
    python scripts/generar_indices_comparativos.py --solo clip openclip
"""

import argparse
import csv
import os
import time
import warnings

import numpy as np
import torch
from PIL import Image
from transformers import CLIPModel, CLIPProcessor, SiglipImageProcessor, SiglipModel

os.environ.setdefault("HF_HUB_OFFLINE", "1")
warnings.filterwarnings("ignore")

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA_DIR = os.path.join(BASE_DIR, "data")
CSV_PATH = os.path.join(DATA_DIR, "products.csv")
# Hito 2 (TRABAJO.md, Sala 4): los tres índices deben usar EXACTAMENTE las
# mismas imágenes NORMALIZADAS por Sala 1 (data/images_normalized/), no las
# originales con marco (data/images_final/).
IMAGES_DIR = os.path.join(DATA_DIR, "images_normalized")
IDS_PATH = os.path.join(DATA_DIR, "ids.npy")
TIEMPOS_CSV = os.path.join(DATA_DIR, "tiempos.csv")

BATCH_SIZE = 16


def resolver_ruta_imagen(fila):
    """
    Devuelve la ruta de la imagen en data/images_normalized/.
    La normalización de Sala 1 convierte TODO a .jpg con el mismo ID, así que
    si el nombre exacto del CSV no existe (p. ej. AIM-P001-005.png) se busca
    el equivalente <id>.jpg. Devuelve None si no hay ningún archivo.
    """
    ruta = os.path.join(IMAGES_DIR, fila["imagen"])
    if os.path.exists(ruta):
        return ruta
    alternativas = [
        os.path.join(IMAGES_DIR, fila["id"] + ".jpg"),
        os.path.join(IMAGES_DIR, fila["id"] + ".png"),
        os.path.join(IMAGES_DIR, os.path.splitext(fila["imagen"])[0] + ".jpg"),
    ]
    for candidata in alternativas:
        if os.path.exists(candidata):
            return candidata
    return None

# Modelos a comparar. Para SigLIP se usa SOLO el preprocesador de imagen
# (SiglipImageProcessor) para no depender del tokenizador SentencePiece.
MODELOS = [
    {
        "clave": "clip",
        "etiqueta": "CLIP (openai/clip-vit-base-patch32)",
        "modelo_cls": CLIPModel,
        "processor_cls": CLIPProcessor,
        "checkpoint": "openai/clip-vit-base-patch32",
    },
    {
        "clave": "openclip",
        "etiqueta": "OpenCLIP (laion/CLIP-ViT-B-32-laion2B-s34B-b79K)",
        "modelo_cls": CLIPModel,
        "processor_cls": CLIPProcessor,
        "checkpoint": "laion/CLIP-ViT-B-32-laion2B-s34B-b79K",
    },
    {
        "clave": "siglip",
        "etiqueta": "SigLIP (google/siglip-base-patch16-224)",
        "modelo_cls": SiglipModel,
        "processor_cls": SiglipImageProcessor,
        "checkpoint": "google/siglip-base-patch16-224",
    },
]


def leer_productos_csv():
    """Devuelve las filas del CSV conservando el orden exacto del archivo."""
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


def cargar_ids(filas):
    """
    Carga data/ids.npy (ya existente) y valida la alineación posicional con el
    CSV. Si el archivo falta o las posiciones no coinciden, regenera los IDs
    desde el CSV (orden fila por fila) con un aviso.
    """
    ids_csv = [fila["id"] for fila in filas]
    if not os.path.exists(IDS_PATH):
        print(f"  [AVISO] No existe {IDS_PATH}; regenerando IDs desde products.csv")
        return np.array(ids_csv, dtype=object)

    ids = np.load(IDS_PATH, allow_pickle=True)
    if len(ids) != len(ids_csv) or any(str(a) != str(b) for a, b in zip(ids, ids_csv)):
        print(
            f"  [AVISO] {IDS_PATH} no coincide con products.csv; "
            "reconstruyendo IDs desde el CSV"
        )
        return np.array(ids_csv, dtype=object)

    print(f"  IDs cargados de data/ids.npy: {len(ids)} (alineados con el CSV)")
    return ids


def extraer_embeddings(features):
    """Extrae el tensor de embeddings de imagen del retorno de get_image_features."""
    if torch.is_tensor(features):
        return features
    for attr in ("image_embeds", "pooler_output"):
        if hasattr(features, attr):
            return getattr(features, attr)
    raise TypeError(f"No se pudo extraer el embedding del retorno: {type(features)}")


def registrar_tiempo(consulta, segundos):
    """Anexa una fila a data/tiempos.csv (crea el encabezado si hace falta)."""
    existe = os.path.exists(TIEMPOS_CSV)
    with open(TIEMPOS_CSV, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if not existe or os.path.getsize(TIEMPOS_CSV) == 0:
            writer.writerow(["consulta", "tiempo_segundos"])
        writer.writerow([consulta, round(float(segundos), 4)])


def limpiar_tiempos_generacion():
    """Quita filas previas `generacion_*` para no duplicar al re-ejecutar."""
    if not os.path.exists(TIEMPOS_CSV):
        return
    with open(TIEMPOS_CSV, "r", encoding="utf-8") as f:
        lector = csv.DictReader(f)
        filas = [
            (row["consulta"], row.get("tiempo_segundos", ""))
            for row in lector if not str(row.get("consulta", "")).startswith("generacion_")
        ]
    with open(TIEMPOS_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["consulta", "tiempo_segundos"])
        writer.writerows(filas)


def generar_indice(cfg, filas, ids, device):
    """Genera, normaliza (L2) y guarda el embedding del modelo indicado."""
    clave = cfg["clave"]
    salida = os.path.join(DATA_DIR, f"embeddings_{clave}.npy")

    print(f"\n=== {cfg['etiqueta']} ===")
    print(f"  Cargando modelo '{cfg['checkpoint']}'...")
    modelo = cfg["modelo_cls"].from_pretrained(cfg["checkpoint"]).to(device)
    processor = cfg["processor_cls"].from_pretrained(cfg["checkpoint"])
    modelo.eval()

    total = len(filas)

    # La dimensión depende del modelo (CLIP/OpenCLIP 512, SigLIP 768): se
    # detecta con una pasada de prueba para no hardcodear el valor.
    proba = Image.new("RGB", (224, 224), (128, 128, 128))
    with torch.no_grad():
        p_in = processor(images=[proba], return_tensors="pt")
        p_in = {k: v.to(device) for k, v in p_in.items()}
        p_out = extraer_embeddings(modelo.get_image_features(**p_in))
    dimensiones = int(p_out.shape[-1])

    embeddings = np.zeros((total, dimensiones), dtype=np.float32)
    errores = 0
    inicio = time.perf_counter()

    for lote_inicio in range(0, total, BATCH_SIZE):
        lote = filas[lote_inicio:lote_inicio + BATCH_SIZE]
        indices_lote = []
        imagenes_lote = []

        for pos, fila in enumerate(lote):
            idx = lote_inicio + pos
            ruta_imagen = resolver_ruta_imagen(fila)
            if ruta_imagen is None:
                print(f"  [ERROR] Imagen no encontrada para {fila['id']}: "
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
        inputs = {k: v.to(device) for k, v in inputs.items()}

        with torch.no_grad():
            features = extraer_embeddings(modelo.get_image_features(**inputs))

        features = features / features.norm(p=2, dim=-1, keepdim=True)
        lote_embeddings = features.cpu().numpy().astype(np.float32)
        for idx_original, vector in zip(indices_lote, lote_embeddings):
            embeddings[idx_original] = vector

    os.makedirs(DATA_DIR, exist_ok=True)
    np.save(salida, embeddings)

    segundos = time.perf_counter() - inicio
    registrar_tiempo(f"generacion_{clave}", segundos)

    generados = int(np.count_nonzero(np.linalg.norm(embeddings, axis=1)))
    dimensiones = embeddings.shape[1]

    print(f"  Tiempo de generación : {segundos:.2f}s")
    print(f"  Embeddings generados : {generados}/{total} (errores: {errores})")
    print(f"  Dimensiones          : {dimensiones}")
    print(f"  Guardado en          : {salida}")
    return generados, errores, segundos


def main():
    parser = argparse.ArgumentParser(description="Sala 4 - Índices comparados CLIP/OpenCLIP/SigLIP")
    parser.add_argument("--solo", nargs="*", choices=[m["clave"] for m in MODELOS],
                        default=None, help="Solo estos modelos (por defecto todos)")
    args = parser.parse_args()

    claves = set(args.solo) if args.solo else {m["clave"] for m in MODELOS}
    seleccion = [m for m in MODELOS if m["clave"] in claves]

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print("=" * 72)
    print("SALA 4 - GENERACIÓN DE ÍNDICES COMPARATIVOS")
    print(f"Dispositivo: {device} | Modelos: {', '.join(m['clave'] for m in seleccion)}")
    print("=" * 72)

    filas = leer_productos_csv()
    ids = cargar_ids(filas)
    limpiar_tiempos_generacion()

    resumen = []
    for cfg in seleccion:
        generados, errores, segundos = generar_indice(cfg, filas, ids, device)
        resumen.append((cfg["clave"], generados, errores, segundos))

    print("\n" + "=" * 72)
    print("RESUMEN DE GENERACIÓN")
    print("=" * 72)
    for clave, generados, errores, segundos in resumen:
        print(f"  {clave:<10s} {generados:>5d} embeddings  errores={errores:<3d}  {segundos:8.2f}s")
    print(f"Tiempos registrados en: {TIEMPOS_CSV}")


if __name__ == "__main__":
    main()
