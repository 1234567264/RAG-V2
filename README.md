# WebScraping — RAG Visual (Hito 2)

Plataforma de búsqueda visual de camisetas deportivas basada en **embeddings CLIP/OpenCLIP/SigLIP**. El proyecto scrapea catálogos de *Designs Aimari*, consolida y normaliza un dataset, convierte cada imagen en un vector, y expone una API que devuelve el **Top 5 de diseños visualmente más parecidos** a una imagen cargada. Todo se presenta en una interfaz Streamlit.

> **Hito 2 — Búsqueda visual robusta:** una camiseta puede encontrarse aunque la consulta no sea idéntica al banco (sin marco, recoloreada, recortada, mockup o persona), y el Top 5 pasa por un reranking visual para que tenga coherencia humana (Sala 4 compara modelos y Sala 3 mejora el motor).

## Flujo del sistema

```text
[Scraper]  →  data/images/  (imágenes crudas)
                │
[consolidar.py] → data/products.csv + data/images_final/   (Sala 1)
                │
[normalizar_imagenes.py] → data/images_normalized/   (Sala 1, Hito 2)
                │
[generar_embeddings.py] → data/embeddings.npy + data/ids.npy   (Sala 4, Hito 1)
[generar_indices_comparativos.py] → embeddings_clip/openclip/siglip.npy sobre images_normalized/   (Sala 4, Hito 2)
                │
[preprocesar_consulta.py] → prepara la imagen de consulta (Sala 2, Hito 2)
                │
[FastAPI api/main.py] → POST /search/image (modos) + /search/image/v2 (índice normalizado + reranking) + GET /health   (Sala 3)
                │
[Streamlit frontend/app.py] → sube imagen, antes/después, Top 5, compara H1 vs H2 y registra evaluación   (Sala 2)
```

## Requisitos previos

- **Python 3.10+** (probado con 3.13).
- Conexión a internet (para descargar el modelo CLIP de Hugging Face y scrapear el sitio).

## Instalación

Desde la raíz del proyecto:

```bash
# 1) (Opcional) Entorno virtual
python -m venv venv
# Windows:
venv\Scripts\activate
# macOS / Linux:
source venv/bin/activate

# 2) Instalar dependencias
pip install -r requirements.txt
```

> La primera vez que se ejecuta, el modelo `openai/clip-vit-base-patch32` se descarga a `~/.cache/huggingface` (~350 MB).

## Ejecución paso a paso

El flujo completo es: **scrapear → consolidar → generar embeddings → levantar API → levantar interfaz**.

### 1. Scrapear el catálogo

```bash
python main.py --paginas 1-20 --imagenes 1000 --modo fresh
```

**Parámetros de `main.py`:**

| Parámetro | Valores | Descripción |
|---|---|---|
| `--paginas` | `1-20`, `1,2,3`, `all` | Páginas del catálogo a scrapear. Un rango se escribe `inicio-fin`. `all` scrapea todo. |
| `--imagenes` | número o `all` | Cantidad máxima de imágenes/productos a descargar. |
| `--modo` | `fresh` o `update` | `fresh` **borra `data/` y re-descarga todo desde cero**. `update` fusiona con los productos existentes (evita re-descargar). |

Este paso genera:
- `data/productos.json` — datos crudos del scraping.
- `data/images/` — las 1000 imágenes descargadas (nombres originales).
- `data/metadata.json` — metadatos de paginación.
- `data/productos.xlsx` — exportación Excel de respaldo.

> En Windows usa `--paginas "1-20"` entre comillas si tu shell interpreta el guion.

### 2. Consolidar el dataset (Sala 1)

```bash
python scripts/consolidar.py
```

Lee `data/productos.json` + `data/images/` y genera:
- `data/products.csv` — dataset canónico (`id, proveedor, pagina, imagen, nombre_original, url`).
- `data/images_final/` — imágenes renombradas con nomenclatura uniforme `AIM-PXXX-NNN.ext`.

Valida nomenclatura, duplicados, archivos existentes y apertura de imagen.

### 3. Validar el dataset (opcional pero recomendado)

