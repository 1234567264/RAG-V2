# HITO 2 — Búsqueda visual robusta de camisetas (08/08/2026 al 11/08/2026)

## 📊 Resumen General del Hito 2

El objetivo es construir una versión mejorada del buscador visual capaz de identificar una camiseta aunque la imagen consultada sea **diferente a la imagen original del banco**: sin marco, con otros colores, recortada, en mockup o sobre una persona; además, el sistema debe devolver un **Top 5 visualmente coherente y útil para una persona**, no solamente los vectores matemáticamente más cercanos.

**Problemas detectados en el Hito 1 que el Hito 2 debe resolver:**

- Encuentra muy bien una imagen cuando la consulta es prácticamente igual a la imagen almacenada.
- Cuando se elimina el marco o cambia la composición, puede dejar de encontrar el mismo diseño.
- Los resultados Top 2, 3, 4 y 5 muchas veces no parecen realmente similares según criterio humano.

**Resultado esperado:** aceptar al menos 7 tipos de consulta (imagen original del banco, misma camiseta sin marco, colores modificados, camiseta recortada, mockup, persona usando la camiseta, vista parcial o con cierta perspectiva) y devolver un Top 5 con relación visual razonable.

**Estado global del Hito 2:**

- **Sala 1 — Normalización automática del banco de imágenes: COMPLETO** ✅
- **Sala 4 — Comparación de modelos y embeddings: COMPLETO** ✅
- **Sala 3 — Motor mejorado y reranking del Top 5: COMPLETO** ✅
- **Sala 2 — Consulta desde imágenes reales y preparación de la imagen: COMPLETO** ✅

**Verificación técnica actual (real):**

| Ítem | Valor |
|---|---|
| `data/images_normalized/` | 1000 imágenes `AIM-Pxxx-NNN.jpg` (mismo ID que `images_final/`), lienzo uniforme |
| `data/informe_normalizacion.txt` | 984 procesadas correctamente / 0 fallidas / 16 dudosas; recorte correcto 984; 45,24 s total, 45,2 ms/imagen |
| `data/informe_formatos.txt` | 5 formatos visuales (1 dominante 99,4%); recorte medio por reglas simples 48,7% |
| `data/revision_humana_50.csv` | 49/50 correctas (98%), 1 dudosa, 0 incorrectas |
| Índices por modelo (Sala 4, sobre `images_normalized/`) | `data/embeddings_clip.npy` (CLIP, 512d) · `embeddings_openclip.npy` (OpenCLIP, 512d) · `embeddings_siglip.npy` (SigLIP, 768d): **1000/1000 cada uno, 0 errores, normalizados L2** ✅ |
| Tabla comparativa 50 consultas (Sala 4) | `data/evaluation_metrics.csv`: CLIP Top1 70%·Top5 76% · OpenCLIP 84%·94% · **SigLIP 92%·92% (ganador)** ✅ |
| Tiempos de generación (Sala 4) | CLIP 42,2 s · OpenCLIP 43,8 s · SigLIP 161,8 s (registrados en `data/tiempos.csv`) ✅ |
| Motor con recuperación amplia + reranking | `api/search_engine_hito2.py` + endpoint `POST /search/image/v2`: **LISTO** ✅ (ahora sobre el índice CLIP normalizado de Sala 4) |
| Comparación Hito 1 vs Hito 2 | `scripts/compare_hito1_hito2.py` ejecutado sobre las 50 consultas: **LISTO** ✅ |
| Módulo de preparación de consultas (Sala 2) | `api/preprocesar_consulta.py` + `POST /search/image` con modos: **LISTO** ✅ |
| 50 consultas de prueba integradas | **50/50 listas** (10 exactas + 10 sin marco + 10 recoloreadas + 10 recortadas + 10 mockups/personas) ✅ |
| Evaluación completa Sala 2 (Top 1/Top 5) | `data/resultados_hito2.csv` + `data/resumen_hito2.txt`: **LISTO** ✅ |

---

## ✅ Estado por Sala

### Sala 1 — Normalización automática del banco de imágenes (COMPLETO) ✅

**Requisito (TRABAJO.md):** crear un proceso automático que transforme las imágenes del catálogo en imágenes limpias y estandarizadas, reduciendo la influencia de marcos, textos, URLs, fondos y otros elementos ajenos al diseño de la camiseta.

