# -*- coding: utf-8 -*-
"""
evaluar_50_consultas.py
-----------------------
SALA 4 - Evaluación de los 3 índices sobre el conjunto de 50 consultas.

Entrada:
    data/embeddings_clip.npy, data/embeddings_openclip.npy, data/embeddings_siglip.npy
    data/ids.npy                      (IDs en el mismo orden posicional)
    data/consultas_test_50.json       (conjunto de prueba de 50 consultas)

Si `data/consultas_test_50.json` no existe, se genera automáticamente desde
`data/consultas/` (16 consultas x 5 variantes: exacta, sin_marco, recortada,
recoloreada, cuerpo) y `data/montajes/`. El id correcto de cada consulta se
deriva por hash perceptual del archivo `cXX_exacto` contra `data/images_final/`
(10 consultas por categoría, semilla 42 -> 5 x 10 = 50).

Salida:
    data/evaluation_metrics.csv       reporte técnico Top1/Top5 por modelo (global y por categoría)
    data/revision_humana_modelos_top5.csv  estructura de revisión cualitativa: Top 5 por consulta/modelo
    data/tiempos.csv                  tiempos de búsqueda por consulta/modelo (filas anexas)

Uso:
    python scripts/evaluar_50_consultas.py
"""

import csv
import json
import os
import random
import sys
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
CONSULTAS_DIR = os.path.join(DATA_DIR, "consultas")
MONTAJES_DIR = os.path.join(DATA_DIR, "montajes")
IMAGES_FINAL_DIR = os.path.join(DATA_DIR, "images_final")
IDS_PATH = os.path.join(DATA_DIR, "ids.npy")
TEST_SET_JSON = os.path.join(DATA_DIR, "consultas_test_50.json")
EVAL_METRICS_CSV = os.path.join(DATA_DIR, "evaluation_metrics.csv")
# OJO: este archivo NO debe llamarse revision_humana_50.csv, ese nombre
# pertenece al entregable de Sala 1 (revisar_muestra_50.py). La revisión
# cualitativa del Top 5 por modelo va en un archivo propio de Sala 4.
REVISION_CSV = os.path.join(DATA_DIR, "revision_humana_modelos_top5.csv")
TIEMPOS_CSV = os.path.join(DATA_DIR, "tiempos.csv")

TOP_K = 5
SEMILLA = 42
POR_CATEGORIA = 10

VARIANTE_A_CATEGORIA = {
    "exacto": "exacta",
    "sin_marco": "sin_marco",
    "recorte": "recortada",
    "recoloreado": "recoloreada",
    "cuerpo": "cuerpo",
}

MODELOS = [
    {
        "clave": "clip",
        "etiqueta": "CLIP (openai/clip-vit-base-patch32)",
        "modelo_cls": CLIPModel,
        "processor_cls": CLIPProcessor,
        "checkpoint": "openai/clip-vit-base-patch32",
        "indice": os.path.join(DATA_DIR, "embeddings_clip.npy"),
    },
    {
        "clave": "openclip",
        "etiqueta": "OpenCLIP (laion/CLIP-ViT-B-32-laion2B-s34B-b79K)",
        "modelo_cls": CLIPModel,
        "processor_cls": CLIPProcessor,
        "checkpoint": "laion/CLIP-ViT-B-32-laion2B-s34B-b79K",
        "indice": os.path.join(DATA_DIR, "embeddings_openclip.npy"),
    },
    {
        "clave": "siglip",
        "etiqueta": "SigLIP (google/siglip-base-patch16-224)",
        "modelo_cls": SiglipModel,
        "processor_cls": SiglipImageProcessor,
        "checkpoint": "google/siglip-base-patch16-224",
        "indice": os.path.join(DATA_DIR, "embeddings_siglip.npy"),
    },
]


# ──────────────────────────────────────────────────────────────────────────
# Conjunto de prueba
# ──────────────────────────────────────────────────────────────────────────

def hash_perceptual(ruta, size=16):
    """Average-hash de la imagen (bool array). None si no se puede leer."""
    try:
        a = np.asarray(Image.open(ruta).convert("L").resize((size, size)), dtype=np.float32)
    except Exception:
        return None
    return a > a.mean()