```bash
python scripts/validate_dataset.py
python scripts/validate_dataset.py --benchmark   # mide tiempo en 1000 registros
```

Reporta: registros totales/válidos, IDs duplicados, nombres vacíos, URLs vacías/repetidas, extensiones inválidas, imágenes faltantes/dañadas y duplicados por hash MD5.

### 4. Generar los embeddings (Sala 4)

```bash
python scripts/generar_embeddings.py
```

Lee `products.csv` en orden, abre cada imagen de `images_final/`, genera su vector con **CLIP** (`openai/clip-vit-base-patch32`), lo normaliza con L2 y guarda:
- `data/embeddings.npy` — matriz `(N, 512)`.
- `data/ids.npy` — IDs alineados por posición con los embeddings.

> La correspondencia posición ↔ ID es obligatoria: si se altera el orden, el sistema devolvería nombres asociados a la imagen equivocada.

### 5. Levantar la API (Sala 3)

```bash
python -m uvicorn api.main:app --port 8000
```

Al iniciar carga el índice y el modelo CLIP una sola vez. Endpoints:

- `GET /health` — estado, cantidad de productos/embeddings y modelo.
- `POST /search/image` — recibe una imagen (multipart) y el `modo` de búsqueda (formulario). Devuelve el **Top 5** y, en los modos que preparan la consulta, además la imagen preparada, ambos rankings (Hito 1 y Hito 2) y el detalle del preprocesamiento (Sala 2, Hito 2).
- `POST /search/image/v2` — igual, pero con el **motor del Hito 2** (recuperación amplia + reranking por color/regiones/estructura + umbral dinámico). Cada resultado incluye `score_inicial`, `score_color_global`, `score_color_frente`, `score_color_espalda`, `score_estructura`, `score_reranking`, `posicion_final` y `modelo_utilizado`.

**Modos de `POST /search/image` (Sala 2):** `auto` (prepara la consulta y devuelve respuesta enriquecida), `procesada` (siempre usa la imagen preparada, Hito 2), `original` (siempre usa la consulta tal cual, Hito 1), `completo` (Sala 2 + reranking de Sala 3) y `legacy` (solo la lista del motor).

Prueba rápida desde otra terminal:

```bash
curl -X POST -F "file=@data/images_final/AIM-P001-001.jpg" http://localhost:8000/search/image
```

### 6. Levantar la interfaz (Sala 2)

```bash
streamlit run frontend/app.py
```

Abre `http://localhost:8501` en el navegador:
1. En el sidebar verifica "API OK · 1000 productos · 1000 embeddings".
2. Elige el **modo de búsqueda** en el sidebar (auto / procesada / original / completo / legacy).
3. Sube una imagen (JPG/JPEG/PNG).
4. Revisa la vista **antes/después** (consulta original vs preparada por Sala 2) y el Top 5 (imagen, ID, nombre, proveedor, URL, score).
5. En los modos con preparación, compara los rankings **Hito 1 vs Hito 2**.
6. Clasifica cada resultado (**Correcto / Útil, pero no duplicado / Incorrecto**) y guarda la evaluación → `data/evaluation.csv`.

### 7. Normalizar el banco de imágenes (Sala 1 — Hito 2)

Transforma las tarjetas del catálogo en imágenes limpias y estandarizadas (solo frente + espalda, sin cabecera, pie/URL, marcos ni logos), sin tocar las originales:

```bash
# a) Analizar formatos del banco (Actividad 1, muestra >= 100)
python scripts/analizar_formatos.py                 # → data/informe_formatos.txt
# b) Normalizar las 1000 imágenes (Actividad 2-4)
python scripts/normalizar_imagenes.py               # → data/images_normalized/
# c) Revisión objetiva de la muestra de 50 (Actividad 5)
python scripts/revisar_muestra_50.py                # → data/revision_humana_50.csv
```

