# AGENTS.md — Reglas de trabajo para la IA en este repositorio

> La IA DEBE leer este archivo al inicio de cada sesión y seguirlo.
> La fuente de verdad de los requisitos es el archivo **`TRABAJO.md`**
> ubicado en la raíz del proyecto. Este archivo resume sus reglas operativas.

## 1. Antes de tocar código: leer el docx

Al comenzar cada sesión, la IA DEBE extraer y revisar el contenido de
`TRABAJO.md`. 
El trabajo siempre debe alinearse con lo que pide ese documento, no con suposiciones.

## 2. Objetivo del proyecto

Motor de búsqueda visual RAG para camisetas deportivas:

1. Se sube una imagen de consulta.
2. CLIP genera su embedding.
3. El motor busca en el **índice único**.
4. La API devuelve Top 5 con ID, nombre, imagen, URL y score.
5. La interfaz muestra los resultados y registra evaluación.

Frase de validación: «Una imagen se carga una sola vez, se procesa con un solo
modelo, se compara contra un solo índice y los resultados se muestran en una
sola interfaz.»

## 3. Estructura canónica (NO crear copias ni rutas alternativas)

```
proyecto/
├── api/
│   ├── main.py                 # API FastAPI (endpoints /search/image y /health)
│   ├── search_engine.py        # motor Hito 1 (embeddings.npy + ids.npy + products.csv)
│   └── search_engine_hito2.py  # motor Hito 2 (recuperación amplia + reranking)
├── data/
│   ├── products.csv            # ÚNICA fuente de productos
│   ├── embeddings.npy          # ÚNICO índice de vectores (Hito 1)
│   ├── ids.npy                 # alineado posición a posición con embeddings.npy
│   ├── embeddings_clip.npy     # índice normalizado de Sala 4 (Hito 2)
│   ├── images_original/        # originales (NO modificar ni borrar)
│   ├── images_normalized/      # banco limpio (Sala 1, Hito 2)
│   └── images_final/           # banco usado por el índice del Hito 1
├── frontend/
│   └── app.py                  # Streamlit = cliente PURO de la API
├── scripts/                    # validación, embeddings, evaluación, etc.
├── requirements.txt
└── README.md
```

PROHIBIDO crear archivos tipo `index_embeddings.npy`, `embeddings_productos.npy`,
`embeddings_final_v2.npy` o duplicar rutas. Los únicos índices son los listados
arriba.

## 4. Contrato común de datos

- `products.csv` con columnas exactas: `id,proveedor,pagina,imagen,nombre_original,url`.
- `imagen` contiene SOLO el nombre de archivo (ej. `AIM-P001-001.jpg`).
- `ids.npy` debe conservar el MISMO orden que `embeddings.npy`
  (posición 0 → id 0, etc.). Si se desalinea, el sistema devuelve nombres
  incorrectos. SIEMPRE validar la alineación al cargar.
- Nomenclatura de IDs: `AIM-P001-001` (patrón `AIM-P###-NNN`).

## 5. Arquitectura de referencia

- **Un solo modelo CLIP:** `openai/clip-vit-base-patch32` (en código se usa
  `SentenceTransformer("clip-ViT-B-32")`).
- **Índice Hito 1:** `data/embeddings.npy` + `data/ids.npy` + `products.csv`
  (generados por `scripts/generate_embeddings.py` sobre `images_final`).
- **Índice Hito 2 (Sala 4):** `data/embeddings_clip.npy` + `data/ids.npy`
  generados por `scripts/generar_indices_comparativos.py` sobre
  `images_normalized`. El motor Hito 2 lo usa y, si no existe, cae al Hito 1.
- **Motor Hito 2:** recuperación amplia (30 candidatos) + reranking visual
  (color HSV por regiones frente/espalda, estructura 32×32, color dominante,
  gama, patrón, marco, franjas) + umbral dinámico (puede devolver < top_k).
- **La interfaz NO genera embeddings ni busca localmente.** Solo consume la API.

## 6. Contrato de respuesta

`POST /search/image` (form-data: `file` + `modo`) devuelve una lista de
objetos con al menos:

```json
[
  {
    "id": "AIM-P001-001",
    "nombre": "Guadalcacin Blue",
    "imagen": "AIM-P001-001.jpg",
    "url": "https://...",
    "proveedor": "Aimari",
    "score": 0.82,
    "score_reranking": 0.85,
    "posicion_final": 1,
    "modelo_utilizado": "clip+color+estructura+patron+marco+franjas"
  }
]
```

`GET /health` devuelve: `status`, `products`, `embeddings`, `model`,
`desfase_detectado`, `observacion`.

## 7. Modos del endpoint (Sala 2, Hito 2)

- `auto` / `completo`: prepara la consulta (Sala 2) + motor Hito 2 (reranking).
- `procesada`: imagen preparada + motor Hito 2.
- `clasico`: Hito 1 + preprocesamiento de Sala 2 (sin reranking).
- `original`: Hito 1 con la consulta tal cual llega.
- `legacy`: solo la lista del motor (comportamiento Hito 1).

## 8. Reglas de la evaluación (Hito 2)

- Mínimo 50 consultas: 10 exactas, 10 sin marco, 10 recoloreadas, 10 recortadas,
  10 mockups/personas. Cada una con su `id_correcto`.
- Métricas: Top 1 exactitud, Top 5 recuperación y calidad Top 5 humana
  (Muy similar / Similar / Poco similar / No relacionado).
- Comparación obligatoria Hito 1 vs Hito 2 sobre las MISMAS consultas.
- No llamar al score «porcentaje de coincidencia» ni «confianza»: es un
  **score de similitud**.

## 9. Manejo de errores obligatorio en la API

La API NO debe cerrarse ante:
- Sin imagen / archivo no válido → 400 `{"error": "El archivo enviado no es una imagen válida"}`.
- Imagen demasiado pequeña (mínimo 32 px por lado) → 400 con mensaje claro.
- Falta `embeddings.npy`, falta `products.csv`, IDs desalineados, modelo no
  carga → 500 con mensaje, sin matar el servidor.
- Una imagen de un candidato que no puede abrirse: puntuar 0 en visuales, no
  romper la búsqueda.

## 10. Flujo de trabajo estándar para cada tarea

1. Leer este archivo y el docx si aplica.
2. Explorar el código existente ANTES de modificar (buscar patrones, no asumir).
3. Implementar en la estructura canónica, sin duplicar motores ni índices.
4. Verificar: `python -m py_compile` de los archivos tocados y probar la API
   con `curl` (subir una imagen real de `data/consultas/`).
5. Correr lint/typecheck si existe; si no, compilar.
6. Actualizar `AI_LOG.md` con el prompt de IA usado (requisito del proyecto).
7. NO commitear a menos que lo pida el usuario explícitamente.

## 11. Medio ambiente de ejecución (Linux/Arch, shell fish)

- No usar pip del sistema (PEP 668). Usar el venv: `source .venv/bin/activate.fish`.
- La API se levanta con: `uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload`.
- La interfaz con: `streamlit run frontend/app.py`.
- El torch instalado es la build CPU (sin NVIDIA), por la falta de GPU y por
  espacio en `/tmp` (tmpfs). No reinstalar torch CUDA.
- Si falta espacio al instalar, apuntar `TMPDIR=/var/tmp` (el disco tiene ~400 GB).
- El usuario usa fish: los comandos de activación de venv son `.fish`, y
  «source .venv/bin/activate» falla.