def derivar_ids_correctos():
    """
    Mapea cada consulta cXX a su id del catálogo comparando el archivo
    `cXX_exacto` (hash perceptual) contra `data/images_final/`. Solo se
    aceptan coincidencias únicas.
    """
    refs = {}
    for nombre in sorted(os.listdir(IMAGES_FINAL_DIR)):
        h = hash_perceptual(os.path.join(IMAGES_FINAL_DIR, nombre))
        if h is not None:
            refs[nombre] = h

    mapeo = {}
    for i in range(1, 17):
        prefijo = f"c{i:02d}_exacto"
        archivo = next(
            (n for n in os.listdir(CONSULTAS_DIR) if n.startswith(prefijo)), None
        )
        if archivo is None:
            continue
        h = hash_perceptual(os.path.join(CONSULTAS_DIR, archivo))
        if h is None:
            continue
        sims = sorted(((int((h == ref).sum()), nombre) for nombre, ref in refs.items()),
                      reverse=True)
        if len(sims) < 2 or sims[0][0] <= sims[1][0]:
            print(f"  [AVISO] {prefijo}: coincidencia ambigua, se omite")
            continue
        mapeo[prefijo[:-len("_exacto")]] = sims[0][1].split(".")[0]
    return mapeo


def generar_conjunto_prueba():
    """Crea data/consultas_test_50.json (10 consultas x 5 categorías)."""
    print("  No existe data/consultas_test_50.json; generándolo desde data/consultas...")
    mapeo = derivar_ids_correctos()
    if not mapeo:
        sys.exit("Error: no se pudo derivar ningún id correcto desde data/consultas")

    consultas = []
    rng = random.Random(SEMILLA)
    for variante, categoria in VARIANTE_A_CATEGORIA.items():
        candidatos = []
        for cXX, id_correcto in sorted(mapeo.items()):
            archivo = next(
                (n for n in os.listdir(CONSULTAS_DIR)
                 if n.startswith(f"{cXX}_{variante}")), None
            )
            if archivo is not None:
                candidatos.append((cXX, archivo, id_correcto))
        rng.shuffle(candidatos)
        for cXX, archivo, id_correcto in candidatos[:POR_CATEGORIA]:
            consultas.append({
                "consulta": f"{cXX}_{variante}",
                "categoria": categoria,
                "archivo": archivo,
                "ruta_imagen": os.path.join("data", "consultas", archivo).replace("\\", "/"),
                "id_correcto": id_correcto,
            })

    consultas.sort(key=lambda c: (c["categoria"], c["consulta"]))
    with open(TEST_SET_JSON, "w", encoding="utf-8") as f:
        json.dump({
            "version": 1,
            "descripcion": "Conjunto de prueba de 50 consultas para la Sala 4 "
                           "(5 categorias x 10, semilla 42). Los ids correctos se "
                           "derivan por hash perceptual de las variantes exactas.",
            "semilla": SEMILLA,
            "consultas": consultas,
        }, f, ensure_ascii=False, indent=2)
    return consultas


def cargar_conjunto_prueba():
    """Carga data/consultas_test_50.json o lo genera si no existe."""
    if not os.path.exists(TEST_SET_JSON):
        return generar_conjunto_prueba()

    with open(TEST_SET_JSON, encoding="utf-8") as f:
        datos = json.load(f)
    if isinstance(datos, list):
        return datos
    return datos.get("consultas", [])


def resolver_ruta(consulta):
    """Devuelve la ruta absoluta de la imagen de la consulta."""
    ruta = consulta.get("ruta_imagen")
    if ruta:
        candidata = os.path.join(BASE_DIR, ruta)
        if os.path.exists(candidata):
            return candidata
    archivo = consulta.get("archivo")
    if archivo:
        for carpeta in (CONSULTAS_DIR, MONTAJES_DIR):
            candidata = os.path.join(carpeta, archivo)
            if os.path.exists(candidata):
                return candidata
    return None


# ──────────────────────────────────────────────────────────────────────────
# Tiempos
# ──────────────────────────────────────────────────────────────────────────