Genera:
- `data/images_normalized/` — 1000 imágenes `AIM-Pxxx-NNN.jpg` (mismo ID que `images_final/`).
- `data/informe_normalizacion.txt` + `data/detalle_normalizacion.csv` — procesadas/fallidas, recortes correctos/incorrectos, tiempos y casos a revisar.
- `data/informe_formatos.txt` + `data/detalle_formatos.csv` — formatos visuales, posición de marcos/cabecera/pie/URL, ubicación de frente y espalda, % recortable.
- `data/revision_humana_50.csv` + `data/revision_contact_sheet.png` — muestra aleatoria de 50 con clasificación y hoja de contacto para el visto bueno visual.

### 8. Motor mejorado y reranking del Top 5 (Sala 3 — Hito 2)

El motor del Hito 1 (`POST /search/image` con `modo=original`) sigue disponible para comparar. El motor del Hito 2 se expone en `POST /search/image/v2`: recuperación amplia (Top 30) + reranking combinando el score CLIP con color HSV global, color por regiones frente/espalda y estructura del patrón, más umbral dinámico (puede devolver 1, 3 o 5 resultados según la calidad):

```bash
python -m uvicorn api.main:app --port 8000
# POST /search/image/v2 -> resultados con: score_inicial, score_color_global,
#   score_color_frente, score_color_espalda, score_estructura, score_reranking,
#   posicion_final, modelo_utilizado
```

### 9. Preparación de la consulta (Sala 2 — Hito 2)

El módulo `api/preprocesar_consulta.py` limpia la imagen del usuario ANTES de generar el embedding (el problema contrario al de Sala 1: Sala 1 limpia el banco, Sala 2 limpia la consulta):

```bash
# a) Generar el conjunto común de 50 consultas (10 diseños × 5 versiones)
python scripts/generar_consultas_hito2.py        # → data/consultas/ + evaluation/consultas_hito2.csv
# b) Evaluar Hito 1 vs Hito 2 sobre las 50 consultas
python scripts/evaluar_hito2.py                  # → data/resultados_hito2.csv + data/resumen_hito2.txt
# c) Evidencia: montajes antes/después + coherencia del Top 5
python scripts/evidencia_hito2.py                # → data/montajes/ + data/evidencia_coherencia_hito2.txt
```

La API guarda por cada consulta la versión original y la procesada en `data/queries_original/` y `data/queries_procesadas/`.

**Prueba integrada común (50 consultas) y comparación Hito 1 vs Hito 2:**

```bash
# Con la API corriendo, comparar ambos motores con las mismas consultas
python scripts/compare_hito1_hito2.py             # → data/comparacion_hito1_hito2.csv + .json
```

El comparador mide Top 1, Top 5 y tiempos por motor y por categoría. Resultados reales de Sala 2 (50 consultas, ids corrigidos): Hito 1 Top 1 32/50 (64%) · Hito 2 Top 1 30/50 (60%) · auto 35/50 (70%); con el motor normalizado de Sala 3: H1 30/50 vs H2 32/50 (ver `REPORTES_HITO2.md`).

### 10. Comparación de modelos y embeddings (Sala 4 — Hito 2)

Determina qué modelo representa mejor la similitud visual de camisetas deportivas usando exactamente las mismas imágenes normalizadas de Sala 1:

```bash
# a) Generar los TRES índices sobre data/images_normalized/ (1000 imágenes cada uno)
python scripts/generar_indices_comparativos.py        # → data/embeddings_clip.npy · embeddings_openclip.npy · embeddings_siglip.npy
# b) Evaluar los tres modelos contra el conjunto común de 50 consultas
python scripts/evaluar_50_consultas.py                # → data/evaluation_metrics.csv (Top1/Top5) + data/revision_humana_modelos_top5.csv
```

Resultado real (50 consultas, índice normalizado): CLIP Top1 70% · OpenCLIP 84% · **SigLIP 92% (ganador, 46/50 Top 1)**; tiempos de generación: CLIP 42 s · OpenCLIP 44 s · SigLIP 162 s (detalle en `data/evaluation_metrics.csv` y `REPORTES_HITO2.md`).

El motor Hito 2 de Sala 3 (`/search/image/v2`) ya recupera contra `embeddings_clip.npy` (índice normalizado) para mantener la coherencia vector ↔ imagen; el índice CLIP del Hito 1 (`embeddings.npy`, con marco) queda como baseline de comparación.