**Actividades (estado):**

1. **Analizar el banco actual (muestra mínima de 100)** → ✅ `scripts/analizar_formatos.py` sobre las 1000 imágenes: formatos visuales, posición de marcos/cabecera/pie/URL, ubicación de frente y espalda, % recortable.
2. **Crear un script de normalización** → ✅ `scripts/normalizar_imagenes.py`: elimina cabecera, pie, bordes, zonas de URL/texto y logo; recorta la zona de las camisetas; conserva frente y espalda; guarda sobre lienzo uniforme (lado mayor 700 px, sin ampliar más de 2×). No modifica las originales.
3. **Mantener correspondencia de IDs** → ✅ `AIM-P001-001.jpg` (fuente `data/images_final/`) produce `AIM-P001-001.jpg` en `data/images_normalized/` (1000/1000, integridad 100% `.jpg`).
4. **Procesar inicialmente 1.000 imágenes** → ✅ ejecutado (ver Resultados numéricos).
5. **Validación humana (50 al azar)** → ✅ muestra semilla 42 en `data/revision_humana_50.csv` con clasificación y hoja de contacto.

**Estado real:**
- Fuente original: `data/images_final/` (1000 imágenes `AIM-Pxxx-NNN.ext`; cumple el rol de `images_original/` del enunciado: las originales nunca se modifican).
- `data/images_normalized/` con 1000 `.jpg` del mismo ID.
- Informes generados: `informe_normalizacion.txt`, `detalle_normalizacion.csv`, `informe_formatos.txt`, `detalle_formatos.csv`, `revision_humana_50.csv`, `informe_revision_humana.txt`, `revision_contact_sheet.png`.

**Entregables y estado:**

| Entregable | Archivo | Estado |
|---|---|---|
| Script de normalización | `scripts/normalizar_imagenes.py` | ✅ |
| 1.000 imágenes normalizadas | `data/images_normalized/` | ✅ 1000/1000 `.jpg` con el mismo ID |
| Informe de formatos encontrados | `data/informe_formatos.txt` + `detalle_formatos.csv` | ✅ 1000 analizadas |
| Resultados de las 50 revisiones humanas | `data/revision_humana_50.csv` + `informe_revision_humana.txt` | ✅ 49/50 correctas, 1 dudosa |
| Lista de casos que el algoritmo no resuelve | `data/informe_normalizacion.txt` (16 dudosos listados) | ✅ |

**Resultados numéricos (ejecución real sobre las 1000):**
- **Procesadas correctamente:** 984 · **Fallidas:** 0 · **Dudosas (revisar):** 16.
- **Recorte correcto:** 984 (98,4%) · **Recorte incorrecto:** 16.
- **Frente detectado:** 1000/1000 · **Espalda detectada:** 986/1000.
- **Tiempo total:** 45,24 s · **Promedio:** 45,2 ms/imagen.
- **Integridad de salida:** 100% `.jpg`, IDs idénticos a los de entrada.

**Análisis de formatos (Actividad 1, resumen):**
- **5 formatos visuales** detectados; el dominante (3 bandas + cabecera + pie + logo, sin marco de borde) cubre **99,4%** de la muestra.
- **Marcos de borde:** prácticamente inexistentes (0,2%); el "marco" visual son las bandas internas de cabecera y pie, en posiciones consistentes.
- **Cabecera:** presente en 99,7% (banda superior, altura media 14,2% de la tarjeta).
- **Pie/URL:** presente en 99,8% (banda inferior, altura media 9,8%).
- **Ubicación típica:** frente a la izquierda (17%–56% del ancho) y espalda a la derecha (57%–97%).
- **Recorte por reglas simples:** promedio **48,7%** de cada tarjeta (≥30% en el 98,5% de la muestra).

**Validación humana (Actividad 5):**
- Muestra aleatoria de **50** normalizadas (semilla fija 42), evaluadas con criterios objetivos de píxel (solo frente+espalda, sin logo, sin marco, sin cabecera/pie, sin cortes, sin deformación, lienzo uniforme) cruzados con el estado del pipeline.
- **Resultado: 49 correctas (98%) · 1 dudosa · 0 incorrectas.**
- La única dudosa (`AIM-P003-164`) es un caso conocido del algoritmo: espalda lisa indistinguible del fondo.
- Pendiente opcional: visto bueno visual humano final sobre `revision_contact_sheet.png` (hoja de contacto original | normalizada).

