# AI_LOG.md - Registro de prompts de IA

> Requisito del supervisor: registrar cada prompt de IA usado en el proyecto.

## Fecha: 2026-08-07 (rama sala-2-v2)

### Prompt 1 - Interfaz como cliente puro de API
**Propósito:** Reemplazar la interfaz que hacía búsqueda local por un cliente
que SOLO consume la API de Sala 3.
**Resultado:** `frontend/app.py` — sube la imagen, hace `POST /search/image`,
muestra Top 5 (imagen, ID, nombre, proveedor, URL, score), permite clasificar cada
resultado (Correcto / Útil / Incorrecto) y guarda la evaluación en
`data/evaluation.csv`. Sin embeddings ni búsqueda local.

### Prompt 2 - Script de métricas
**Propósito:** Calcular la precisión Top 1, Top 5, falsos positivos, falsos
negativos y tiempo promedio a partir de `evaluation.csv`.
**Resultado:** `scripts/reporte_metricas.py`.

### Prompt 3 - Protocolo de evaluación (20 pruebas)
**Propósito:** Definir el plan de las 20 consultas de prueba y las imágenes del
grupo A.
**Resultado:** `evaluation/test_plan.csv`, `evaluation/README.md` y 5 imágenes de
prueba en `evaluation/test_images/`.

### Prompt 4 - Verificación de la API de Sala 3
**Propósito:** Verificar que `api/search_engine.py` (conector de
Sala 1 + embeddings de Sala 4) carga los 1000 productos y responde búsquedas.
**Resultado:** Confirmado: 1000 productos, 1000 embeddings (1000,512), búsqueda
Top-K OK.

## Fecha: 2026-08-10 (rama sala-1, Hito 2)

### Prompt 5 - Informe de formatos del banco (Actividad 1 de Sala 1)
**Propósito:** Determinar cuántos formatos visuales existen, posición de marcos,
cabecera, pie/URL, ubicación de frente y espalda, y % recortable por reglas simples,
sobre una muestra ≥100 (se analizaron las 1000).
**Resultado:** `scripts/analizar_formatos.py` → `data/informe_formatos.txt` +
`data/detalle_formatos.csv`. Hallazgos: 5 formatos (1 dominante con 99,4%),
cabecera en 99,7%, pie/URL en 99,8%, frente 17–56% y espalda 57–97% del ancho,
recorte medio estimado 48,7%.

### Prompt 6 - Revisión de la muestra de 50 (Actividad 5 de Sala 1)
**Propósito:** Completar `data/revision_humana_50.csv` (muestra aleatoria semilla 42)
con la clasificación de cada normalizada: solo frente+espalda, sin logo, sin marco,
sin cabecera/pie, sin cortes, sin deformación, lienzo uniforme.
**Resultado:** `scripts/revisar_muestra_50.py` aplica criterios objetivos de píxel
cruzados con el estado del pipeline → **49/50 correctas (98%), 1 dudosa**
(`AIM-P003-164`, espalda lisa indistinguible del fondo), 0 incorrectas.
`data/informe_revision_humana.txt` + hoja de contacto para visto bueno visual final.

## Fecha: 2026-08-10 (rama piloto, complemento Sala 3 / Hito 2)

### Prompt 7 - Bug de rutas no-ASCII en el reranking del Hito 2
**Propósito:** El motor de Sala 3 (`api/search_engine_hito2.py`) dejaba
`score_color = 0` en todas las consultas: `cv2.imread` falla silenciosamente con
rutas que contienen caracteres no-ASCII (p. ej. la carpeta `Imágenes` del perfil
de Windows).
**Resultado:** lectura de imágenes reemplazada por PIL (`Image.open` → BGR) en
`_leer_bgr_desde_ruta` y `_a_imagen_bgr`. Verificado: el reranking por color
ahora produce scores > 0 y el Top 1 es correcto en consultas exactas y sin marco.

### Prompt 8 - Reranking por regiones y estructura
**Propósito:** Complementar el reranking del Hito 2 con los criterios que pide
TRABAJO.md: comparación por regiones (frente/espalda) y distribución del patrón,
con pesos en constantes para calibrar (no asumidos).
**Resultado:** `api/search_engine_hito2.py` ahora combina 5 señales: embedding CLIP
(0,55) + color HSV global (0,15) + color frente (0,10) + color espalda (0,10) +
estructura en grises 32×32 (0,10). Respuesta ampliada con `score_color_global`,
`score_color_frente`, `score_color_espalda`, `score_estructura`, `score_reranking`,
`posicion_final` y `modelo_utilizado`.

### Prompt 9 - Comparación Hito 1 vs Hito 2 con evidencia
**Propósito:** Medir objetivamente si el motor nuevo mejora al del Hito 1 usando
las mismas consultas, con tiempos por consulta y evidencia guardada.
**Resultado:** `scripts/compare_hito1_hito2.py` (lee `evaluation/consultas_hito2.csv`,
mide Top 1/Top 5/tiempos, guarda `data/comparacion_hito1_hito2.csv` + `.json`) y
`scripts/generar_consultas_prueba.py` (genera las 20 consultas derivables:
10 exactas + 10 sin marco; documenta cómo agregar las 30 restantes).
**Resultado real sobre 20 consultas:** Hito 1: Top1 80% / Top5 100% (2 294 ms);
Hito 2: Top1 90% / Top5 95% (2 665 ms). En sin_marco el Top 1 sube de 6/10 a 8/10.

## Fecha: 2026-08-11 (integración de Sala 4 / Hito 2)

### Prompt 11 - Índices comparativos de Sala 4 sobre el banco normalizado
**Propósito:** Sala 4 ya había generado `embeddings_clip/openclip/siglip.npy`
pero desde `images_final/` (con marco), cuando TRABAJO.md exige usar exactamente
las imágenes NORMALIZADAS de Sala 1. Además el CSV apunta a `.png` mientras la
normalización entrega `.jpg` con el mismo ID.
**Resultado:** `scripts/generar_indices_comparativos.py` lee ahora de
`data/images_normalized/` con resolución de extensión (`<id>.jpg`). Re-ejecutado:
CLIP 42,2 s · OpenCLIP 43,8 s · SigLIP 161,8 s; 1000/1000 por modelo, 0 errores,
normalizados L2 (`data/tiempos.csv`).

