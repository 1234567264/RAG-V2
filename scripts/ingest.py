import argparse
import json
import os
from datetime import datetime

import numpy as np
import pandas as pd

# ─────────────────────────────────────────────
# Rutas base (relativas a la raíz WebScraping/)
# ─────────────────────────────────────────────
DATADIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data"))
CSVPATH = os.path.join(DATADIR, "products.csv")
JSONPATH = os.path.join(DATADIR, "metadata.json")
EMBEDDINGSPATH = os.path.join(DATADIR, "embeddings.npy")

# Ruta del CSV products generado por Sala 1 (consolidar.py)
CSV_SALA1_PATH = os.path.join(
    os.path.dirname(__file__), "..", "data", "products.csv"
)
CSV_SALA1_PATH = os.path.abspath(CSV_SALA1_PATH)

# Columnas que produce consolidar.py y que search.py espera
COLUMNAS_REQUERIDAS = ["id", "proveedor", "pagina", "imagen", "nombre_original", "url"]


# ─────────────────────────────────────────────
# 1. FUNCIONES DE ESCRITURA (sin cambios de contrato)
# ─────────────────────────────────────────────

def GuardarProductos_csv(df_productos: pd.DataFrame, csv_path: str = CSVPATH):
    """
    Guarda el DataFrame de productos como CSV.
    Campos requeridos: id, proveedor, pagina, imagen, nombre_original, url
    """
    os.makedirs(os.path.dirname(csv_path), exist_ok=True)
    df_productos.to_csv(csv_path, index=False, encoding="utf-8")
    print(f"[Ingest] Guardados {len(df_productos)} productos en {csv_path}")


def GuardarEmbeddings(matrix_embeddings: np.ndarray, embeddings_path: str = EMBEDDINGSPATH):
    """
    Guarda la matriz de embeddings (N_productos × Dimensión) en formato .npy.
    Los vectores se normalizan a float32 para facilitar la similitud coseno
    mediante producto punto directo en search.py.

    NOTA: Este método es llamado por Sala 4 cuando entrega los embeddings CLIP reales.
    No sobreescribe embeddings.npy si ya existe y no se llama explícitamente.
    """
    os.makedirs(os.path.dirname(embeddings_path), exist_ok=True)
    matrix = np.array(matrix_embeddings, dtype=np.float32)

    # Normalización L2 para que dot(a, b) == cosine_similarity(a, b)
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    matrix_normalized = matrix / norms

    np.save(embeddings_path, matrix_normalized)
    print(
        f"[Ingest] Guardados {matrix_normalized.shape[0]} embeddings "
        f"de dimensión {matrix_normalized.shape[1]} en {embeddings_path}"
    )


# ─────────────────────────────────────────────
# 2. FLUJO REAL — leer desde products.csv (Sala 1)
# ─────────────────────────────────────────────

def CargarDesdeSala1(csv_path: str = CSV_SALA1_PATH) -> pd.DataFrame:
    """
    Lee data/products.csv generado por consolidar.py (Sala 1) y
    devuelve un DataFrame con las columnas que search.py espera.

    Columnas de entrada (products.csv):
        id, proveedor, pagina, imagen, nombre_original, url

    Las mismas se conservan sin transformación; solo se valida que existan.
    """
    if not os.path.exists(csv_path):
        raise FileNotFoundError(
            f"[Ingest] No se encontró '{csv_path}'.\n"
            "Ejecuta primero:\n"
            "  python scripts/consolidar.py"
        )

    df = pd.read_csv(csv_path, encoding="utf-8")

    # Verificar que el CSV tenga todas las columnas necesarias
    faltantes = [c for c in COLUMNAS_REQUERIDAS if c not in df.columns]
    if faltantes:
        raise ValueError(
            f"[Ingest] El archivo '{csv_path}' le faltan columnas: {faltantes}\n"
            "Verifica que consolidar.py esté actualizado."
        )

    # Limpieza defensiva: eliminar filas sin id o sin imagen
    antes = len(df)
    df = df.dropna(subset=["id", "imagen"])
    eliminadas = antes - len(df)
    if eliminadas > 0:
        print(f"[Ingest] ⚠️  Se eliminaron {eliminadas} filas con id o imagen vacíos.")

    print(f"[Ingest] Cargados {len(df)} productos desde '{csv_path}'")
    return df