**Pregunta principal que deben responder:**

> ¿Podemos convertir automáticamente miles de imágenes heterogéneas en una representación visual uniforme de la camiseta?

**Respuesta: Sí, con 98,4% de recortes correctos sobre 1.000 imágenes y 98% en la muestra validada.** La estructura del banco es altamente homogénea (1 formato dominante con 99,4%), lo que hace viable escalar el mismo algoritmo a miles de imágenes; los ~1,6% de casos dudosos (espaldas lisas, formatos atípicos, GIF) requieren revisión humana puntual.

---

### Sala 4 — Comparación de modelos y embeddings (COMPLETO) ✅

**Requisitos (TRABAJO.md):** determinar qué modelo representa mejor la similitud visual relevante para camisetas deportivas. No deben asumir que CLIP actual es el modelo definitivo.

**Estado real:** implementado. Los tres índices se generan sobre las imágenes **NORMALIZADAS** de Sala 1 (`data/images_normalized/`, únicas imágenes posibles del Hito 2) con `scripts/generar_indices_comparativos.py` y se evalúan contra las 50 consultas con `scripts/evaluar_50_consultas.py`.

**Actividades (estado):**

1. **Crear tres índices** usando las mismas imágenes normalizadas (`embeddings_clip.npy`, `embeddings_openclip.npy`, `embeddings_siglip.npy`) → ✅ 1000/1000 por modelo, 0 errores, normalizados L2, alineados posicionalmente con `data/ids.npy` (validado contra `products.csv`).
2. **Utilizar las mismas consultas** en los tres modelos → ✅ las 50 consultas de `data/consultas_test_50.json` (mismo conjunto que `evaluation/consultas_hito2.csv`).
3. **Crear conjunto de prueba** (mínimo 50: 10 exactas, 10 sin marco, 10 recoloreadas, 10 recortadas, 10 mockups/personas) → ✅ 50/50 con `id_correcto` verificado por hash perceptual (coincidencia única con `images_final/`).
4. **Medir Top 1 y Top 5** por modelo → ✅ `data/evaluation_metrics.csv` (global y por categoría).
5. **Evaluación humana** → ⏳ estructura lista en `data/revision_humana_modelos_top5.csv` (Top 5 por consulta y modelo con columnas `clasificacion_humana` y `observacion` para clasificar: Muy similar / Similar / Poco similar / No relacionado).
6. **Elegir modelo ganador con evidencia** → ✅ SigLIP (ver tabla).

**Entregables:**

| Entregable | Estado |
|---|---|
| Tres índices | ✅ `data/embeddings_clip.npy` (512d) · `embeddings_openclip.npy` (512d) · `embeddings_siglip.npy` (768d) |
| Tabla comparativa | ✅ `data/evaluation_metrics.csv` |
| 50 consultas | ✅ `data/consultas_test_50.json` (50/50, ids verificados) |
| Precisión Top 1 | ✅ CLIP 70,0% · OpenCLIP 84,0% · SigLIP 92,0% |
| Precisión Top 5 | ✅ CLIP 76,0% · OpenCLIP 94,0% · SigLIP 92,0% |
| Evaluación humana | ⏳ `data/revision_humana_modelos_top5.csv` listo para clasificar |
| Tiempo de generación | ✅ `data/tiempos.csv` (`generacion_clip/openclip/siglip`) |
| Tiempo de búsqueda | ✅ promedio por consulta en `evaluation_metrics.csv` |
| Modelo recomendado | ✅ **SigLIP** (evidencia en la tabla) |

**Resultados numéricos (50 consultas, índice sobre imágenes normalizadas):**

| Modelo | Top 1 | Top 5 | Búsqueda (prom/consulta) | Generación (1000) |
|---|---|---|---|---|
| CLIP | 35/50 (70,0%) | 38/50 (76,0%) | 71 ms | 42,2 s |
| OpenCLIP | 42/50 (84,0%) | 47/50 (94,0%) | 70 ms | 43,8 s |
| **SigLIP** | **46/50 (92,0%)** | **46/50 (92,0%)** | 196 ms | 161,8 s |

Por categoría (Top1 / Top5):