### Prompt 12 - Evaluación de Sala 4 y colisión de archivo con Sala 1
**Propósito:** `scripts/evaluar_50_consultas.py` escribía su revisión humana en
`data/revision_humana_50.csv`, el MISMO archivo del entregable de Sala 1
(revisar_muestra_50.py), sobrescribiéndolo.
**Resultado:** la salida de Sala 4 ahora es `data/revision_humana_modelos_top5.csv`
(estructura de clasificación humana del Top 5) y se restauró el CSV de Sala 1
(49/50 correctas, 1 dudosa). Evaluación real sobre 50 consultas con índices
normalizados: **CLIP Top1 70% · OpenCLIP 84% · SigLIP 92% (ganador)**,
`data/evaluation_metrics.csv`.

### Prompt 13 - Manifest de la prueba integrada con ids incorrectos (CRÍTICO)
**Propósito:** `evaluation/consultas_hito2.csv` asignaba `id_correcto` con la
lista de patrones vieja (AIM-P001-001/-010/-025/...) que no correspondía a los
archivos reales de `data/consultas/`; la comparación H1 vs H2 daba 0/50.
**Resultado:** ids verificados por hash perceptual (coincidencia única): los 16
diseños son `AIM-P001-001..016` en orden (c01=AIM-P001-013, c06=AIM-P001-002,
c16=AIM-P001-012). Corregidos los 50 del manifest; `generar_consultas_hito2.py`
y `evidencia_hito2.py` actualizados para no volver a romperlo.

### Prompt 14 - Motor Hito 2 sobre el índice normalizado de Sala 4
**Propósito:** integrar el entregable de Sala 4 en el motor de Sala 3: el
reranking calculaba color/estructura sobre `images_final/` mientras el vector
CLIP provenía del índice Hito 1 (incoherente).
**Resultado:** `api/search_engine_hito2.py` recupera candidatos contra
`data/embeddings_clip.npy` (índice normalizado de Sala 4) con `CARPETA_IMAGENES =
images_normalized` y fallback al Hito 1 si falta el índice. `compare_hito1_hito2.py`
re-ejecutado sobre las 50 consultas: **H1 Top1 30/50 (60%) → H2 32/50 (64%);
Top5 34→37; sin_marco 8/10→10/10; recortada 5/10→10/10; tiempo por consulta
5 472→2 141 ms**; `evaluar_hito2.py` y `evidencia_hito2.py` re-ejecutados;
`REPORTES_HITO2.md`, `README.md` e `INFORME_SALA2_HITO2.md` actualizados.

## Fecha: 2026-08-11 (rama sala-2 / Hito 2) — histórico, números superados

> Nota: los resultados del Prompt 10 (35/50 · 33/50 · 37/50) usaban un manifest
> con `id_correcto` incorrectos; corregido en el Prompt 13 (números reales:
> 32/50 · 30/50 · 35/50 Top 1).

### Prompt 10 - Migración de Sala 2 a la estructura canónica del repo
**Propósito:** El supervisor marcó que `REPORTES_HITO2.md` estaba desactualizado
(decía PENDIENTE y 20/50), que los números eran inconsistentes (resumen 35/50 vs
informe 8/50), que `frontend/app.py` no enviaba `modo`, que faltaban
`data/queries_original/` y `data/queries_procesadas/`, que
`evaluation/consultas_hito2.csv` solo tenía 20 filas y que la carpeta `hito2/`
debía borrarse moviendo sus archivos a las carpetas correspondientes.
**Resultado:**
- `evaluation/consultas_hito2.csv` reconstruido a **50 filas** (10 diseños × 5
  versiones) con las imágenes reales de `data/consultas/` (nomenclatura nueva:
  `cNN_exacto.jpg`, `cNN_sin_marco.jpg`, `cNN_recoloreado.jpeg`, `cNN_recorte.jpg`,
  `cNN_cuerpo.jpeg`) y su `id_correcto`.
- Run canónico nuevo en `data/resultados_hito2.csv` + `data/resumen_hito2.txt`:
  **Hito 1 Top1 35/50 · Hito 2 Top1 33/50 · auto 37/50; Top5 38/50 · 36/50 · 39/50**.
  Borrado el set viejo (`resultados_hito2_sala2_referencia.csv`,
  `resumen_hito2_sala2.txt`, `evidencia_coherencia_sala2.txt`).
- Scripts movidos a `scripts/` con rutas canónicas: `evaluar_hito2.py`,
  `evidencia_hito2.py`, `generar_consultas_hito2.py` (leen `evaluation/consultas_hito2.csv`
  y `data/consultas/`, escriben en `data/`).
- `frontend/app.py` integra selector de modo (`auto`, `procesada`, `original`,
  `completo`, `legacy`), vista antes/después (original vs preparada) y comparación
  de rankings Hito 1 vs Hito 2.
- Generadas `data/queries_original/` (50) y `data/queries_procesadas/` (50) con la
  venv usando `api/preprocesar_consulta.py` (backend GrabCut).
- `REPORTES_HITO2.md` actualizado: Sala 2 **COMPLETO**, 50/50 consultas, métricas
  finales con los números nuevos, comparación por casos A–F y próximos pasos.
- `evaluation/INFORME_SALA2_HITO2.md` actualizado a los números nuevos y movido a
  su carpeta canónica.
- Carpeta `hito2/` eliminada por completo.

## Fecha: 2026-08-11 (Fase 3 - robustez del motor y descriptores avanzados)

