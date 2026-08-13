import base64
import io
import os
import sys
import time
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone

import numpy as np
from PIL import Image
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sentence_transformers import SentenceTransformer

# Asegurar importación del módulo search_engine independientemente del working directory
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from api.search_engine import cargar_indice, info_indice, search_similar
from api.search_engine_hito2 import (
    search_similar_reranked,
    search_similar_reranked_fusion,
)
from api.preprocesar_consulta import preparar_consulta

MODEL_NAME = "clip-ViT-B-32"  # equivalente a openai/clip-vit-base-patch32
_model = None

# Modelos de embeddings disponibles en el motor Hito 2 (Sala 4). "clip" es el
# estándar del proyecto; "openclip" es la mejora solicitada: más robusto a
# franjas/dibujos centrales y variaciones de diseño. "fusion" combina CLIP +
# OpenCLIP + SigLIP en la recuperación (lo más robusto a oclusiones). Los
# índices se generan con scripts/generar_indices_comparativos.py.
MODELOS_VALIDOS = ("clip", "openclip", "fusion")
MODELOS_ETIQUETA = {
    "clip": "openai/clip-vit-base-patch32",
    "openclip": "laion/CLIP-ViT-B-32-laion2B-s34B-b79K",
    "fusion": "fusion(clip+openclip+siglip)",
}
_openclip = None  # (modelo, processor) de transformers, lazy
_siglip = None    # (modelo, processor) de transformers, lazy


def get_openclip():
    """Singleton del modelo OpenCLIP (laion/CLIP-ViT-B-32-laion2B-s34B-b79K)
    vía transformers. Carga perezosa: solo cuando se usa modelo=openclip."""
    global _openclip
    if _openclip is None:
        try:
            import torch
            from transformers import CLIPModel, CLIPProcessor

            modelo = CLIPModel.from_pretrained(MODELOS_ETIQUETA["openclip"])
            processor = CLIPProcessor.from_pretrained(MODELOS_ETIQUETA["openclip"])
            modelo.eval()
            _openclip = (modelo, processor)
            print(f"[API] Modelo OpenCLIP '{MODELOS_ETIQUETA['openclip']}' "
                  f"cargado correctamente (torch {torch.__version__}).")
        except Exception as e:
            raise RuntimeError(
                f"No se pudo cargar el modelo OpenCLIP: {e}"
            ) from e
    return _openclip


def get_siglip():
    """Singleton del modelo SigLIP (google/siglip-base-patch16-224) vía
    transformers. Carga perezosa: solo cuando se usa modelo=fusion."""
    global _siglip
    if _siglip is None:
        try:
            import torch
            from transformers import SiglipModel, SiglipImageProcessor

            modelo = SiglipModel.from_pretrained("google/siglip-base-patch16-224")
            processor = SiglipImageProcessor.from_pretrained(
                "google/siglip-base-patch16-224"
            )
            modelo.eval()
            _siglip = (modelo, processor)
            print(f"[API] Modelo SigLIP 'google/siglip-base-patch16-224' "
                  f"cargado correctamente (torch {torch.__version__}).")
        except Exception as e:
            raise RuntimeError(f"No se pudo cargar el modelo SigLIP: {e}") from e
    return _siglip


def _embedding_openclip(imagen) -> np.ndarray:
    """Embedding L2-normalizado de la imagen con OpenCLIP (transformers).
    La salida de get_image_features puede ser un tensor o un objeto
    BaseModelOutputWithPooling; se extrae el campo image_embeds como en
    scripts/generar_indices_comparativos.py para mantener coherencia."""
    import torch

    modelo, processor = get_openclip()
    inputs = processor(images=imagen, return_tensors="pt")
    with torch.no_grad():
        features = modelo.get_image_features(**inputs)
    if not torch.is_tensor(features):
        features = getattr(features, "image_embeds", None) or features.pooler_output
    features = features / features.norm(p=2, dim=-1, keepdim=True)
    return features.cpu().numpy().astype(np.float32)[0]