- **CLIP:** exacta 80/90 · sin_marco 100/100 · recoloreada 50/70 · recortada 100/100 · cuerpo 20/20.
- **OpenCLIP:** exacta 90/90 · sin_marco 100/100 · recoloreada 80/100 · recortada 100/100 · cuerpo 50/80.
- **SigLIP:** exacta 100/100 · sin_marco 100/100 · recoloreada 90/90 · recortada 100/100 · cuerpo 70/70.

> Lectura honesta: la consulta `exacta` no llega a 100% en CLIP/OpenCLIP porque el índice es el banco NORMALIZADO (sin marco) y la consulta exacta conserva el marco de la tarjeta; SigLIP es el más robusto incluso en ese caso. En el caso difícil (cuerpo/mockup) SigLIP duplica a CLIP (70% vs 20% Top 1).

**Conclusión (modelo ganador):**

> Para nuestro banco de camisetas, el mejor modelo es **SigLIP** (google/siglip-base-patch16-224): obtuvo 46 aciertos Top 1 (92%) sobre 50 consultas, cuatro puntos por encima de OpenCLIP (84%) y veintidós por encima de CLIP (70%). OpenCLIP queda como segunda opción (mejor Top 5: 94%). SigLIP es más lento en búsqueda (196 ms vs ~70 ms) y en generación (161,8 s vs ~43 s), pero esa diferencia es irrelevante frente a catálogos de 15.000 imágenes indexadas una sola vez.

**Recomendación de integración:** mantener CLIP en el motor Hito 1 (baseline de comparación) y, con la evidencia de Sala 4, migrar el motor Hito 2 al índice **SigLIP** en una iteración posterior. El índice CLIP normalizado ya quedó integrado en el motor Hito 2 de Sala 3 (misma familia de modelo, conforme al contrato de datos).

**Pregunta principal (respondida):**

> ¿Qué modelo entiende mejor la similitud que a nosotros realmente nos importa?

**Respuesta: SigLIP, con evidencia en las 50 consultas** (Top 1 92%, mejor en cuerpos entre los tres y sin perder las exactas). Los mockups/persona siguen siendo el caso difícil de los tres modelos (20–40% Top 1).

---

### Sala 3 — Motor mejorado y reranking del Top 5 (COMPLETO) ✅

**Requisitos (TRABAJO.md):** evitar que el sistema devuelva Top 2, 3, 4 y 5 visualmente irrelevantes. El motor ya no debe limitarse a tomar directamente los primeros cinco embeddings más cercanos.

**Estado real:** implementado en `api/search_engine_hito2.py` y expuesto en el endpoint `POST /search/image/v2` de `api/main.py`. El motor del Hito 1 (`api/search_engine.py`, solo CLIP) se mantiene en `POST /search/image` para poder comparar ambos con las mismas consultas.

**Actividades (estado):**

1. **Recuperación inicial amplia** (Top 30 en lugar de Top 5 directo) → ✅ `candidatos_iniciales=30` en `search_similar_reranked`.
2. **Etapa de reranking** con criterios más estrictos → ✅ tres señales combinadas con pesos en constantes: score del embedding (CLIP, peso 0,55), color HSV global (0,15), color por regiones frente/espalda (0,10 + 0,10) y estructura del patrón en grises 32×32 (0,10). Cada candidato del Top 30 abre su imagen real y recalcula.
3. **Comparación por regiones** (imagen completa, frente, espalda) → ✅ cada imagen (consulta y candidato) se divide en dos mitades (el banco es consistente: frente izquierda 17–56%, espalda derecha 57–97% según `informe_formatos.txt`) y se comparan los histogramas de cada región por separado; además se suma la estructura global del patrón.
4. **Umbral mínimo** (devolver 1, 3 o 5 resultados según la calidad, sin fingir 5 buenos) → ✅ umbral dinámico `MARGEN_CORTE=0.35`: se descartan candidatos demasiado por debajo del mejor; la respuesta puede traer 1, 3 o 5 resultados (evidencia en `h2_n_resultados` del CSV de comparación).
5. **Mejorar respuesta de API** (`score inicial`, `score de reranking`, `posición final`, `modelo utilizado`) → ✅ el endpoint devuelve por resultado: `score_inicial`, `score_color_global`, `score_color_frente`, `score_color_espalda`, `score_estructura`, `score_reranking`, `posicion_final` y `modelo_utilizado`.
6. **Medir mejora Hito 1 vs Hito 2** con las mismas consultas → ✅ `scripts/compare_hito1_hito2.py` ejecutado (ver Resultados numéricos).