### Prompt 15 - Reranking enriquecido con descriptores avanzados y API robusta
**Propósito:** reforzar el motor del Hito 2 añadiendo descriptores visuales
avanzados al score (más allá de color+estructura), corregir escalas del score
CLIP, y endurecer la API (lifespan, validación de imagen, modos correctos).
**Resultado:**
- `api/descriptores_visuales.py` (nuevo): descriptores avanzados por atributo —
  color dominante (k-means HSV), gama cromática (histograma HSV grueso), patrón
  de diseño (energía de textura en grilla), estructura con/sin marco (banda
  perimetral) y franjas/rayas + banda central. Con `similitudes_visuales()`
  (todas las similitudes en [0,1]).
- `scripts/precomputar_descriptores.py` (nuevo): precálculo de los descriptores
  avanzados de las 1000 imágenes → `data/descriptores.json` (clave `id_catalogo`).
- `api/search_engine_hito2.py`: el score_final ahora combina 10 atributos
  (embedding normalizado por consulta con min-max + color global/frente/espalda +
  estructura 32x32 + 5 descriptores avanzados) con pesos calibrables que suman 1;
  `modelo_utilizado` actualizado. Descriptores clásicos y avanzados se leen de la
  carpeta coherente con el índice activo (`images_normalized` en Hito 2,
  `images_final` en el fallback del Hito 1); se usa el precomputado cuando existe
  y on-the-fly con cache si no. Fix de correlación: dos diseños lisos (sin
  variación) ahora puntúan 1.0 en patrón/estructura en vez de 0.0.
- `api/main.py`: `on_event("startup")` (deprecado) reemplazado por
  `lifespan`; validación de dimensión mínima (32px por lado) en `/search/image`
  y `/search/image/v2`; modos corregidos — `auto`/`completo`/`procesada` usan el
  motor con reranking (Sala 1+2+3), nuevo `clasico` (Hito 1 + preprocesamiento de
  Sala 2), `original` y `legacy` sin cambios.
- Verificación: `py_compile` OK en todos los archivos tocados y test funcional de
  `descriptores_visuales` con imágenes sintéticas (auto-similitud 1.0, colores
  distintos → 0.0 en color, lisos vs rayados distinguidos por patrón/franjas).

## Fecha: 2026-08-11 (verificación integral + correcciones)

### Prompt 16 - Verificación de punta a punta del proyecto (sin commit)
**Propósito:** ejecutar el prompt de inicio de sesión (leer AGENTS.md + docx,
hacer que el proyecto funcione completo: API, motor Hito 1 + Hito 2 y frontend,
verificando con curl, registrando en AI_LOG, SIN commit ni push).
**Resultado:**
- `AGENTS.md` creado: reglas operativas para la IA, con la fuente de verdad en
  `RAG HACKATON FIN DE SEMANA .docx`.
- API levantada con la venv (torch CPU): `/health` OK (1000 productos, 1000
  embeddings, 512 dims, `desfase_detectado=false`, ids alineados con el CSV).
- `/search/image` probado con consultas reales: exacto→#2, sin_marco→#1,
  recoloreado→#1, recorte→#1, persona→fuera del Top 5 (caso difícil permitido).
- Manejo de errores OK: sin imagen→422, archivo inválido→400 con el mensaje del
  docx, imagen <32px→400 con mensaje claro.
- `data/descriptores.json` regenerado con las **1000** imágenes (antes 20),
  0 errores, 60s.
- Frontend reescrito como interfaz simple (subir imagen → Top 5); `py_compile`
  OK, Streamlit sirve HTTP 200 sin errores.
- Fix en `api/main.py`: `modo=original` es ruta rápida (0.4s, sin preprocesar);
  antes corría GrabCut + doble embedding innecesariamente.
- Fix en `scripts/compare_hito1_hito2.py`: H1 ahora llama con `modo=original`
  (el default `auto` pasó a usar el motor H2, lo que sesgaba la columna H1);
  categoría `persona` agregada al resumen (estaba como `mockup_persona`).
- Comparación H1 vs H2 regenerada (50 consultas, mismas imágenes):
  **H1 Top1 32/50 (64%) · Top5 36/50 (72%); H2 Top1 36/50 (72%) · Top5 37/50
  (74%)**. Por categoría: sin_marco 7→10 y recortada 6→10 en Top1; recoloreada
  6→7; exacta 10→8 y persona 3→1. La "regresión" en exacta es un artefacto del
  set (las exactas son copias de images_final y el índice H2 es images_normalized);
  persona es el caso difícil documentado en el docx.
- NOTA: no se hizo commit ni push.

### Prompt 17 - Integración OpenCLIP como mejora de la búsqueda (sin commit)
**Propósito:** integrar OpenCLIP (laion/CLIP-ViT-B-32-laion2B-s34B-b79K) como
modelo de embeddings opcional del motor Hito 2 para que la búsqueda reconozca
mejor diseños con franjas/dibujos centrales, usando el índice ya existente
`data/embeddings_openclip.npy` (Sala 4, 1000×512).
**Resultado:**
- `api/search_engine_hito2.py`: índice generalizado por modelo
  (`INDICES_NORMALIZADOS` con `embeddings_clip.npy` / `embeddings_openclip.npy`,
  cache por modelo en `_cache_indices`). `cargar_indice_normalizado(modelo)`,
  `buscar_en_indice_normalizado(..., modelo)` y `search_similar_reranked(...,
  modelo)`. Si falta el índice openclip → ValueError con instrucción de
  generación (sin fallback silencioso); para "clip" se conserva el fallback al
  índice Hito 1. `modelo_utilizado` responde `openclip+color+estructura+...`.
- `api/main.py`: parámetro de formulario `modelo` (`clip` default | `openclip`)
  en `/search/image` y `/search/image/v2`; encoder lazy de OpenCLIP vía
  transformers (`get_openclip`/`_embedding_openclip`) precalentado en lifespan;
  extracción del embedding coherente con `extraer_embeddings` del script de
  índices (el checkpoint devuelve `BaseModelOutputWithPooling`; se usa
  `image_embeds` o `pooler_output`). `modelo=openclip` solo válido en modos Hito 2
  (auto/completo/procesada); en H1 (clasico/original/legacy) → 400 con mensaje.
  En modo openclip no se devuelven `resultados_original/procesada` (serían
  mezclas contra el índice CLIP del Hito 1). `/health` expone
  `modelo_openclip` e `indice_openclip_ok`.