def _embedding_siglip(imagen) -> np.ndarray:
    """Embedding L2-normalizado de la imagen con SigLIP (transformers).
    Misma extracción que en scripts/generar_indices_comparativos.py."""
    import torch

    modelo, processor = get_siglip()
    inputs = processor(images=imagen, return_tensors="pt")
    with torch.no_grad():
        features = modelo.get_image_features(**inputs)
    if not torch.is_tensor(features):
        features = getattr(features, "image_embeds", None) or features.pooler_output
    features = features / features.norm(p=2, dim=-1, keepdim=True)
    return features.cpu().numpy().astype(np.float32)[0]


def _recortes_consulta(imagen):
    """Recortes de la consulta para robustez a oclusiones: imagen completa
    más los 4 cuadrantes. Si un punto tapa el diseño en una zona, el recorte
    opuesto sigue reconociendo el producto."""
    w, h = imagen.size
    mw, mh = w // 2, h // 2
    if mw == 0 or mh == 0:
        return [imagen]
    return [
        imagen,
        imagen.crop((0, 0, mw, mh)),
        imagen.crop((mw, 0, w, mh)),
        imagen.crop((0, mh, mw, h)),
        imagen.crop((mw, mh, w, h)),
    ]


def _encodificar_fusion(imagen) -> dict:
    """Embeddings multi-recorte de la imagen con los tres modelos de la
    fusión: cada modelo devuelve una lista de vectores (uno por recorte)."""
    recortes = _recortes_consulta(imagen)
    return {
        "clip": [get_model().encode(r) for r in recortes],
        "openclip": [_embedding_openclip(r) for r in recortes],
        "siglip": [_embedding_siglip(r) for r in recortes],
    }


