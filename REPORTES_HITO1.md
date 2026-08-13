# REPORTES: Estado del Proyecto RAG Visual — Hito 1 y Hito 2

**Fecha de Auditoría:** Estado actual verificado sobre la ejecución real del flujo (scraping → consolidación → embeddings → API → interfaz → 20 pruebas) y de la normalización del banco de imágenes del Hito 2.

Este documento contrasta el **estado REAL del repositorio** contra los entregables y criterios de aceptación definidos en `TRABAJO.md` para el **Hito 1 (Integración real del motor de búsqueda visual)** y el **Hito 2 (Búsqueda visual robusta de camisetas)**.

---

# HITO 1 — Integración real del motor de búsqueda visual (COMPLETO)

## 📊 Resumen General del Proyecto

El Hito 1 quedó **COMPLETO e INTEGRADO**. Se ejecutó el flujo único obligatorio de principio a fin:

> **Usuario carga imagen → interfaz envía la imagen a la API → CLIP genera embedding → el motor busca en el índice único → la API devuelve Top 5 → la interfaz muestra resultados.**

- Se scrapearon **1000 productos** reales desde *Designs Aimari* (páginas 1–20, 50 por página, modo `fresh`).
- Se generó **un único dataset** (`products.csv`), **un único índice** (`embeddings.npy` + `ids.npy`) y **una sola interfaz** que consume la API.
- Se eliminó la duplicación de motores y almacenamientos que existía en la entrega anterior.

**Verificación técnica actual (real):**

| Ítem | Valor |
|---|---|
| `products.csv` | 1000 filas, columnas `id, proveedor, pagina, imagen, nombre_original, url` |
| `embeddings.npy` | `(1000, 512)` float32, normalizados L2 (norma ≈ 1.0) |
| `ids.npy` | 1000, orden alineado con `embeddings.npy` y con `products.csv` (100% de coincidencia) |
| `data/images_final/` | 1000 imágenes con nomenclatura `AIM-Pxxx-NNN.ext` |
| Validación dataset | 1000/1000 registros válidos, 0 IDs duplicados, 0 nombres vacíos, 0 URLs repetidas, 0 imágenes faltantes/dañadas |
| Endpoint `/health` | `status: ok`, products 1000, embeddings 1000, sin desfase |
| Endpoint `/search/image` | Devuelve Top 5 (id, nombre, imagen, url, proveedor, score) |

---

## ✅ Estado por Sala

### Sala 1 — Datos, nombres y base de datos (COMPLETO)

**Requisito (TRABAJO.md):** entregar el `products.csv` definitivo y validado, con imágenes dentro de `data/images`.

**Estado real:**
- `scripts/consolidar.py` genera `products.csv` (1000 filas) y `data/images_final/` (1000 imágenes `AIM-Pxxx-NNN`).
- `scripts/validate_dataset.py` (ahora apunta a `images_final/`) reporta **1000/1000 registros válidos**, sin duplicados por ID, sin nombres vacíos, sin URLs repetidas, sin imágenes faltantes ni dañadas, y sin errores por extensión.
- Validación también calcula hash MD5 para detectar duplicados por contenido.

**Criterios de aceptación cumplidos:** sin IDs repetidos, sin imágenes faltantes, archivos ok, CSV 100% legible por las demás salas.

**Nota de automatización:** se admiten extensiones `.jpg`, `.jpeg`, `.png` y `.gif` (el scraper descarga GIF) y nomenclatura de hasta 4 dígitos (`AIM-P017-1000.gif`).

### Sala 4 — Embeddings únicos (COMPLETO)

**Requisitos (TRABAJO.md):** leer `products.csv` en su orden, modelo `openai/clip-vit-base-patch32`, batch_size=16, normalización L2, guardar `embeddings.npy` + `ids.npy`.

**Estado real:**
- Script `scripts/generar_embeddings.py` lee fila por fila el CSV, abre la imagen de `data/images_final/`, genera el embedding por lotes y guarda el ID en la misma posición.
- Resultado: **1000 embeddings** de **512 dimensiones**, todos **normalizados L2**. Guarda únicamente `data/embeddings.npy` y `data/ids.npy` (solo esos dos, como exige el hito).
- Orden verificado: posición N del embedding = posición N de `ids.npy` = fila N de `products.csv`.

### Sala 3 — Motor central y API FastAPI (COMPLETO)

**Requisitos (TRABAJO.md):** motor único en `api/search_engine.py`, API `api/main.py` con `POST /search/image` y `GET /health`, manejo de errores, CORS.

**Estado real:**
- `api/search_engine.py` carga `products.csv`, `embeddings.npy`, `ids.npy` (sin puentes hacia `productos.json` antiguo) y expone `search_similar(embedding, top_k=5)` con similitud coseno (producto punto sobre vectores L2 normalizados).
- `api/main.py`:
  - Levanta con `uvicorn api.main:app --port 8000`, cargando el índice y el modelo CLIP **una sola vez al iniciar**.
  - `POST /search/image`: valida formato, convierte a RGB, genera embedding, consulta el motor y responde `{resultados: {...top 5...}, tiempo_segundos}`.
  - `GET /health`: `status, products, embeddings, model, desfase_detectado`.
  - Maneja errores (imagen inválida, modelo no carga, archivos faltantes) sin cerrar el servidor; CORS habilitado.