- `frontend/app.py`: radio CLIP/OpenCLIP (OpenCLIP por defecto) que envía
  `modelo`; la caption muestra el modelo usado.
- `scripts/compare_hito1_hito2.py`: flag `--openclip` agrega el motor `h2oc`
  (endpoint `/search/image/v2` con `modelo=openclip`) como columna y en el
  resumen por categoría.
- Evaluación (50 consultas, 3 motores, mismas imágenes):
  **H1 Top1 32/50 (64%) · Top5 36/50 (72%)**
  **H2 (CLIP) Top1 36/50 (72%) · Top5 37/50 (74%)**
  **H2 OpenCLIP Top1 41/50 (82%) · Top5 47/50 (94%)** (+5 Top1, +10 Top5 vs CLIP).
  Por categoría (Top1/Top5): exacta 9/10, sin_marco 10/10, recoloreada 9/10,
  recortada 10/10, **persona 3/10→7/10** (CLIP solo 1/10). Evidencia en
  `data/comparacion_hito1_hito2.csv` y `.json`.
- Fix: `_embedding_openclip` inicial falló con `BaseModelOutputWithPooling` (sin
  `.norm()` ni `.image_embeds`); resuelto con la misma lógica de
  `extraer_embeddings` (image_embeds → pooler_output).
- NOTA: el modelo OpenCLIP queda como opción (`modelo=openclip`); el default
  sigue siendo `clip` para conservar el contrato del docx ("un solo modelo CLIP").
- NOTA: no se hizo commit ni push.

### Prompt 18 - Robustez a oclusiones: fusión CLIP+OpenCLIP+SigLIP y multi-recorte (sin commit)
**Propósito:** que la búsqueda encuentre el producto más parecido AUNQUE la
imagen tenga un "punto grande" u otro elemento tapando parte del diseño.
**Resultado:**
- `api/search_engine_hito2.py`: recuperación por FUSIÓN de índices alineados
  (`recuperacion_fusion` promedia por producto los cosenos de clip+openclip+
  siglip) y multi-recorte (imagen completa + 4 cuadrantes, score = MÁXIMO por
  recorte): si un recorte contiene el punto que tapa, otro lo compensa.
  Refactor del reranking en `_rerank_candidatos` reutilizable por el motor de
  un solo modelo y por el de fusión (`search_similar_reranked_fusion`).
  Pesos reajustados para robustez: embedding 0.50 (la señal más robusta a
  oclusiones), estructura 0.07, color_dominante 0.08, patron 0.06, franjas 0.04.
- `api/main.py`: modelo `fusion` (CLIP+OpenCLIP+SigLIP) con `get_siglip` +
  `_embedding_siglip` (transformers, lazy) y `_recortes_consulta`/`_encodificar_fusion`
  (5 recortes × 3 modelos). `_motor_reranked` despacha según modelo;
  `CANDIDATOS_INICIALES_FUSION=100`. En modos no-clip solo se calcula el
  embedding de la consulta preparada (ahorra ~50% del cómputo). `/health`
  expone `modelos_fusion`.
- `frontend/app.py`: radio con opción recomendada "Fusión (CLIP + OpenCLIP +
  SigLIP) — más robusto" como default.
- `scripts/compare_hito1_hito2.py`: flag `--fusion` agrega el motor `h2fu`.
- Evaluación estándar (50 consultas): **Fusión Top1 42/50 (84%) · Top5 48/50
  (96%)**, OpenCLIP 40/46, H2-CLIP 34/37, H1 32/36. Fusión recupera exacta
  10/10 y persona 8/10 Top5.
- Prueba de oclusión (punto negro/blanco 34% y 50%, 3 posiciones, 5 productos,
  60 casos): oclusión 34% → **fusión 30/30 y openclip 30/30** (clip 27/30);
  oclusión 50% (punto que cubre toda la imagen) → fusión 18/30 (openclip
  15/30, clip 11/30).
- Tiempos (CPU, en caliente): fusión ~5-6s por consulta (15 forwards), clip y
  openclip <1s.
- LÍMITE honesto: no existe "100%". Con un punto de hasta ~1/3 del diseño la
  fusión acierta siempre; con una mancha que cubre TODA la imagen (50%) ningún
  modelo puede garantizarlo. Es el límite físico de cualquier sistema visual.
- NOTA: no se hizo commit ni push.

### Prompt 19 - images_normalized como carpeta ÚNICA de búsqueda (sin commit)
**Propósito:** que `data/images_normalized/` sea la carpeta de donde se buscan
TODAS las imágenes del catálogo (antes el fallback del Hito 1 leía los
descriptores visuales desde `images_final/`).
**Resultado:**
- `api/search_engine_hito2.py`: eliminado `CARPETA_IMAGENES_H1` y la bandera
  `_indice_normalizado_activo`. `_carpeta_imagenes_activa()` ahora SIEMPRE
  devuelve `CARPETA_IMAGENES` (`data/images_normalized/`), sin excepciones.
  Los descriptores visuales (color/estructura/avanzados) se calculan siempre
  sobre el banco limpio, coherente con los índices de Sala 4.
- Nuevo `_resolver_imagen(nombre, id)`: resuelve por nombre exacto del CSV o
  por el equivalente normalizado `<id>.jpg` (Sala 1 convierte todo a .jpg);
  usado por `_descriptores_de_archivo` y `_descriptores_avanzados_candidato`.
  Verificado: las 1000 imágenes de products.csv resuelven en images_normalized.
- `_descriptores_avanzados_candidato` ahora usa SIEMPRE los precomputados de
  `descriptores.json` (calculados sobre images_normalized), no solo cuando el
  índice activo era el normalizado.
- El fallback del Hito 1 (falta embeddings_clip.npy) sigue funcionando solo
  para el ranking por vectores; las imágenes siempre salen de images_normalized.
- Verificación: `/search/image/v2` con openclip sobre una imagen de
  images_normalized → top1 correcto (score 1.0), `modelo_utilizado` correcto.