def IngestarDatosReales():
    """
    Flujo principal de Sala 3:
    1. Lee products.csv (Sala 1)
    2. Revalida/mantiene products.csv (contrato con search.py y Sala 4)
    3. Actualiza metadata.json (embeddings_disponibles = false hasta que Sala 4 entregue CLIP)
    """
    df = CargarDesdeSala1()
    GuardarProductos_csv(df)
    GenerarMetadata(df)
    print("[Ingest] ✅ Flujo real completado. Listo para recibir embeddings de Sala 4.")


# ─────────────────────────────────────────────
# 3. METADATA
# ─────────────────────────────────────────────

def GenerarMetadata(df: pd.DataFrame, metadata_path: str = JSONPATH):
    """
    Crea o actualiza data/metadata.json con información del dataset real.

    Campos generados:
    - total_productos      : cantidad de filas en el CSV
    - proveedor            : valor del campo 'proveedor' (o 'Desconocido' si varía)
    - fecha_generacion     : timestamp ISO 8601 del momento de ejecución
    - columnas             : lista de columnas del CSV
    - ruta_csv             : ruta del products.csv
    - ruta_embeddings      : ruta del embeddings.npy
    - embeddings_disponibles: false hasta que Sala 4 llame a GuardarEmbeddings()

    Si el archivo ya existe se conserva 'embeddings_disponibles' del estado anterior
    (para no borrar el flag cuando Sala 4 ya lo activó).
    """
    os.makedirs(os.path.dirname(metadata_path), exist_ok=True)

    # Conservar flag de embeddings si el JSON ya existe
    embeddings_disponibles = False
    if os.path.exists(metadata_path):
        try:
            with open(metadata_path, "r", encoding="utf-8") as f:
                metadata_existente = json.load(f)
            embeddings_disponibles = metadata_existente.get("embeddings_disponibles", False)
        except (json.JSONDecodeError, IOError):
            pass  # archivo corrupto o vacío → se sobreescribe desde cero

    # Proveedor: si todos los registros tienen el mismo, lo reportamos
    proveedores_unicos = df["proveedor"].dropna().unique().tolist() if "proveedor" in df.columns else []
    proveedor_str = proveedores_unicos[0] if len(proveedores_unicos) == 1 else str(proveedores_unicos)

    metadata = {
        "total_productos": int(len(df)),
        "proveedor": proveedor_str,
        "fecha_generacion": datetime.now().isoformat(timespec="seconds"),
        "columnas": list(df.columns),
        "ruta_csv": CSVPATH,
        "ruta_embeddings": EMBEDDINGSPATH,
        "embeddings_disponibles": embeddings_disponibles,
    }

    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=4, ensure_ascii=False)

    print(f"[Ingest] metadata.json actualizado → {metadata_path}")
    print(f"         total_productos      : {metadata['total_productos']}")
    print(f"         proveedor            : {metadata['proveedor']}")
    print(f"         fecha_generacion     : {metadata['fecha_generacion']}")
    print(f"         embeddings_disponibles: {metadata['embeddings_disponibles']}")


# ─────────────────────────────────────────────
# 4. MODO DEMO — solo para smoke test / desarrollo
# ─────────────────────────────────────────────

def InicializarDatosDemo(n_samples: int = 20, dim: int = 512):
    """
    Genera un dataset y embeddings sintéticos para pruebas rápidas
    sin depender del scraper ni de Sala 4.

    ⚠️  Solo disponible con:  python scripts/ingest.py --demo
    No se ejecuta en el flujo real de producción.
    """
    print(f"[Ingest] ⚠️  MODO DEMO — generando {n_samples} productos sintéticos (dim={dim})...")

    productos = []
    for i in range(1, n_samples + 1):
        prod_id = f"AIM-P001-{i:03d}"
        productos.append({
            "id": prod_id,
            "proveedor": "Designs Aimari",
            "pagina": 1,
            "imagen": f"{prod_id}.jpg",
            "nombre_original": f"Camiseta Deportiva Modelo #{i}",
            "url": f"https://designsaimari.com/{prod_id}",
        })

    df = pd.DataFrame(productos)
    GuardarProductos_csv(df)

    # Vectores sintéticos aleatorios normalizados
    embeddings_dummy = np.random.randn(n_samples, dim).astype(np.float32)
    GuardarEmbeddings(embeddings_dummy)

    GenerarMetadata(df)
    print("[Ingest] ✅ Dataset demo generado exitosamente.")


# ─────────────────────────────────────────────
# 5. ENTRYPOINT
# ─────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Sala 3 — Ingesta de datos para búsqueda vectorial RAG"
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Genera datos sintéticos de prueba en lugar de usar products.csv"
    )
    args = parser.parse_args()

    if args.demo:
        InicializarDatosDemo(n_samples=20, dim=512)
    else:
        IngestarDatosReales()