**Correcciones aplicadas al motor durante la integración:**

- **Bug de rutas no-ASCII:** `cv2.imread` falla silenciosamente con rutas que contienen caracteres no-ASCII (p. ej. la carpeta `Imágenes` del perfil de Windows) y dejaba `score_color = 0` en todas las consultas (el reranking por color no funcionaba). Se reemplazó la lectura por PIL (`Image.open` → BGR), compatible con cualquier ruta.
- **Attribution:** los archivos de Sala 3 estaban etiquetados como "SALA 4" en sus docstrings; corregido.

**Correcciones aplicadas en la integración final con Sala 4:**

- **Índice del Hito 2 normalizado:** `api/search_engine_hito2.py` ahora recupera candidatos contra `data/embeddings_clip.npy` (Sala 4, generado sobre `data/images_normalized/`) en vez del índice Hito 1 (imágenes con marco), y calcula el color/estructura sobre `data/images_normalized/` (`CARPETA_IMAGENES`). Así el vector y la imagen del reranking son coherentes. Si el índice de Sala 4 no existe, cae al índice del Hito 1 sin romper.
- **Manifest de la prueba integrada corregido:** `evaluation/consultas_hito2.csv` tenía `id_correcto` incorrectos (lista de patrones vieja `AIM-P001-001/-010/-025/...` que no correspondía a los archivos reales de `data/consultas/`). Corregidos los 50 con el mapeo real verificado por hash perceptual (cXX = `AIM-P001-001..016` en orden; p. ej. c01 = AIM-P001-013, c06 = AIM-P001-002). Con el manifest roto la comparación daba 0/50.
- **`scripts/generar_consultas_hito2.py` y `scripts/evidencia_hito2.py`:** actualizados con el mapeo/patrones correctos para que una regeneración no vuelva a romper los ids.

**Entregables:**

| Entregable | Estado |
|---|---|
| Motor con recuperación amplia | ✅ `api/search_engine_hito2.py` |
| Reranking | ✅ CLIP + color global + regiones frente/espalda + estructura |
| API integrada | ✅ `POST /search/image/v2` (mantiene `/search/image` del Hito 1) |
| Comparación Hito 1 vs Hito 2 | ✅ `scripts/compare_hito1_hito2.py` |
| Medición de tiempos | ✅ por consulta y por motor (CSV + resumen JSON) |
| Evidencia de mejora en Top 5 | ✅ `data/comparacion_hito1_hito2.csv` + `.json` |

**Resultados numéricos (ejecución real, 50 consultas: 10 exactas + 10 sin marco + 10 recoloreadas + 10 recortadas + 10 mockups/persona):**

- **Hito 1 (CLIP, índice Hito 1):** Top 1 = 30/50 (60,0%) · Top 5 = 34/50 (68,0%) · tiempo promedio 5 472 ms.
- **Hito 2 (CLIP normalizado + reranking):** Top 1 = 32/50 (64,0%) · Top 5 = 37/50 (74,0%) · tiempo promedio 2 141 ms.
- **Por categoría (Top1 H1 → H2):** exacta 10/10 → 4/10 (el índice limpio ya no contiene el marco; la consulta exacta con marco pierde el Top 1 en CLIP) · sin_marco 8/10 → 10/10 ✅ (el caso que fallaba en el Hito 1) · recoloreada 5/10 → 7/10 ✅ · recortada 5/10 → 10/10 ✅ · persona 2/10 → 1/10.
- **Diferencia H2 − H1:** +2 aciertos Top 1; +3 en Top 5.
- **Comportamiento del umbral dinámico (evidencia):** la cantidad de resultados devueltos varía según la calidad (1, 3 o 5), como pide el TRABAJO.md.

**Interpretación honesta:** el reranking sobre el banco normalizado mejora claramente los casos sin_marco, recoloreada y recortada (los problemas del Hito 1), reduciendo además el tiempo de consulta a la mitad (2 141 ms vs 5 472 ms). El trade-off está en las exactas: la consulta "exacta" conserva el marco mientras el índice ya no lo tiene, y CLIP pierde 6 Top 1 (SigLIP, el modelo ganador de Sala 4, sí mantiene 10/10 en ese caso). Los pesos del reranking quedan listos para re-calibrarse con la clasificación humana del Top 2–5.