- REFUERZO ESTRICTO: se revisó todo el flujo de búsqueda (frontend + API +
  precomputo). `frontend/app.py` y `api/search_engine_hito2.py` solo usan
  `data/images_normalized/`. `scripts/precomputar_descriptores.py` también se
  hizo estricto: eliminado el respaldo a `images_final`; si un producto no
  resuelve en images_normalized se marca error, no se sustituye. Se regeneró
  `data/descriptores.json` → fuente "images_normalized", 1000/1000 OK, 0
  errores (el respaldo a images_final nunca fue necesario).
- NOTA: no se hizo commit ni push.

## Fecha: 2026-08-12 (migración de banco: images_final -> images_normalized)

### Prompt - Unificar el banco de imágenes del sistema en data/images_normalized/
**Propósito:** Hacer que las imágenes que muestra la interfaz, las que usa el
algoritmo para generar embeddings y las que se comparan contra la consulta del
usuario sean SIEMPRE las normalizadas de data/images_normalized/ (Sala 1, sin
marco ni texto externo), en lugar de data/images_final/.
**Resultado:**
- scripts/generar_embeddings.py: IMAGES_DIR -> data/images_normalized/ +
  esolver_ruta_imagen() (fallback <id>.jpg porque la normalización
  convierte todo a .jpg y 177 filas del CSV usan .png/.gif/.jpeg).
- rontend/app.py: uta_local() ahora intenta el nombre exacto del CSV y,
  si falta, el equivalente <id>.jpg en images_normalized/ (antes 177
  productos caían a la URL remota).
- scripts/validate_dataset.py: valida contra data/images_normalized/ con el
  mismo fallback.
- Re-generados data/embeddings.npy + data/ids.npy desde images_normalized:
  1000 productos, 1000 embeddings (1000x512), errores 0, IDs alineados con
  products.csv, vectores L2 normalizados. Resultado idéntico a
  data/embeddings_clip.npy (ambos sobre el banco normalizado con el mismo
  modelo openai/clip-vit-base-patch32), confirmando coherencia Hito 1/Hito 2.

## Fecha: 2026-08-12 (Sala 1, Hito 3 — banco de 15.272)

### Prompt 6 - Consolidadar 15.272 y normalizar el banco completo
**Propósito:** Llevar el flujo del README hasta la creación de data/images_normalized/ con el banco completo (~15.000) descargado en data/images/.
**Resultado:**
- scripts/consolidar.py corregido: (a) las URLs repetidas del sitio (misma preview para productos distintos con imágenes locales distintas) ahora son avisos, no errores bloqueantes; (b) fallback por índice numérico para los 97 nombres con espacios dobles; (c) conversión automática de .webp a .jpg (AIM-P221-001); (d) redimensionado de la imagen gigante (AIM-P130-056, 219M px) para evitar DecompressionBombError y OOM; (e) limpieza de archivos huérfanos en images_final.
- scripts/normalizar_imagenes.py: fallback conservador 'dudoso' para imágenes sin frente/espalda detectables (casacas claras sobre fondo blanco), completando 15.272/15.272.
- Productos: products.csv 15.272 filas, images_final 15.272, images_normalized 15.272 (.jpg), 0 fallidas, 347 dudosas, informe_normalizacion, detalle_normalizacion, analizar_formatos (5 formatos), revisión muestra 50 (98% correctas), validate_dataset (0 faltantes/dañadas; 104 URLs repetidas aviso; 307 duplicados por hash MD5).

### Prompt 7 - Reporte del Hito 3 y validación humana de 100
**Propósito:** Crear el reporte REPORTES_HIT3.md analizando el Hito 3 de TRABAJO.md (foco Sala 1) y completar la validación humana de 100 imágenes que el Hito 3 exige (antes eran 50).
**Resultado:**
- REPORTES_HIT3.md: resumen, estado global (Sala 1 completa; Salas 4, 3, 2 y 5 pendientes), análisis del proyecto (15.272 productos), Sala 1 en detalle (entregables, actividades, validaciones, medición, problemas resueltos en consolidar.py, desglose de 347 dudosas, respuesta a la pregunta central), métricas obligatorias y próximos pasos.
- scripts/normalizar_imagenes.py: generar_muestra_humana parametrizable (revision_humana_{N}.csv + revision_contact_sheet_{N}.png) y modo --solo-muestra --muestra N para regenerar la muestra sin re-normalizar; main() acepta --muestra.
- scripts/revisar_muestra_50.py: acepta --n (100 en Hito 3), nombres dinámicos y aviso de uso.
- Resultado real: revision_humana_100.csv -> 99/100 correctas (99%), 1 dudosa (AIM-P202-007: 4 bandas, frente/espalda fusionados), 0 incorrectas; informe_revision_humana_100.txt; revision_contact_sheet_100.png.
- REPORTES_HIT3.md actualizado con los resultados reales de la revisión de 100.

## Fecha: 2026-08-13 (Sala 4 + Sala 3, Hito 3 — embeddings a escala 15.272)

### Prompt - Re-indexar el sistema a escala 15.272 sobre images_normalized
**Propósito:** Generar los índices del Hito 3 con el banco completo (15.272) a
partir de data/images_normalized/ (única carpeta del catálogo), que eran los
bloqueos de Sala 4 y Sala 3 (no existía ningún .npy a escala).
**Resultado:**
- `scripts/generar_embeddings.py` (Hito 1, CLIP openai) re-ejecutado sobre las
  15.272 normalizadas → `data/embeddings.npy` (15272×512) + `data/ids.npy`
  (15272, alineado posición a posición con products.csv).
- `scripts/generar_indices_comparativos.py` (Sala 4) re-ejecutado a escala →
  `data/embeddings_clip.npy` (15272×512, listo) y `embeddings_openclip.npy` +
  `embeddings_siglip.npy` en generación (CPU, sin GPU; run secuencial).
- Verificado motor Hito 1 a escala: carga 0,62 s, búsqueda 61 ms, Top 1 exacto.
- Verificado motor Hito 2 (`search_similar_reranked`) contra el índice clip de
  15.272: recuperación Top 30 en 0,15 s, Top 1 correcto, respuesta con
  score_recuperacion/score_reranking/posicion_inicial/posicion_final/modelo.