## Evaluación de las 20 pruebas (Sala 2)

El plan está en `evaluation/test_plan.csv` (grupos A–D) y las imágenes de consulta en `evaluation/test_images/`.

```bash
# Métricas (Precisión Top 1 y Top 5, falsos positivos/negativos, tiempos)
python scripts/reporte_metricas.py
```

Genera `data/reporte_evaluacion.xlsx` y la tabla Consulta | Top 1 correcto | Top 5 útiles | Observación.

## Estructura del proyecto

```text
WebScraping/
├── api/                 # FastAPI + motores de búsqueda (Sala 3)
│   ├── main.py           #   endpoints /search/image (modos, Sala 2), /search/image/v2 (Hito 2) y /health
│   ├── search_engine.py  #   carga índice y search_similar(top_k=5) (Hito 1)
│   ├── search_engine_hito2.py # recuperación amplia (índice normalizado Sala 4) + reranking (Hito 2, Sala 3)
│   └── preprocesar_consulta.py # preparación de la consulta del usuario (Sala 2, Hito 2)
├── frontend/
│   └── app.py           # Interfaz Streamlit (Sala 2: antes/después, modos, comparación H1 vs H2)
├── data/
│   ├── images/          # Imágenes crudas del scraping (fuente, legacy)
│   ├── images_final/    # Imágenes con ID uniforme (entregable Sala 1)
│   ├── images_normalized/ # Imágenes normalizadas frente+espalda (Sala 1, Hito 2)
│   ├── consultas/       # 50 consultas de prueba (Sala 2, Hito 2)
│   ├── queries_original/   # Consultas originales guardadas por la API (Sala 2, Hito 2)
│   ├── queries_procesadas/ # Consultas preparadas guardadas por la API (Sala 2, Hito 2)
│   ├── montajes/        # Antes/después (Sala 2, Hito 2)
│   ├── productos.csv    # Dataset canónico
│   ├── embeddings.npy   # Vectores CLIP sobre images_final (Sala 4, Hito 1)
│   ├── embeddings_clip.npy      # Vectores CLIP sobre images_normalized (Sala 4, Hito 2)
│   ├── embeddings_openclip.npy  # Vectores OpenCLIP sobre images_normalized (Sala 4, Hito 2)
│   ├── embeddings_siglip.npy    # Vectores SigLIP 768d sobre images_normalized (Sala 4, Hito 2)
│   ├── ids.npy          # IDs alineados con embeddings
│   ├── consultas_test_50.json   # Conjunto de prueba de Sala 4 (50 consultas con id_correcto verificado)
│   ├── evaluation_metrics.csv   # Top1/Top5 por modelo (Sala 4, Hito 2)
│   ├── revision_humana_modelos_top5.csv # Clasificación humana Top5 por modelo (Sala 4, Hito 2)
│   ├── evaluation.csv   # Resultado de las evaluaciones (Sala 2)
│   ├── tiempos.csv      # Tiempo por consulta (Sala 4 incluye generacion_*)
│   ├── resultados_hito2.csv      # Resultados Hito 1 vs Hito 2 por consulta (Sala 2, Hito 2)
│   ├── resumen_hito2.txt         # Top 1/Top 5 por regla y categoría (Sala 2, Hito 2)
│   ├── evidencia_coherencia_hito2.txt # Coherencia del Top 5 (Sala 2, Hito 2)
│   ├── comparacion_hito1_hito2.csv  # Comparación H1 vs H2 por consulta (Sala 3, Hito 2)
│   ├── comparacion_hito1_hito2.json # Resumen Top 1/Top 5/tiempos (Sala 3, Hito 2)
│   ├── informe_normalizacion.txt  # Resultados de la normalización (Sala 1)
│   ├── detalle_normalizacion.csv  # Estado por imagen (Sala 1)
│   ├── informe_formatos.txt       # Análisis de formatos del banco (Sala 1)
│   ├── detalle_formatos.csv       # Estructura por imagen (Sala 1)
│   ├── revision_humana_50.csv     # Clasificación de la muestra de 50 (Sala 1)
│   ├── informe_revision_humana.txt # Resultados de las 50 revisiones (Sala 1)
│   └── revision_contact_sheet.png # Hoja de contacto original|normalizada (Sala 1)
├── scripts/             # consolidar, validar, normalizar, analizar formatos, embeddings, índices comparativos (Sala 4), evaluación, reportes, hito2
├── scraper/             # Engine de scraping (main.py lo usa)
├── utils/               # helpers, pagination, limits, update
├── storage/             # exportación a Excel
├── config/              # configuración del scraper
├── evaluation/          # consultas_hito2.csv + INFORME_SALA2_HITO2.md + test_plan.csv + test_images/
├── requirements.txt     # Dependencias del proyecto
├── main.py              # Punto de entrada del scraper
├── TRABAJO.md           # Consigna oficial del proyecto
├── REPORTES.md          # Auditoría del estado vs TRABAJO.md
├── REPORTES_HITO2.md    # Reporte del Hito 2 (las 4 salas completas)
└── README.md            # Este documento
```

