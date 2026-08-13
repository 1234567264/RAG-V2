
import os
import pandas as pd
import numpy as np

DATADIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data"))
CSVPATH = os.path.join(DATADIR, "products.csv")
EMBEDDINGSPATH = os.path.join(DATADIR, "embeddings.npy")


def CargarDatosVectoriales(csvPath: str = CSVPATH, embeddingsPath: str = EMBEDDINGSPATH):
    """Carga el CSV de productos"""

    if not os.path.exists(csvPath):
        raise FileNotFoundError(f"No se encontró el archivo de metadata en {csvPath}")
    if not os.path.exists(embeddingsPath):
        raise FileNotFoundError(f"No se encontró el archivo de embeddings en {embeddingsPath}")
        
    df_products = pd.read_csv(csvPath)
    embeddings = np.load(embeddingsPath)
    
    return df_products, embeddings

def BuscarSimilares(
    vector_query: list | np.ndarray,
    k: int = 5,
    csvPath: str = CSVPATH,
    embeddingsPath: str = EMBEDDINGSPATH
) -> list[dict]:

    df_products, embeddings = CargarDatosVectoriales(csvPath, embeddingsPath)
    
    v_query = np.array(vector_query, dtype=np.float32).flatten()
    
    dim_database = embeddings.shape[1]
    if v_query.shape[0] != dim_database:
        raise ValueError(f"Dimensión del vector de consulta ({v_query.shape[0]}) no coincide con la base de datos ({dim_database})")
        
    # Normalizar vector de consulta para Similitud Cosine
    norm_q = np.linalg.norm(v_query)
    if norm_q > 0:
        v_query = v_query / norm_q
    
    scores = np.dot(embeddings, v_query)
    
    # Obtener los índices de los Top K puntuaciones de mayor a menor
    top_k_indices = np.argsort(scores)[::-1][:k]
    
    resultados = []
    for idx in top_k_indices:
        row = df_products.iloc[idx]
        score_val = float(scores[idx])
        
        similitud_porcentaje = max(0.0, float((score_val + 1.0) / 2.0)) if score_val < 0 else min(1.0, float(score_val))
        
        resultados.append({
            "id": str(row.get("id", "")),
            "nombre": str(row.get("nombre_original", row.get("nombre", ""))),
            "imagen": str(row.get("imagen", "")),
            "url": str(row.get("url", "")),
            "score": round(similitud_porcentaje, 4)
        })
        
    return resultados

if __name__ == "__main__":
    print("[Search] Ejecutando prueba local de búsqueda vectorial...")
    try:
        df, embs = CargarDatosVectoriales()
        print(f"[Search] Cargados {len(df)} productos y {embs.shape[0]} embeddings.")
        
        # Generar un vector de prueba usando el primer producto con un pequeño ruido
        query_vector = embs[0] + np.random.normal(0, 0.05, size=embs.shape[1])
        
        top5 = BuscarSimilares(query_vector, k=5)
        print("\n TOP 5 RESULTADOS SIMILARES \n")
        for i, res in enumerate(top5, 1):
            print(f"{i}. ID: {res['id']} | Score: {res['score']:.4f} ({res['score']*100:.2f}%) | Nombre: {res['nombre']}")
            print(f"   Imagen: {res['imagen']} | URL: {res['url']}")
    except FileNotFoundError as e:
        print(f"[Search] Archivos no encontrados: {e}")
        print("[Search] Ejecuta primero 'python scripts/ingest.py' para generar datos de prueba.")