### Prompt - Contrato de respuesta del Hito 3 y descriptores a escala
**Propósito:** Alinear la respuesta de la API con HITO3.md (Sala 3, punto 7) y
escalar los descriptores del reranking.
**Resultado:**
- `api/search_engine_hito2.py`: cada resultado ahora incluye `score_recuperacion`
  (alias de score_inicial), `posicion_inicial` (posición en la recuperación
  amplia) y `modelo` (además de `modelo_utilizado`), cumpliendo el contrato
  `id, score_recuperacion, score_reranking, posicion_inicial, posicion_final,
  modelo, nombre, imagen, url`.
- `frontend/app.py`: muestra recuperación vs reranking y `posicion_inicial →
  posicion_final`.
- `scripts/precomputar_descriptores.py` re-ejecutado a 15.272 →
  `data/descriptores.json` (fuente images_normalized) para que el reranking no
  compute descriptores on-the-fly con el catálogo grande.
- NOTA: no se hizo commit ni push.

## Fecha: 2026-08-13 (rediseño de interfaz frontend)

### Prompt - Mejora de la UI de frontend/app.py sin romper el funcionamiento
**Propósito:** Rediseñar la interfaz de Sala 2 (cliente puro de la API) con un
look moderno y más información, manteniendo intacto el contrato con la API.
**Resultado:** rontend/app.py rediseñado:
- Tema oscuro deportivo vía CSS (gradientes, tarjetas redondeadas, chips de
  estado, barra de score por resultado).
- Sidebar nueva: URL de la API configurable, verificación de /health,
  selector de modelo (fusion/openclip/clip) e instrucciones.
- Header con estado de la API (productos/embeddings) y chips.
- Panel de consulta: imagen original + imagen preparada por Sala 2
  (imagen_procesada_b64) + detalles del preprocesamiento en expander.