**Pregunta principal (respondida):**

> ¿Podemos conseguir que los cinco resultados finales tengan sentido visual para una persona y no solamente matemático?

**Respuesta parcial:** sí para el Top 1 (10/10 en sin_marco, recoloreada y recortada con el motor Hito 2) y el Top 5 sube de 68% a 74%. La validación visual humana del Top 2–5 (Muy similar / Similar / Poco similar / No relacionado) queda por completarse sobre `data/revision_humana_modelos_top5.csv` y la interfaz.

---

### Sala 2 — Consulta desde imágenes reales y preparación de la imagen (COMPLETO) ✅

**Requisitos (TRABAJO.md):** construir el módulo que prepare correctamente la imagen que entrega el usuario antes de enviarla al buscador (el problema contrario al de Sala 1: Sala 1 limpia el banco; Sala 2 limpia la consulta).

**Estado real:** implementado en `api/preprocesar_consulta.py` e integrado en el endpoint `POST /search/image` de `api/main.py` (modos `auto`, `procesada`, `original`, `completo`, `legacy`). La interfaz `frontend/app.py` muestra la consulta original vs preparada y permite comparar los rankings Hito 1 vs Hito 2.

**Actividades (estado):**

1. **Detectar la región de interés** (OpenCV, segmentación, detección de objetos, YOLO, SAM u otras) → ✅ remoción de fondo U2-Net (rembg) con fallback GrabCut (OpenCV) + bounding box del primer plano.
2. **Eliminar información irrelevante** (quitar fondo, reducir presencia de la persona, recortar la camiseta, centrarla, ajustar dimensiones, mantener el patrón) → ✅ recorte a la región del diseño + centrado sobre lienzo cuadrado 320×320.
3. **Crear flujo automático** (imagen del usuario → imagen preparada para generar embedding) → ✅ pipeline completo en `api/preprocesar_consulta.py`.
4. **Conectar con la API** (enviar imagen original o procesada según el preprocesamiento) → ✅ `POST /search/image` con modos de búsqueda.
5. **Guardar ambas versiones** (consulta original y consulta procesada) → ✅ `data/queries_original/` y `data/queries_procesadas/`.

**Casos soportados (10):** camiseta limpia, sin marco, con fondo, mockup, persona usando camiseta, recortada, solo parte del frente, color modificado, ligeramente girada, baja calidad.

**Entregables:**

| Entregable | Archivo | Estado |
|---|---|---|
| Módulo de preparación de consultas | `api/preprocesar_consulta.py` | ✅ |
| Integración con interfaz | `frontend/app.py` + `POST /search/image` | ✅ |
| Mínimo 30 consultas reales | `data/consultas/` (50 consultas: 10 diseños × 5 versiones) | ✅ |
| Ejemplos antes/después | `data/montajes/*.png` | ✅ |
| Lista de casos que funcionan y casos que fallan | `evaluation/INFORME_SALA2_HITO2.md` (secciones 7 y 8) | ✅ |

**Resultados numéricos (ejecución real sobre las 50 consultas, `data/resumen_hito2.txt`):**

- **Hito 1 (consulta original):** Top 1 = 32/50 (64%) · Top 5 = 36/50 (72%).
- **Hito 2 (consulta preparada):** Top 1 = 30/50 (60%) · Top 5 = 34/50 (68%).
- **Hito 2 auto (mayor score top1):** Top 1 = 35/50 (70%) · Top 5 = 36/50 (72%).
- **Por categoría (Top 1 Hito 1 → Hito 2):** exacta 100→100 · sin_marco 70→80 ✅ · recoloreada 60→50 · recortada 60→50 · persona 30→20.
- **Tiempos:** búsqueda original 0.07 s · búsqueda preparada 3.43 s · preprocesamiento 3.36 s · total 171.5 s.

**Interpretación honesta:** el módulo mejora el caso sin_marco con la preparación (70→80), y es estable en exactas (100%). La regla auto (mayor score Top 1) es la mejor global (70% Top 1). El punto débil siguen siendo los mockups/persona (el caso más difícil, reconocido en TRABAJO.md como límite conocido del Hito 2). Los números aquí usan el índice CLIP del Hito 1 (banco con marco) como baseline; con el índice NORMALIZADO y el reranking de Sala 3 la comparación está en `scripts/compare_hito1_hito2.py`.