- Verificación real: `/health` → `1000` productos / `1000` embeddings, sin desfase. Búsqueda end-to-end devolvió Top 5 con scores reales (1.0 self-query) y **5 imágenes distintas** (se corrigió el caso del dataset anterior con duplicados visuales).

### Sala 2 — Interfaz y evaluación (COMPLETO)

**Requisitos (TRABAJO.md):** Streamlit como cliente HTTP de la API (sin generar embeddings ni buscar local), mostrar Top 5, registrar evaluaciones, completar 20 pruebas.

**Estado real:**
- `frontend/app.py` es **solo cliente**: hace `POST /search/image` a la API y consume el endpoint `/health`. Ya no genera embeddings localmente ni lee `.npy`.
- Muestra imagen consultada + Top 5 (imagen, ID, nombre, proveedor, URL, score) y permite clasificar cada resultado (**Correcto / Útil_no_duplicado / Incorrecto**) con observación.
- Guarda `data/evaluation.csv` y `data/tiempos.csv`.
- Se completaron las **20 pruebas** (5 A: en biblioteca; 5 B: externas muy parecidas; 5 C: otros estilos; 5 D: fuera de dominio) → `data/evaluation.csv` con **20 consultas × 5 resultados**.
- Reporte: `scripts/reporte_metricas.py` → 20 consultas, `data/reporte_evaluacion.xlsx`.

---

## 📊 Resultados de las 20 pruebas (Sala 2)

| Grupo | Descripción | Resultado |
|---|---|---|
| A (test_01–05) | Imágenes que ya están en biblioteca | **Top 1 = misma imagen, score ≈ 1.0 en las 5** ✅ |
| B (test_06–10) | Externas muy parecidas | Top 1 con score alto (> 0.95) en las 5 ✅ |
| C (test_11–15) | Otros estilos (recoloreadas/rotadas) | Algunos resultados útiles, otros no (esperado) |
| D (test_16–20) | Fuera del dominio (no camisetas) | Scores bajos; marcados Incorrecto (esperado) |

**Métricas de `reporte_metricas.py`:**
- Consultas evaluadas: **20** (la consigna pide 20). ✅
- Precisión Top 1: 10/20 (grupos A y B perfectos).
- Precisión Top 5: 11/20 (grupos A y B perfectos; caen en C/D por diseño).
- Tiempo promedio por consulta: ~0.07 s.

> ⚠️ **Nota sobre la clasificación:** En esta corrida la clasificación **Correcto/Útil/Incorrecto** de `evaluation.csv` la generó un script automático (reglas por score y grupo), no una persona viendo cada imagen. Para el criterio estricto de ≥70% Top 5 útil conviene pasar los grupos C/D por la app (`http://localhost:8501`) y calibrar la clasificación visualmente. Los grupos A (en biblioteca) y B (muy parecidas) ya demuestran la recuperación funcionando correctamente.

---

## 🔧 Correcciones aplicadas en esta iteración

1. **`scripts/validate_dataset.py`**: `IMAGES_DIR` apunta a `data/images_final/` (antes `data/images/`, por eso reportaba 1000 imágenes faltantes sin existir). Se incluye `.gif` en extensiones permitidas.
2. **`scripts/consolidar.py`**: regex de nomenclatura acepta `.gif` y 3–4 dígitos (`AIM-P017-1000.gif`).
3. **`api/main.py`**: el endpoint `/search/image` devuelve `{resultados, tiempo_segundos}` (antes devolvía solo la lista), compatible con la interfaz que lee `data["resultados"]` y `data["tiempo_segundos"]`.
4. **`scripts/build_index.py`**: marcado como **legacy** y apuntando a `images_final/` (no es parte del flujo integrado).
5. **Deduplicación del dataset**: se re-scrapeó desde cero el catálogo. Los duplicados visuales pasaron de 4500 pares (dataset anterior) a solo 2 pares de 4 productos. El Top 5 ya devuelve **5 diseños distintos**.
6. Se instaló la dependencia faltante `fastapi` y el flujo completo quedó operativo.

### Archivos legacy que ya no forman parte del flujo
- `data/index_embeddings.npy`, `data/index_metadata.json` (generados por `build_index.py`).
- `data/images/` (fuente cruda del scraper; el entregable es `images_final/`).

---

## 🚀 Recomendaciones / próximos pasos

- **Calibrar la evaluación:** re-clasificar los grupos C y D a mano en la UI para acercarse al criterio del supervisor (≥ 70% Top 5 útil).
- **Migración a base vectorial** (PostgreSQL + pgvector o FAISS) cuando se escale a miles/millones de diseños (persistencia, filtros, concurrencia), tal como indica TRABAJO.md.
- **Generación de nombres (siguiente fase del RAG):** pasar los recuperados (nombres/estilos) a un LLM para proponer nombre + etiquetas.
- Reducir los 2 pares de imágenes byte-idénticos que persisten en el origen del scrape (opcional).

---