- Resultados en tarjetas: badge de ranking (#1 destacado), nombre, ID,
  proveedor, score de similitud con barra, recuperación vs reranking,
  posición inicial → final, modelo utilizado y enlace a la imagen original.
- Registro de evaluación humana (Muy similar / Similar / Poco similar /
  No relacionado + observación) guardado en data/evaluation.csv con las
  columnas del contrato (consulta, resultado_id, posicion, score,
  clasificacion_humana, observacion).
- Selector de imágenes de prueba desde data/consultas/ para demos.
- Sin embeddings ni búsqueda local: solo consume POST /search/image.
**Verificado:** py_compile OK, arranque headless de Streamlit OK (HTTP 200)
y prueba real contra la API con consulta de data/consultas/ (modo completo,
modelo fusion, 5 resultados con todos los campos del contrato).

## Fecha: 2026-08-13 (tema claro/oscuro en español, caché de preferencia)

### Prompt - Tema en español, tema claro mejorado y preferencia en caché
**Propósito:** Que la interfaz esté íntegramente en español, arreglar el tema
claro (se veía mal) y recordar la elección de tema entre sesiones.
**Resultado:**
- .streamlit/config.toml nuevo: [theme] base = "dark" para que los widgets
  nativos (selectbox, botones, expander) combinen con el diseño oscuro.
- rontend/app.py: toggle "🌓 Tema claro" en el sidebar (español) que aplica
  un tema claro rediseñado (gradientes suaves, tarjetas blancas, textos y
  chips legibles, botones/inputs/expander re-skin via CSS) y guarda la
  preferencia en rontend/.theme_pref.json (caché entre sesiones) +
  st.session_state (caché entre reruns).
- Menú nativo: se ocultan los items en inglés "Get help"/"Report a bug" y
  "About" muestra texto en español (el menú Settings de Streamlit en sí no es
  traducible; el control de tema propio queda en español).
- rontend/.theme_pref.json agregado a .gitignore.
**Verificado:** py_compile OK, arranque headless con tema claro OK (HTTP 200),
ciclo guardar/leer de la preferencia OK.

### Prompt - Fix KeyError tema_claro
**Propósito:** Corregir KeyError: st.session_state has no key "tema_claro" en
arranque: la inyección CSS condicional (linea 178) se ejecutaba antes de la
inicializacion de la clave en session_state.
**Resultado:** cargar_tema()/guardar_tema() y la inicializacion
if "tema_claro" not in st.session_state movidas al inicio del script (antes
de la inyeccion CSS). Verificado con streamlit.testing.v1.AppTest:
arranque sin pref, con pref claro, y toggle off (persiste en
rontend/.theme_pref.json).

## Fecha: 2026-08-13 (acciones imprimir/descargar, sin emojis, tema claro)

### Prompt - Imprimir/descargar en resultados, soporte tema claro, sin emojis
**Propósito:** (1) Botones Imprimir y Descargar imagen en cada resultado; (2)
que esos controles soporten el tema claro; (3) eliminar TODOS los emojis de la
interfaz usando iconos SVG en línea (sin descargar librerías, solo código
inline); (4) sin opción de grabar video.
**Resultado:**
- html_acciones(): iframe via streamlit.components.v1.html con botones
  "Descargar" (data-URI + download) e "Imprimir" (ventana nueva + print) por
  resultado, coloreados según tema claro/oscuro.
- Iconos SVG estilo Feather inline (_svg() + dict ICONOS): gear, zap, cpu,
  info, sun, target, search, trophy, wrench, link, edit, shirt. Sin emojis en
  toda la app y sin CDN (nada se descarga, todo inline).
- page_icon emoji eliminado; clase .result-img con borde adaptado a cada
  tema; labels de widgets en texto plano.
- No se agregó ninguna opción de grabación de video.
**Verificado:** py_compile OK; AppTest en tema oscuro y claro sin excepciones;
flujo completo con imagen real (c01_cuerpo.jpeg) contra la API: 5 tarjetas +
5 iframes de acciones + 5 expanders de evaluación renderizados sin errores.

## Fecha: 2026-08-13 (fix iconos SVG invisibles + descarga corrupta)

### Prompt - Fix: iconos no visibles y descarga de imagen corrupta
**Propósito:** (1) Los SVG inline no se renderizaban porque el sanitizador de
Streamlit no permite etiquetas svg (labels de expander usan allowHTML=false
y st.markdown pasa por rehype-raw/DOMPurify); (2) la descarga por data-URI
JS descargaba archivo corrupto (data URI gigante en el srcdoc del iframe).
**Resultado:**
- Iconos migrados a **Bootstrap Icons por CDN** (solo URL, sin descargar):
  <link> en st.markdown + <i class="bi bi-xxx ic"></i>. Los labels de
  expander (que escapan HTML) quedan sin icono, en texto plano.
- Descarga reemplazada por st.download_button nativo: envía los BYTES reales
  del archivo local por websocket (archivo JPEG siempre válido). El iframe
  queda solo con el botón Imprimir.
- Tema claro: botón secundario (Descargar) también re-estilizado en claro.
**Verificado:** py_compile OK; AppTest con imagen real contra la API en tema
oscuro y claro: 5 resultados, 5 download_buttons (label/filename/mime/bytes)
sin excepciones; sin emojis restantes.

## Fecha: 2026-08-13 (fix: descarga re-dispara búsqueda + iconos emoji)

### Prompt - Fix: al descargar se repite la búsqueda; los SVG no se ven
**Propósito:** (1) El botón Descargar (widget) provoca un rerun de Streamlit
que re-ejecutaba la búsqueda contra la API (lento y duplicaba consultas);
(2) los iconos por CDN (Bootstrap Icons) tampoco se veían en el navegador;
el usuario autorizó emojis si SVG no funciona.
**Resultado:**
- **Caché de búsqueda:** hash md5(bytes imagen + modelo + api_url) guardado en
  st.session_state["busqueda_clave"]; la API solo se consulta si cambia la
  clave. Los reruns de widgets (descargar, evaluar) ya no re-buscan.
- **Iconos en emojis** (texto plano, se ven en todos los contextos): sidebar,
  encabezados, chips, labels de expander y botón Imprimir del iframe
  (🖨️/⬇️/⚙️/🧠/ℹ️/🎯/🔍/🏆/🛠️/🔗/✏️/👕). Eliminado el CDN y la clase .ic.
**Verificado:** py_compile OK; AppTest con contador de requests.post: 1 solo
POST tras subir la imagen y 0 nuevos en reruns posteriores; 5 download_buttons;
sin excepciones en tema oscuro y claro; emojis presentes en labels y expanders.

## Fecha: 2026-08-13 (fix: Imprimir no mostraba la imagen)

### Prompt - Fix: la opción Imprimir no muestra la imagen a imprimir
**Causa raíz:** (1) html_imprimir usaba el base64 crudo como src de la
imagen sin el prefijo data:image/jpeg;base64, (lo inyectaba tal cual
devuelve imagen_a_b64) -> imagen rota en el popup; (2) el flujo dependía de
window.open + document.write con el base64 gigante (popups bloqueables y
límite de 1 MB de Chrome en document.write).
**Solución:** sin popup ni document.write. La imagen vive oculta
(display:none) dentro del propio iframe y solo se muestra con
@media print; window.print() imprime el documento del iframe (el sandbox
de components.html incluye llow-modals, verificado en el bundle:
IFrameUtil.PlC_b34Z.js). img.onload garantiza que la imagen ya cargó antes
de imprimir. Agregado el prefijo data:image/jpeg;base64, en el src.
**Verificado:** py_compile OK; AST-test de html_imprimir: print-area +
data URI con prefijo + @media print + window.print, sin window.open ni
document.write, en ambos temas; AppTest flujo completo sin excepciones
(5 iframes, 5 download_buttons).

## Fecha: 2026-08-13 (rediseño visual completo - estética Google Stitch)

### Prompt - Rediseño UI/UX: interfaz moderna de producto de IA (dark ambient)
**Objetivo:** Solo UI/UX; sin tocar arquitectura, API, lógica ni contratos.
Referencia conceptual Google Stitch: dark ambient, minimalismo, gradientes
luminosos sutiles, glassmorphism ligero, espacio negativo, jerarquía fuerte.
**Cambios en frontend/app.py (lógica intacta):**
- Fondo oscuro #05070d con 3 gradientes radiales ambientales (cyan→azul→violeta).
- Hero rejerarquizado: eyebrow "Búsqueda visual" con punto pulsante → título
  grande gradiente "Encuentra camisetas visualmente similares" → subtítulo →
  meta discreta "15,272 productos · 15,272 embeddings · API activa" (sin cards).
- Dropzone protagonista: 250px, borde discontinuo, vidrio (backdrop-filter),
  hover con glow; los textos internos en inglés del widget ("Upload",
  "200MB per file...", "Drag and drop...") se ocultan por CSS (testids
  verificados en bundle FileUploader.Bg9tjvVJ.js) y se superpone overlay en
  español (SVG data-URI + "Arrastra tu imagen aquí / o haz clic para elegir
  archivo") solo en estado vacío vía :has(). Con archivo cargado el overlay
  desaparece y la lista de archivos sigue visible y funcional.
- Pasos en una línea minimalista: "01 Sube tu imagen → 02 La analizamos →
  03 Encuentra similares" (reemplaza las 3 cards).
- Resultados: aparición escalonada (fadeUp con delay 70ms por rank), tarjetas
  glass con hover sutil, score bar delgada, sección "Resultados" con meta
  inline (Top 5 · Modo · Modelo · tiempo).
- Sidebar translúcido con blur; widgets select/input oscuros; botón primario
  gradiente cyan con glow; #MainMenu/footer ocultos; header transparente.
- Responsive: clamp() en título, min-height 195px en dropzone móvil,
  result-layout con flex-wrap en <=640px.
- Tema claro: misma estructura con ambient suave, tarjetas blancas y overlay
  de dropzone en azul.
**Verificado:** py_compile OK; AppTest en oscuro y claro: estado inicial y con
imagen real (c01_cuerpo.jpeg) sin excepciones; 1 file_uploader, 5
download_buttons, 7 expanders, hero/flow/meta/query-status/Resultados
presentes.

## Fecha: 2026-08-13 (luz ambiental interactiva que sigue al cursor)

### Prompt - Efecto ambiental interactivo (estilo Google Stitch), SOLO visual
**Objetivo:** halo de luz difuminado (cyan→azul→violeta, muy sutil) que sigue
el cursor con interpolación suave; decorativo, sin tocar lógica/API/upload.
**Implementación (frontend/app.py):**
- html_luz_ambiental(): iframe invisible (components.html, height=1) cuyo
  script, aprovechando allow-same-origin (sandbox verificado en bundle
  IFrameUtil), manipula el DOM del padre: crea 3 divs .luz de 1900px
  (radial-gradient closest-side, opacidades .16/.12/.09, offsets
  -140/-80 y +120/+50 para un halo asimétrico) colgados de .stApp.
- CSS: .stApp { isolation: isolate; } + .luz { position: fixed;
  z-index: -1; pointer-events: none; will-change: transform; opacity 0 →
  .luz-on 1 (transición .8s) } → la luz queda BAJO la UI y se percibe a
  través de las superficies translúcidas. iframe oculto con
  iframe.stIFrame[height="1px"].
- JS: lerp 0.10 por frame con requestAnimationFrame, solo transform
  translate3d (compositor, sin repaints); encendido en el primer mousemove
  (sin parpadeo inicial), apagado suave al salir de la ventana
  (mouseleave/mouseenter en documentElement); guard anti-duplicados
  (querySelector('.luz')) porque el iframe se re-ejecuta en cada rerun.
- Accesibilidad/perf: desactivada con prefers-reduced-motion y
  pointer: coarse (táctiles); listener mousemove pasivo en el documento.
- Tema claro: mismas capas con alphas reducidas (.11/.08/.06).
- Fix: definición de la función movida antes de su llamada (NameError);
  label del file_uploader no vacío con label_visibility collapsed
  (warning de accesibilidad de Streamlit 1.60).
**Verificado:** py_compile OK; AppTest oscuro/claro: sin excepciones
(inicial y con imagen real); 6 iframes (1 luz + 5 imprimir), 5
download_buttons; JS verificado por AST (rAF, translate3d, reduced-motion,
coarse, guard, 3 capas).

## Fecha: 2026-08-13 (fix: luz ambiental de página completa, no solo en el dropzone)

### Prompt - Fix: el difuminado solo se ve dentro del box de subir imagen
**Causa:** las capas .luz con position:fixed colgadas de .stApp quedaban
ancladas al contenedor (o eran casi invisibles sobre el fondo oscuro plano
fuera de las superficies translúcidas), por lo que el efecto solo se
percibía dentro del dropzone.
**Solución:**
- Capas en position: absolute con .stApp { position: relative }
  (anclaje determinista al documento, inmune a transforms del contenedor) y
  compensación de scroll en el transform: translate3d(scrollX + x + dx,
  scrollY + y + dy) → la luz sigue al cursor en viewport aunque se scrollee.
- Tamaño subido a 2200px y alphas aumentadas (.20/.14/.10 oscuro,
  .14/.10/.07 claro): perceptible sobre toda la página, no solo tras el
  vidrio. Sigue siendo un ambiente sutil (z-index -1, pointer-events none).
**Verificado:** py_compile OK; JS por AST (scrollX/scrollY en transform);
AppTest oscuro/claro sin excepciones (6 iframes, 5 download_buttons).

## Fecha: 2026-08-13 (fix: UI en blanco al cargar + luz ambiental robusta)

### Prompt - Fix: rompiste la UI, no se ve nada al cargar la web
**Causa probable:** las capas .luz ancladas dentro de .stApp con
z-index: -1 + isolation: isolate + position: relative en .stApp
podían romper el apilado/render del contenedor raíz de Streamlit en el
navegador (contenedores de positioning no estándar en .stApp).
**Solución (patrón a prueba de balas):**
- Los gradientes ambientales del fondo pasaron de .stApp a ody
  (el lienzo raíz); .stApp y [data-testid="stAppViewContainer"]
  quedan ackground: transparent.
- Las 3 capas de luz se cuelgan de document.body con
  position: fixed; z-index: -1 (body nunca tiene transform → el
  containing block es siempre el viewport) y transform solo
  clientX/clientY (sin compensación de scroll).
- Eliminados isolation: isolate, position: relative de .stApp y el
  listener de scroll sobrante: .stApp vuelve a su estado original.
- Pintado: sobre el fondo de body y bajo todo el contenido (la luz se ve
  a través de superficies translúcidas) en toda la página.
**Verificado:** py_compile OK; llaves CSS balanceadas (82/82); AppTest
oscuro/claro sin excepciones (6 iframes, 5 download_buttons). Sugerido al
usuario: recarga con Ctrl+F5 (posible caché del bundle anterior).

## Fecha: 2026-08-13 (revert: eliminado efecto de luz ambiental)

### Prompt - vuelve a cambios atrás porque está roto, la cagaste, arregla
**Decisión:** revertir por completo el efecto de luz ambiental (fue la
única adición desde el rediseño aprobado por el usuario) y devolver la
app al estado que el usuario confirmó como bueno.
**Cambios aplicados (frontend/app.py):**
- Eliminado html_luz_ambiental() y su llamada
  components.html(..., height=1, scrolling=False) (línea 454).
- Eliminado CSS .luz, .luz-on, .luz-1/2/3 y
  iframe.stIFrame[height="1px"] del tema oscuro y claro.
- Fondo ambiental restaurado en .stApp (gradientes originales), sin
  ody + transparentes + stAppViewContainer.
**Verificado:** py_compile OK; AppTest oscuro/claro sin excepciones y
con 5 download_buttons tras subir data/consultas/c01_cuerpo.jpeg.
El usuario debe recargar con Ctrl+F5 (caché de bundle anterior).