def _encodificar(imagen, modelo: str):
    """Devuelve el embedding (o dict de embeddings en modo fusion) de la
    imagen con el modelo indicado."""
    if modelo == "openclip":
        return _embedding_openclip(imagen)
    if modelo == "fusion":
        return _encodificar_fusion(imagen)
    return get_model().encode(imagen)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Carga el índice de vectores y el modelo CLIP una sola vez al iniciar el servidor."""
    try:
        cargar_indice()
        print("[API] Índice de embeddings y dataset cargado correctamente.")
    except Exception as e:
        print(f"[API] AVISO al cargar índice: {e}")

    try:
        get_model()
        print(f"[API] Modelo CLIP '{MODEL_NAME}' cargado correctamente.")
    except Exception as e:
        print(f"[API] ERROR al cargar el modelo CLIP: {e}")

    try:
        get_openclip()
    except Exception as e:
        print(f"[API] AVISO al precalentar OpenCLIP (se cargará bajo demanda): {e}")

    try:
        get_siglip()
    except Exception as e:
        print(f"[API] AVISO al precalentar SigLIP (se cargará bajo demanda): {e}")

    yield


app = FastAPI(
    title="Motor de Búsqueda Visual RAG - Sala 3 API",
    description="API FastAPI para búsqueda e integración visual de camisetas deportivas",
    version="1.1.0",
    lifespan=lifespan,
)

# Configuración CORS para la interfaz de Sala 2 y clientes frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Parámetros del Hito 2: cuántos candidatos se recuperan en la fase amplia
# antes de hacer el reranking por color.
CANDIDATOS_INICIALES = 30

# La fusión recupera más candidatos (varios modelos = más robusto) para darle
# al reranking más chances de "resucitar" el producto correcto ocluido.
CANDIDATOS_INICIALES_FUSION = 100


def _motor_reranked(embedding, query_image, modelo: str):
    """Despacha al motor Hito 2 según el modelo elegido. `embedding` es un
    vector para clip/openclip y un dict {modelo: vector} para fusion."""
    if modelo == "fusion":
        return search_similar_reranked_fusion(
            embedding,
            query_image=query_image,
            top_k=5,
            candidatos_iniciales=CANDIDATOS_INICIALES_FUSION,
        )
    return search_similar_reranked(
        embedding,
        query_image=query_image,
        top_k=5,
        candidatos_iniciales=CANDIDATOS_INICIALES,
        modelo=modelo,
    )

# Tamaño mínimo (px por lado) para aceptar una imagen de consulta. Por debajo
# no hay píxeles suficientes para que el histograma HSV ni el descriptor de
# estructura tengan sentido, y CLIP produce vectores poco fiables.
MIN_DIM = 32

# Guardado de las dos versiones de cada consulta (Sala 2, Hito 2)
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
QUERIES_ORIGINAL_DIR = os.path.join(BASE_DIR, "data", "queries_original")
QUERIES_PROCESADA_DIR = os.path.join(BASE_DIR, "data", "queries_procesadas")


def get_model():
    """Retorna la instancia singleton del modelo CLIP, cargándolo si es necesario."""
    global _model
    if _model is None:
        _model = SentenceTransformer(MODEL_NAME)
    return _model


@app.get("/health")
def health():
    """Endpoint de verificación del estado de la API y datos indexados."""
    try:
        info = info_indice()
        indice_openclip = os.path.join(BASE_DIR, "data", "embeddings_openclip.npy")
        return {
            "status": "ok",
            "products": info["products"],
            "embeddings": info["embeddings"],
            "model": "openai/clip-vit-base-patch32",
            "desfase_detectado": info.get("desfase_detectado", False),
            "observacion": info.get("observacion", ""),
            "modelo_openclip": "laion/CLIP-ViT-B-32-laion2B-s34B-b79K",
            "indice_openclip_ok": os.path.exists(indice_openclip),
            "modelos_fusion": ["openai/clip-vit-base-patch32",
                               "laion/CLIP-ViT-B-32-laion2B-s34B-b79K",
                               "google/siglip-base-patch16-224"],
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "detail": str(e)}
        )


def _imagen_b64(imagen) -> str:
    """Codifica una imagen PIL en base64 (JPEG)."""
    buf = io.BytesIO()
    imagen.convert("RGB").save(buf, "JPEG", quality=90)
    return base64.b64encode(buf.getvalue()).decode("ascii")


def _guardar_versiones(query_id, original, procesada):
    """Guarda la consulta original y la procesada para comparar resultados."""
    os.makedirs(QUERIES_ORIGINAL_DIR, exist_ok=True)
    os.makedirs(QUERIES_PROCESADA_DIR, exist_ok=True)
    original.save(os.path.join(QUERIES_ORIGINAL_DIR, f"{query_id}.jpg"), "JPEG", quality=92)
    procesada.save(os.path.join(QUERIES_PROCESADA_DIR, f"{query_id}.jpg"), "JPEG", quality=92)


def _error_dimensiones(imagen) -> str | None:
    """Devuelve un mensaje de error si la imagen es demasiado pequeña (None si ok)."""
    w, h = imagen.size
    if min(w, h) < MIN_DIM:
        return (
            f"La imagen es demasiado pequeña ({w}x{h}); se requiere un mínimo "
            f"de {MIN_DIM}px por lado para una búsqueda fiable."
        )
    return None


@app.post("/search/image")
async def search_image(
    file: UploadFile = File(...),
    modo: str = Form("auto"),
    modelo: str = Form("clip"),
):
    """
    Recibe una imagen (JPG/PNG) y devuelve los 5 productos más parecidos.

    Parametro de formulario `modo` (Sala 2, Hito 2):
      - "auto"      : pipeline completo (Sala 1 + Sala 2 + Sala 3): prepara la
                      consulta y aplica el reranking visual del motor Hito 2.
                      Respuesta enriquecida (original + procesada + ambos
                      rankings + preprocesamiento + modelo).
      - "completo"  : igual que "auto" (alias del pipeline completo).
      - "procesada" : usa la imagen preparada (Sala 2) con el motor Hito 2.
      - "clasico"   : Hito 1 (Sala 1 + preprocesamiento Sala 2), sin reranking.
      - "original"  : fuerza el uso de la consulta tal como llega (motor Hito 1).
      - "legacy"    : devuelve solo la lista del motor (comportamiento Hito 1).

    Parametro de formulario `modelo`:
      - "clip"     (default): openai/clip-vit-base-patch32 (estándar).
      - "openclip"           : laion/CLIP-ViT-B-32-laion2B-s34B-b79K (mejora;
                               más robusto a franjas/dibujos centrales).
      - "fusion"             : combina CLIP + OpenCLIP + SigLIP en la
                               recuperación (lo más robusto a oclusiones:
                               un punto que tape parte del diseño).
      Solo aplica a los modos del motor Hito 2 (auto/completo/procesada);
      los modos Hito 1 (clasico/original/legacy) siempre usan "clip".
    """
    if file.content_type and file.content_type not in ("image/jpeg", "image/jpg", "image/png"):
        return JSONResponse(
            status_code=400,
            content={"error": "El archivo enviado no es una imagen válida"}
        )

    try:
        contenido = await file.read()
        imagen = Image.open(io.BytesIO(contenido)).convert("RGB")
    except Exception:
        return JSONResponse(
            status_code=400,
            content={"error": "El archivo enviado no es una imagen válida"}
        )

    error_dim = _error_dimensiones(imagen)
    if error_dim:
        return JSONResponse(status_code=400, content={"error": error_dim})

    if modelo not in MODELOS_VALIDOS:
        return JSONResponse(
            status_code=400,
            content={"error": f"Modelo desconocido '{modelo}'; modelos válidos: "
                     f"{', '.join(MODELOS_VALIDOS)}"}
        )
    if modelo in ("openclip", "fusion") and modo in ("legacy", "original", "clasico"):
        return JSONResponse(
            status_code=400,
            content={"error": "Los modelos OpenCLIP y fusion solo aplican a los "
                     "modos del motor Hito 2 (auto/completo/procesada); los modos "
                     "clasico/original/legacy usan el Hito 1 con CLIP."}
        )

    try:
        model = get_model()
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": f"Error al cargar el modelo CLIP: {str(e)}"}
        )

    try:
        t0 = time.perf_counter()
        etiqueta_modelo = MODELOS_ETIQUETA[modelo]
        if modo == "legacy":
            embedding = _encodificar(imagen, "clip")
            return search_similar(embedding, top_k=5)

        if modo == "original":
            # Hito 1 con la consulta tal cual llega, sin preprocesar (ruta
            # rápida usada por la comparación Hito 1 vs Hito 2).
            embedding = _encodificar(imagen, "clip")
            res_original = search_similar(embedding, top_k=5)
            return {
                "query_id": f"q_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}",
                "modo": "original",
                "modelo": etiqueta_modelo,
                "preprocesamiento": {
                    "ok": False, "pasos": [], "backend": None,
                    "bbox": None, "recorte_pct": None, "tiempo_segundos": None,
                },
                "tiempo_segundos": round(time.perf_counter() - t0, 3),
                "resultados": res_original,
            }

        prep = preparar_consulta(imagen)
        procesada = prep["procesada"]

        # Comparaciones Hito 1 (índice CLIP openai) solo en modo clip: con
        # OpenCLIP no tiene sentido mezclar su embedding contra el índice H1.
        # En los demás modos solo se calcula el embedding de la consulta
        # preparada (ahorra ~50% del cómputo en fusion, que usa multi-recorte).
        res_original = None
        res_procesada = None
        if modelo == "clip":
            emb_original = _encodificar(imagen, modelo)
            emb_procesada = _encodificar(procesada, modelo)
            res_original = search_similar(emb_original, top_k=5)
            res_procesada = search_similar(emb_procesada, top_k=5)
        else:
            emb_procesada = _encodificar(procesada, modelo)

        query_id = f"q_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
        _guardar_versiones(query_id, imagen, procesada)

        if modo in ("completo", "auto"):
            # Pipeline completo: Sala 1 + Sala 2 + Sala 3 (mejor Top 5).
            # La respuesta incluye resultados_original/procesada para comparar
            # (solo en modo clip: son comparaciones contra el índice del Hito 1).
            modo_usado = "completo"
            resultados = _motor_reranked(emb_procesada, procesada, modelo)
        elif modo == "clasico":
            # Hito 1 con el preprocesamiento de Sala 2 (sin reranking)
            modo_usado = "clasico"
            resultados = search_similar(_encodificar(procesada, "clip"), top_k=5)
        else:
            # "procesada", "auto" y cualquier modo no reconocido: motor Hito 2
            # sobre la consulta preparada (recuperación amplia + reranking).
            modo_usado = "procesada" if modo == "procesada" else "completo"
            resultados = _motor_reranked(emb_procesada, procesada, modelo)

        return {
            "query_id": query_id,
            "modo": modo_usado,
            "modelo": etiqueta_modelo,
            "preprocesamiento": {
                "ok": True,
                "pasos": prep["pasos"],
                "backend": prep["backend"],
                "bbox": prep["bbox"],
                "recorte_pct": prep["recorte_pct"],
                "tiempo_segundos": prep["tiempo_segundos"],
            },
            "tiempo_segundos": round(time.perf_counter() - t0, 3),
            "imagen_original_b64": _imagen_b64(imagen),
            "imagen_procesada_b64": _imagen_b64(procesada),
            "resultados": resultados,
            "resultados_original": res_original,
            "resultados_procesada": res_procesada,
        }
    except FileNotFoundError as e:
        return JSONResponse(
            status_code=500,
            content={"error": f"Falta un archivo de datos: {str(e)}"}
        )
    except ValueError as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": f"Error interno: {str(e)}"}
        )


@app.post("/search/image/v2")
async def search_image_v2(
    file: UploadFile = File(...),
    modelo: str = Form("clip"),
):
    """
    Hito 2: Motor mejorado con reranking por color HSV.
    Recibe la imagen igual que /search/image, pero en vez de devolver el
    top 5 directo de CLIP, hace una recuperación amplia de
    CANDIDATOS_INICIALES y reordena combinando el score de embeddings con el
    score del histograma HSV de la imagen real (recuperación amplia +
    reranking + umbral dinámico, ver api/search_engine_hito2.py).

    Parametro de formulario `modelo`:
      - "clip"     (default): openai/clip-vit-base-patch32.
      - "openclip"           : laion/CLIP-ViT-B-32-laion2B-s34B-b79K (más
                               robusto a franjas/dibujos centrales).
      - "fusion"             : combina CLIP + OpenCLIP + SigLIP (lo más
                               robusto a oclusiones: puntos que tapen diseño).
    """
    # Mismo control de tipo de archivo que el endpoint del Hito 1
    if file.content_type and file.content_type not in ("image/jpeg", "image/jpg", "image/png"):
        return JSONResponse(
            status_code=400,
            content={"error": "El archivo enviado no es una imagen válida"}
        )

    try:
        contenido = await file.read()
        imagen = Image.open(io.BytesIO(contenido)).convert("RGB")
    except Exception:
        return JSONResponse(
            status_code=400,
            content={"error": "El archivo enviado no es una imagen válida"}
        )

    error_dim = _error_dimensiones(imagen)
    if error_dim:
        return JSONResponse(status_code=400, content={"error": error_dim})

    if modelo not in MODELOS_VALIDOS:
        return JSONResponse(
            status_code=400,
            content={"error": f"Modelo desconocido '{modelo}'; modelos válidos: "
                     f"{', '.join(MODELOS_VALIDOS)}"}
        )

    try:
        model = get_model()
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": f"Error al cargar el modelo CLIP: {str(e)}"}
        )

    try:
        t0 = time.perf_counter()
        embedding = _encodificar(imagen, modelo)
        resultados = _motor_reranked(embedding, imagen, modelo)
        tiempo_segundos = round(time.perf_counter() - t0, 4)
        return {
            "resultados": resultados,
            "tiempo_segundos": tiempo_segundos,
            "candidatos_evaluados": (
                CANDIDATOS_INICIALES_FUSION if modelo == "fusion"
                else CANDIDATOS_INICIALES
            ),
            "modelo": MODELOS_ETIQUETA[modelo],
        }
    except FileNotFoundError as e:
        return JSONResponse(
            status_code=500,
            content={"error": f"Falta un archivo de datos: {str(e)}"}
        )
    except ValueError as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": f"Error interno: {str(e)}"}
        )