def limpiar_tiempos_busqueda():
    """Quita filas previas `*__clip|openclip|siglip` para no duplicar."""
    if not os.path.exists(TIEMPOS_CSV):
        return
    sufijos = tuple(f"__{m['clave']}" for m in MODELOS)
    with open(TIEMPOS_CSV, "r", encoding="utf-8") as f:
        lector = csv.DictReader(f)
        filas = [
            (row["consulta"], row.get("tiempo_segundos", ""))
            for row in lector if not str(row.get("consulta", "")).endswith(sufijos)
        ]
    with open(TIEMPOS_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["consulta", "tiempo_segundos"])
        writer.writerows(filas)


def registrar_tiempo(consulta, segundos):
    existe = os.path.exists(TIEMPOS_CSV)
    with open(TIEMPOS_CSV, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if not existe or os.path.getsize(TIEMPOS_CSV) == 0:
            writer.writerow(["consulta", "tiempo_segundos"])
        writer.writerow([consulta, round(float(segundos), 4)])


# ──────────────────────────────────────────────────────────────────────────
# Evaluación
# ──────────────────────────────────────────────────────────────────────────

def extraer_embeddings(features):
    if torch.is_tensor(features):
        return features
    for attr in ("image_embeds", "pooler_output"):
        if hasattr(features, attr):
            return getattr(features, attr)
    raise TypeError(f"No se pudo extraer el embedding del retorno: {type(features)}")


def cargar_indice(cfg):
    embeddings = np.load(cfg["indice"])
    ids = np.load(IDS_PATH, allow_pickle=True)
    if len(ids) != len(embeddings):
        sys.exit(
            f"Error: {cfg['indice']} ({len(embeddings)} filas) y {IDS_PATH} "
            f"({len(ids)}) no coinciden. Ejecutar generar_indices_comparativos.py."
        )
    return embeddings.astype(np.float32), ids


def evaluar(cfg, consultas, device):
    """Devuelve (metricas_global, metricas_por_categoria, filas_revision)."""
    indice, ids = cargar_indice(cfg)
    modelo = cfg["modelo_cls"].from_pretrained(cfg["checkpoint"]).to(device)
    processor = cfg["processor_cls"].from_pretrained(cfg["checkpoint"])
    modelo.eval()

    filas_revision = []
    aciertos = {"top1": 0, "top5": 0, "n": 0}
    tiempos = []
    por_categoria = {}

    for c in consultas:
        ruta = resolver_ruta(c)
        consulta = c["consulta"]
        categoria = c.get("categoria", "desconocida")
        id_correcto = str(c.get("id_correcto", ""))

        if ruta is None:
            print(f"  [OMITIDA] {consulta}: imagen no encontrada")
            continue

        try:
            imagen = Image.open(ruta).convert("RGB")
        except Exception as e:
            print(f"  [OMITIDA] {consulta}: no se pudo abrir ({e})")
            continue

        t0 = time.perf_counter()
        inputs = processor(images=[imagen], return_tensors="pt")
        inputs = {k: v.to(device) for k, v in inputs.items()}
        with torch.no_grad():
            q = extraer_embeddings(modelo.get_image_features(**inputs))[0]
        q = q / q.norm()
        sims = indice @ q.cpu().numpy()
        orden = np.argsort(sims)[::-1][:TOP_K]
        tiempo_busqueda = time.perf_counter() - t0

        top5_ids = [str(ids[i]) for i in orden]
        scores = [float(sims[i]) for i in orden]
        top1_ok = bool(top5_ids) and top5_ids[0] == id_correcto
        top5_ok = id_correcto in top5_ids

        aciertos["top1"] += int(top1_ok)
        aciertos["top5"] += int(top5_ok)
        aciertos["n"] += 1
        tiempos.append(tiempo_busqueda)
        por_categoria.setdefault(categoria, {"top1": 0, "top5": 0, "n": 0})
        por_categoria[categoria]["top1"] += int(top1_ok)
        por_categoria[categoria]["top5"] += int(top5_ok)
        por_categoria[categoria]["n"] += 1
        registrar_tiempo(f"{consulta}__{cfg['clave']}", tiempo_busqueda)

        for pos, (rid, score) in enumerate(zip(top5_ids, scores), start=1):
            filas_revision.append({
                "modelo": cfg["clave"],
                "consulta": consulta,
                "categoria": categoria,
                "id_correcto": id_correcto,
                "posicion": pos,
                "resultado_id": rid,
                "score": round(score, 4),
                "clasificacion_humana": "Correcto" if rid == id_correcto else "",
                "observacion": "",
            })

    n = max(1, aciertos["n"])
    metricas_global = {
        "modelo": cfg["clave"], "categoria": "global", "n_consultas": aciertos["n"],
        "top1_correctos": aciertos["top1"],
        "precision_top1": round(100 * aciertos["top1"] / n, 2),
        "top5_correctos": aciertos["top5"],
        "precision_top5": round(100 * aciertos["top5"] / n, 2),
        "tiempo_busqueda_prom_ms": round(1000 * (sum(tiempos) / n), 2) if tiempos else 0.0,
    }
    metricas_por_categoria = []
    for categoria, m in sorted(por_categoria.items()):
        n_cat = max(1, m["n"])
        metricas_por_categoria.append({
            "modelo": cfg["clave"], "categoria": categoria, "n_consultas": m["n"],
            "top1_correctos": m["top1"],
            "precision_top1": round(100 * m["top1"] / n_cat, 2),
            "top5_correctos": m["top5"],
            "precision_top5": round(100 * m["top5"] / n_cat, 2),
            "tiempo_busqueda_prom_ms": "",
        })

    print(f"  {cfg['etiqueta']}: Top1={aciertos['top1']}/{aciertos['n']} "
          f"({metricas_global['precision_top1']:.1f}%)  "
          f"Top5={aciertos['top5']}/{aciertos['n']} "
          f"({metricas_global['precision_top5']:.1f}%)  "
          f"tiempo prom={metricas_global['tiempo_busqueda_prom_ms']:.0f} ms")
    return metricas_global, metricas_por_categoria, filas_revision


def main():
    print("=" * 72)
    print("SALA 4 - EVALUACIÓN DE 50 CONSULTAS (CLIP / OpenCLIP / SigLIP)")
    print("=" * 72)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Dispositivo: {device}")

    consultas = cargar_conjunto_prueba()
    if not consultas:
        sys.exit("Error: el conjunto de prueba está vacío.")
    print(f"Consultas de prueba: {len(consultas)} "
          f"(desde {TEST_SET_JSON})")

    limpiar_tiempos_busqueda()

    filas_metricas = []
    filas_revision = []
    for cfg in MODELOS:
        if not os.path.exists(cfg["indice"]):
            sys.exit(
                f"Error: no existe {cfg['indice']}. "
                "Ejecutar primero scripts/generar_indices_comparativos.py"
            )
        print(f"\n=== {cfg['etiqueta']} ===")
        globales, por_categoria, revision = evaluar(cfg, consultas, device)
        filas_metricas.append(globales)
        filas_metricas.extend(por_categoria)
        filas_revision.extend(revision)

    # ── evaluation_metrics.csv (reporte técnico) ──
    columnas = ["modelo", "categoria", "n_consultas", "top1_correctos",
                "precision_top1", "top5_correctos", "precision_top5",
                "tiempo_busqueda_prom_ms"]
    with open(EVAL_METRICS_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=columnas)
        writer.writeheader()
        writer.writerows(filas_metricas)

    # ── revision_humana_50.csv (estructura de revisión cualitativa) ──
    columnas_rev = ["modelo", "consulta", "categoria", "id_correcto", "posicion",
                    "resultado_id", "score", "clasificacion_humana", "observacion"]
    with open(REVISION_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=columnas_rev)
        writer.writeheader()
        writer.writerows(filas_revision)

    print("\n" + "=" * 72)
    print("RESUMEN GLOBAL (precision_top1 / precision_top5)")
    print("=" * 72)
    for m in filas_metricas:
        if m["categoria"] == "global":
            print(f"  {m['modelo']:<10s} Top1={m['precision_top1']:6.2f}%  "
                  f"Top5={m['precision_top5']:6.2f}%  ({m['n_consultas']} consultas)")
    print(f"Reporte técnico : {EVAL_METRICS_CSV}")
    print(f"Revisión humana : {REVISION_CSV}")
    print(f"Tiempos anexados: {TIEMPOS_CSV}")


if __name__ == "__main__":
    main()