## Archivos generados clave

| Archivo | Contenido |
|---|---|
| `data/products.csv` | 1000 filas: `id, proveedor, pagina, imagen, nombre_original, url` |
| `data/embeddings.npy` | Matriz `(1000, 512)` float32, normalizada L2 (CLIP, banco con marco, Hito 1) |
| `data/embeddings_clip.npy` | Matriz `(1000, 512)` CLIP sobre `images_normalized/` (Sala 4, Hito 2) |
| `data/embeddings_openclip.npy` | Matriz `(1000, 512)` OpenCLIP sobre `images_normalized/` (Sala 4, Hito 2) |
| `data/embeddings_siglip.npy` | Matriz `(1000, 768)` SigLIP sobre `images_normalized/` (Sala 4, Hito 2, ganador) |
| `data/ids.npy` | 1000 IDs en el mismo orden que los embeddings |
| `data/evaluation_metrics.csv` | Top 1/Top 5 por modelo y categoría (Sala 4, Hito 2) |
| `data/evaluation.csv` | Evaluación de las 20 consultas (5 filas por consulta) |
| `data/reporte_evaluacion.xlsx` | Resumen por consulta |
| `data/images_normalized/` | 1000 imágenes normalizadas `AIM-Pxxx-NNN.jpg` (Sala 1, Hito 2) |
| `data/informe_normalizacion.txt` | Estadísticas de la normalización (Sala 1, Hito 2) |
| `data/informe_formatos.txt` | Análisis de formatos del banco (Sala 1, Hito 2) |
| `data/revision_humana_50.csv` | Clasificación de las 50 revisiones (Sala 1, Hito 2) |
| `data/revision_humana_modelos_top5.csv` | Top 5 por consulta y modelo para clasificación humana (Sala 4, Hito 2) |

> **Nota sobre archivos legacy:** `data/index_embeddings.npy` y `data/index_metadata.json` son de `scripts/build_index.py` (fuera del flujo integrado). El flujo del Hito 1 usa únicamente `embeddings.npy` + `ids.npy`.

## Solución de problemas

- **`ModuleNotFoundError`**: instala las dependencias (`pip install -r requirements.txt`).
- **La API no responde en `/health`**: verifica que esté corriendo (`python -m uvicorn api.main:app --port 8000`). La interfaz muestra el error en el sidebar.
- **El validador reporta imágenes faltantes**: asegúrate de haber corrido `consolidar.py` (el validador apunta a `data/images_final/`).
- **Errores de codificación en consola (Windows)**: usa `set PYTHONIOENCODING=utf-8` antes de ejecutar, o activa la consola UTF-8.
- **Primera ejecución lenta**: la descarga del modelo CLIP y de las imágenes toma unos minutos.

## Próximos pasos

- Calibrar la clasificación humana de los grupos C y D para alcanzar el ≥70% de Top 5 útil del supervisor.
- Migrar el índice a **PostgreSQL + pgvector** (o FAISS) para persistencia, filtros y concurrencia al escalar.
- Fase siguiente del RAG: usar un LLM con los resultados recuperados para **proponer nombres y etiquetas**.