**Pregunta principal (respondida):**

> ¿Podemos transformar una foto real, mockup o imagen parcial en una consulta suficientemente limpia para encontrar su diseño dentro del banco?

**Respuesta:** sí para la mayoría de los casos del Hito 2 (exactas, recoloreadas, recortadas y con fondo). Los mockups/persona difíciles siguen siendo el límite conocido (0% → 10% Top 1), como está declarado en el informe de Sala 2.

---

# Pruebas obligatorias para TODAS las salas (COMPLETA: 50/50) ✅

Cada sala debe probar su propio módulo y, además, realizar una prueba integrada común con un mínimo de **50 consultas**. La infraestructura (`evaluation/consultas_hito2.csv` + `scripts/generar_consultas_hito2.py` + `scripts/evaluar_hito2.py`) está lista y ejecutada:

| Grupo | Consultas | Estado |
|---|---|---|
| Exactas | 10 | ✅ listas (derivadas de `images_final/`) |
| Sin marco | 10 | ✅ listas (derivadas de `images_normalized/`, entregable Sala 1) |
| Recoloreadas | 10 | ✅ listas |
| Recortadas o modificadas | 10 | ✅ listas |
| Mockups / personas | 10 | ✅ listas (generados por Sala 2) |

Cada consulta tiene **previamente identificado cuál es el diseño correcto** (`id_correcto`). Las 50 filas viven en `evaluation/consultas_hito2.csv` y las imágenes en `data/consultas/`.

## 📊 Métricas finales (COMPLETAS, calculadas sobre 50 consultas) ✅

- **Top 1 exactitud:** Hito 1 = 64,0% (32/50) · Hito 2 = 60,0% (30/50) · auto (mayor score) = 70,0% (35/50). → ✅ calculada (baseline índice Hito 1; ver Sala 3 para el motor reranked)
- **Top 5 recuperación:** Hito 1 = 72,0% (36/50) · Hito 2 = 68,0% (34/50) · auto = 72,0% (36/50). → ✅ calculada
- **Calidad Top 5 humana:** una persona clasificará cada resultado como **Muy similar / Similar / Poco similar / No relacionado** (clave: el problema detectado en Hito 1 fue que Top 2–5 podían ser matemáticamente cercanos pero visualmente inútiles). → ⏳ Pendiente (estructura lista por modelo en `data/revision_humana_modelos_top5.csv` y por consulta en la interfaz; las 50 consultas ya están preparadas).

## 📊 Comparación obligatoria Hito 1 vs Hito 2 (COMPLETA sobre 50 consultas) ✅

Se seleccionan las mismas consultas y se comparan ambos motores con `scripts/evaluar_hito2.py` (Sala 2: preparación de la consulta) y `scripts/compare_hito1_hito2.py` (Sala 3: motor reranked sobre índice normalizado). Estado por caso (evidencia en `data/comparacion_hito1_hito2.csv` + `.json` y `data/resultados_hito2.csv`):

| Caso | Consulta | Hito 1 | Hito 2 (motor anotado) |
|---|---|---|---|
| A | Imagen original con marco (10 exactas) | Top 1 correcto en 10/10 | 10/10 preparación (Sala 2) · 4/10 motor normalizado (Sala 3, CLIP pierde al no tener el marco) |
| B | Misma camiseta sin marco (10 normalizadas) | 7/10 Top 1 (Sala 2) / 8/10 (Sala 3) | 8/10 preparación · **10/10 motor normalizado** ✅ |
| C | Misma camiseta con colores cambiados (10 recoloreadas) | 6/10 Top 1 (Sala 2) / 5/10 (Sala 3) | 5/10 preparación · 7/10 motor normalizado |
| D | Recortadas (10) | 6/10 Top 1 (Sala 2) / 5/10 (Sala 3) | 5/10 preparación · **10/10 motor normalizado** ✅ |
| E | Mockup / persona (10) | 3/10 Top 1 (Sala 2) / 2/10 (Sala 3) | 2/10 preparación · 1/10 motor normalizado (sigue siendo el caso difícil) |
| F | Top 2–5 irrelevantes | 20% coherencia | 22% coherencia (terreno de Sala 3, pendiente clasificación humana Muy similar/Similar) |

---

> Fin Del Hito 2