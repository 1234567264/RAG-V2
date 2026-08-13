import os
import sys
import importlib.util
import numpy as np
import pandas as pd

# Directorio base del proyecto (raíz WebScraping)
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATADIR = os.path.join(BASE_DIR, "data")

# Única ubicación de embeddings y datos en la raíz del proyecto
EMBEDDING_PATHS = [
    os.path.join(DATADIR, "embeddings.npy"),
    os.path.join(DATADIR, "index_embeddings.npy"),
]

IDSPATH = os.path.join(DATADIR, "ids.npy")
CONECTOR_PATH = os.path.join(BASE_DIR, "scripts", "conector_sala3.py")


def _get_embeddings_path():
    """Retorna la primera ruta de embeddings existente."""
    for path in EMBEDDING_PATHS:
        if os.path.exists(path):
            return path
    return EMBEDDING_PATHS[0]


def _importar_conector_sala1():
    """Importa dinámicamente cargar_productos_sala1 desde conector_sala3.py"""
    if not os.path.exists(CONECTOR_PATH):
        raise FileNotFoundError(f"No se encontró el conector de Sala 1 en: {CONECTOR_PATH}")
    spec = importlib.util.spec_from_file_location("conector_sala3", CONECTOR_PATH)
    conector = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(conector)
    return conector.cargar_productos_sala1


df = None
embeddings_norm = None
ids = None


def cargar_indice():
    """
    Carga los productos reales desde Sala 1 (data/products.csv) mediante conector_sala3.py
    y los embeddings de Sala 3.
    Lanza un ValueError descriptivo si la cantidad de productos no coincide con los embeddings.
    """
    global df, embeddings_norm, ids

    cargar_productos_sala1 = _importar_conector_sala1()
    _df = cargar_productos_sala1()

    emb_path = _get_embeddings_path()
    if not os.path.exists(emb_path):
        raise FileNotFoundError(f"Falta el archivo de embeddings en: {emb_path}")

    _embeddings = np.load(emb_path).astype(np.float32)

    # Validar coincidencia de cantidad entre productos y embeddings
    if len(_df) != _embeddings.shape[0]:
        raise ValueError(
            f"Desfase detectado: Hay {len(_df)} productos en products.csv (Sala 1) "
            f"pero {_embeddings.shape[0]} embeddings en embeddings.npy (Sala 3). "
            f"Pendiente actualización de embeddings por Sala 4."
        )

    _ids = None
    if os.path.exists(IDSPATH):
        try:
            loaded_ids = np.load(IDSPATH, allow_pickle=True)
            if len(loaded_ids) == len(_embeddings):
                _ids = loaded_ids
        except Exception:
            pass

    if _ids is None:
        if "id" in _df.columns and len(_df) == len(_embeddings):
            _ids = _df["id"].values
        else:
            _ids = np.array([str(i) for i in range(len(_embeddings))])

    if _embeddings.shape[0] != len(_ids):
        raise ValueError(
            f"Cantidad de embeddings ({_embeddings.shape[0]}) no coincide con ids ({len(_ids)})"
        )

    # Normalización L2 de la matriz de embeddings
    normas = np.linalg.norm(_embeddings, axis=1, keepdims=True)
    normas[normas == 0] = 1e-10
    _embeddings_norm = _embeddings / normas

    df, embeddings_norm, ids = _df, _embeddings_norm, _ids
    return df, embeddings_norm, ids


def search_similar(query_embedding, top_k: int = 5) -> list[dict]:
    """
    Recibe un embedding de consulta (list o np.ndarray) y devuelve el top_k de productos más similares.
    Contrato de respuesta: list de objetos con keys: id, nombre, imagen, url, proveedor, score.
    """
    if df is None or embeddings_norm is None:
        cargar_indice()

    v_query = np.array(query_embedding, dtype=np.float32).flatten()

    dim_esperada = embeddings_norm.shape[1]
    if v_query.shape[0] != dim_esperada:
        raise ValueError(
            f"El vector de consulta tiene {v_query.shape[0]} dimensiones, se esperaban {dim_esperada}"
        )

    norm_q = np.linalg.norm(v_query)
    if norm_q == 0:
        raise ValueError("El vector de consulta no puede ser un vector nulo")
    v_query = v_query / norm_q

    # Producto punto con la matriz normalizada L2 para similitud coseno
    scores = np.dot(embeddings_norm, v_query)
    top_k_idx = np.argsort(scores)[::-1][:top_k]

    resultados = []
    for idx in top_k_idx:
        row = df.iloc[idx]
        nombre = row.get("nombre_original", row.get("nombre", ""))
        imagen = row.get("imagen", row.get("archivo", ""))
        url = row.get("url", "")
        proveedor = row.get("proveedor", "Designs Aimari")

        resultados.append({
            "id": str(ids[idx]),
            "nombre": str(nombre),
            "imagen": str(imagen),
            "url": str(url),
            "proveedor": str(proveedor),
            "score": round(float(scores[idx]), 4),
        })
    return resultados


def info_indice() -> dict:
    """
    Retorna la cantidad de productos (Sala 1) y embeddings (Sala 3) actuales
    para permitir visualizar el desfase en el endpoint /health.
    """
    try:
        cargar_productos_sala1 = _importar_conector_sala1()
        df_sala1 = cargar_productos_sala1()
        num_products = len(df_sala1)
    except Exception:
        num_products = len(df) if df is not None else 0

    try:
        emb_path = _get_embeddings_path()
        if os.path.exists(emb_path):
            emb_arr = np.load(emb_path, mmap_mode="r")
            num_embeddings = int(emb_arr.shape[0])
        else:
            num_embeddings = int(embeddings_norm.shape[0]) if embeddings_norm is not None else 0
    except Exception:
        num_embeddings = int(embeddings_norm.shape[0]) if embeddings_norm is not None else 0

    info = {
        "products": num_products,
        "embeddings": num_embeddings,
    }

    if num_products != num_embeddings:
        info["desfase_detectado"] = True
        info["observacion"] = (
            f"Desfase detectado: {num_products} productos en products.csv (Sala 1) vs "
            f"{num_embeddings} embeddings en embeddings.npy (Sala 3). Pendiente entrega de Sala 4."
        )

    return info
