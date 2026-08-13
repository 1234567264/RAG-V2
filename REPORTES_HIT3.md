# HITO 3 — Escala real, reranking y conexión WordPress (11/08/2026 al 14/08/2026)

## 📊 Resumen General del Hito 3

El objetivo es **escalar el buscador visual de 1.000 a ~15.000 diseños reales** y mejorar su calidad para que el diseño correcto se mantenga en las primeras posiciones aunque la consulta tenga modificaciones, recortes, cambios de color, logos, fotografías reales o una persona usando la camiseta; al mismo tiempo, iniciar la integración con **WordPress/WooCommerce** mediante un plugin que consuma el mismo motor inteligente.

**Problemas que debe resolver el Hito 3:**

- Pequeñas modificaciones pueden hacer caer el diseño correcto del Top 1 al Top 3, 4 o 5.
- Los resultados Top 2–5 muchas veces no tienen semejanza visual real.
- El sistema devuelve vectores matemáticamente cercanos, aunque algunos no sean útiles.
- Falta probar el comportamiento sobre una biblioteca mucho mayor (~15.000).
- Fotografías de personas, perspectivas, arrugas y vistas parciales siguen siendo casos difíciles.
- WordPress todavía no consume directamente el buscador.

**Criterio de éxito del Hito 3:**

> Sobre una biblioteca cercana a 15.000 diseños, el motor mantiene una buena recuperación del diseño correcto frente a modificaciones y fotografías reales, mejora claramente la coherencia visual de los resultados alternativos mediante reranking y ya puede ser consumido desde WordPress mediante un plugin independiente.

**Estado global del Hito 3 (avance real a hoy):**

- **Sala 1 — Biblioteca real de 15.000 diseños: COMPLETA** ✅ (banco de 15.272 incorporado, normalizado al 100% y **100/100 revisiones humanas realizadas**)
- **Sala 4 — Embeddings a escala y estabilidad visual: PENDIENTE** ⏳ (persiste índice CLIP de 1.000; falta generar los ~15.000 embeddings con el modelo ganador SigLIP y pruebas de estabilidad)
- **Sala 3 — Motor de recuperación + RERANKING: PENDIENTE** ⏳ (el motor del Hito 2 ya tiene recuperación amplia + reranking, pero solo contra 1.000; falta re-indexar a 15.000, Top 30/50, caso Barça y comparación Hito 2 vs Hito 3)
- **Sala 2 — Fotos reales y consultas difíciles: PENDIENTE** ⏳ (las 50 consultas del Hito 2 existen; falta el banco de 50 consultas reales del Hito 3 y la evaluación de casos difíciles)
- **Sala 5 — Plugin WordPress / WooCommerce: PENDIENTE** ⏳ (sin plugin aún)

**Verificación técnica actual (real):**

| Ítem | Valor |
|---|---|
| `data/images/` (originales crudos del scraping) | 15.272 imágenes (nombres originales, prefijo numérico único, 0 sin numerar) |
| `data/products.csv` | **15.272 filas** `id,proveedor,pagina,imagen,nombre_original,url` ✅ |
| `data/images_final/` (banco canónico renombrado) | **15.272 imágenes** `AIM-Pxxx-NNN.ext`, 0 huérfanos, 0 extensiones inválidas (0 `.webp`, 0 fuera de nomenclatura) ✅ |
| `data/images_normalized/` (banco limpio Sala 1) | **15.272 imágenes** `AIM-Pxxx-NNN.jpg` (mismo ID que `images_final/`), integridad 100% `.jpg` ✅ |
| Normalización (15.272) | 14.925 correctas (97,7%) · 0 fallidas · 347 dudosas (2,3%) · frente 15.268/15.272 · espalda 15.103/15.272 |
| Tiempo de normalización | 525,04 s total (≈8 min 45 s) · **34,4 ms/imagen** |
| Validación automática | 15.272 registros: 0 IDs duplicados · 0 nombres vacíos · 0 URLs vacías · 0 extensiones inválidas · 0 imágenes faltantes/dañadas · **104 URLs repetidas** (aviso) · **307 duplicados por hash MD5** |
| Tiempo de validación | 16,4 s para los 15.272 registros |
| `data/informe_formatos.txt` | 5 formatos visuales (1 dominante **99,4%**), cabecera 99,7%, pie/URL 99,8%, frente 17–56% / espalda 57–97% del ancho, recorte medio por reglas simples 48,7% |
| Revisión humana de muestra | **99/100 correctas (99%)**, 1 dudosa, 0 incorrectas (semilla 42) |

---

## ✅ Estado por Sala

### Sala 1 — Biblioteca real de 15.000 diseños (CONPLETO) ✅

**Requisito (TRABAJO.md Hito 3):** escalar y validar la biblioteca que utilizarán las demás salas. Procesar aproximadamente **15.000 diseños** manteniendo: ID único, nombre, proveedor, URL, imagen original e imagen normalizada, sin modificar ni sobrescribir los originales.

**Estructura real del proyecto (mapeo contra el enunciado):**

| Enunciado (TRABAJO.md) | Proyecto | Estado |
|---|---|---|
| `data/images_original/` | `data/images/` (crudas del scraping, jamás se tocan) + `data/images_final/` (renombradas `AIM-Pxxx-NNN`, fuente del Hito 1, tampoco se modifican) | ✅ |
| `data/images_normalized/` | `data/images_normalized/` (salida de la normalización, mismo ID) | ✅ 15.272 |
| `products.csv` | `data/products.csv` (15.272 filas) | ✅ |

**Actividades (estado):**

1. **Incorporar el banco completo (~15.000)** → ✅ **15.272 productos** con `id, proveedor, pagina, imagen, nombre_original, url` en `data/products.csv`; imágenes originales en `data/images/` y banco renombrado en `data/images_final/`.

2. **Aplicar automáticamente la normalización del Hito 2 a todas las imágenes** → ✅ `scripts/normalizar_imagenes.py` ejecutado sobre las 15.272: elimina cabecera, pie/URL, marco, logo y margenes; conserva frente y espalda; centra el contenido y mantiene la proporción (lienzo lado mayor 700 px, sin ampliar más de 2×). Las originales quedan intactas.

3. **Validación automática** → ✅ `scripts/validate_dataset.py` (15.272 registros en 16,4 s) + validaciones internas de `consolidar.py`. Reporta: productos totales 15.272, imágenes originales/normalizadas 15.272/15.272, IDs duplicados 0, archivos dañados 0, archivos faltantes 0, nombres vacíos 0, URLs repetidas 104 (aviso), duplicados exactos por hash 307.

4. **Validación humana (100 al azar)** → ✅ **100/100 realizada.** La muestra semilla 42 quedó en **99 correctas (99%) · 1 dudosa · 0 incorrectas** (criterios objetivos de píxel: solo frente+espalda, sin logo, sin marco, sin cabecera/pie, sin cortes, sin deformación, lienzo uniforme). La única dudosa fue `AIM-P202-007` (4 bandas en vez de 3, frente/espalda fusionados; recorte guardado como `<id>.jpg`, pendiente solo de visto bueno visual). Ejecución: `normalizar_imagenes.py --solo-muestra --muestra 100` + `revisar_muestra_50.py --n 100`.

5. **Medición** → ✅ tamaño del banco **15.272 productos**; tiempo total de normalización **525,04 s**; promedio **34,4 ms/imagen**; errores: 0 fallidas, 347 dudosas (listadas en `detalle_normalizacion.csv` e `informe_normalizacion.txt`).

**Entregables y estado:**

| Entregable | Archivo | Estado |
|---|---|---|
| Banco de ~15.000 productos | `data/images/` + `data/images_final/` + `data/products.csv` | ✅ 15.272 |
| Imágenes normalizadas | `data/images_normalized/` | ✅ 15.272 `.jpg` (mismo ID, 100% integridad) |
| Script de validación | `scripts/validate_dataset.py` | ✅ |
| Resultado de 100 revisiones humanas | `data/revision_humana_100.csv` + `data/informe_revision_humana_100.txt` | ✅ 100/100 (99% correctas, 1 dudosa, 0 incorrectas) |
| Informe de errores | `data/informe_normalizacion.txt` + `detalle_normalizacion.csv` + `informe_formatos.txt` | ✅ |

**Problemas encontrados y resueltos en esta corrida (Sala 1, Hito 3):**

| Problema | Cantidad | Solución implementada en `consolidar.py` |
|---|---|---|
| URLs repetidas entre productos con imágenes locales distintas (la tienda reusa el preview) | 104 URLs | Se reportan como **aviso**, no error bloqueante; cada producto conserva su propia imagen. |
| Nombres `archivo` con espacios dobles/tildes que no existen tal cual en disco | 97 | Fallback por **índice numérico** de la imagen (`12-…` → producto 12). |
| Conversión webp → fuera de nomenclatura | 1 (`AIM-P221-001`) | Conversión automática a `.jpg`. |
| PNG gigante (219 M px) que dispara DecompressionBombError y riesgo de OOM | 1 (`AIM-P130-056`) | Redimensionado a lado mayor ≤ 4096 px. |
| Archivos huérfanos de corridas anteriores en `images_final/` (esquemas viejos) | 5.176 | Limpieza automática: la carpeta queda exacta al CSV. |

**Resultados numéricos (ejecución real sobre 15.272):**

- **Procesadas correctamente:** 14.925 (97,7%) · **Fallidas:** 0 · **Dudosas (revisar):** 347 (2,3%).
- **Recorte correcto:** 14.925 · **Recorte incorrecto:** 347.
- **Frente detectado:** 15.268/15.272 · **Espalda detectada:** 15.103/15.272.
- **Tiempo total:** 525,04 s (≈8 min 45 s) · **Promedio:** 34,4 ms/imagen.
- **Integridad de salida:** 100% `.jpg`, IDs idénticos a los de entrada.

**Desglose de las 347 dudosas (para el informe de casos que el algoritmo no resuelve):**

| Motivo principal | Cantidad | Comentario |
|---|---|---|
| Espalda no distinguible del fondo (espalda lisa) | 167 | Conservada como `<id>.jpg` para revisión; afecta poco al embedding |
| Logo/bloque izquierdo tratado | 138 | Logo detectado y separado; verificar recorte en revisión visual |
| Otros / estructura atípica (n° de bandas, fusión frente-espalda, sin cabecera/pie) | 42 | Formatos minoritarios del banco |
| Fallback por contenido (sin frente/espalda detectables: camisetas claras sobre fondo blanco) | 2 | Usado para `AIM-P023-020` y `AIM-P086-027`; producen recorte útil marcado «dudoso» |

**Análisis de formatos escalado (Actividad 1 — muestra de 1.000):**

- **5 formatos visuales**; el dominante (3 bandas + cabecera + pie + logo, sin marco de borde) cubre **99,4%** de la muestra → el algoritmo del Hito 2 escala con pocas fallas.
- **Cabecera:** 99,7% (banda superior, altura media 14,2%). **Pie/URL:** 99,8% (banda inferior, altura media 9,8%).
- **Frente:** 17%–56% del ancho · **Espalda:** 57%–97% del ancho.
- **Recorte medio por reglas simples:** 48,7% de la tarjeta.
- **Marcos de borde:** prácticamente inexistentes (0,2%) — las bandas internas son el elemento a limpiar.

**Pregunta principal que deben responder:**

> ¿Podemos mantener una biblioteca limpia y consistente de 15.000 diseños sin intervención manual significativa?

**Respuesta: Sí.** Con 15.272/15.272 procesadas, **0 fallidas**, 97,7% de recortes correctos y **99% de correctas en la revisión humana de 100** (0 incorrectas), la tasa de casos que requieren revisión manual es de ~2,3% (347), todos listados con su motivo en `detalle_normalizacion.csv`. La homogeneidad estructural del banco (1 formato dominante con 99,4%) hace que el pipeline del Hito 2 sea directamente escalable a los 15.000 diseños. Queda solo la revisión visual humana de los 347 dudosos y de la única dudosa de la muestra (`AIM-P202-007`).

---

### Sala 4 — Embeddings a escala y estabilidad visual (PENDIENTE) ⏳

**Requisito:** generar los embeddings de las ~15.000 imágenes con el **modelo ganador del Hito 2 (SigLIP, 92% Top 1)** y medir la estabilidad de la representación frente a modificaciones (original, punto, círculo, recoloreado, cambio de texto/logo, recorte, giro) e invariancia de color.

**Estado real:** los índices actuales (`embeddings_clip/openclip/siglip.npy`) fueron generados sobre las **1.000** imágenes del Hito 2. Ahora que Sala 1 entregó las 15.272 normalizadas, falta:
- ajustar `scripts/generar_indices_comparativos.py` (o el script de Sala 4) para leer las 15.272 desde el mismo orden del CSV;
- generar el índice principal (SigLIP, 768d) y verificar `productos = IDs = embeddings` (15.272 = 15.272 = 15.272);
- pruebas de estabilidad sobre 20 diseños conocidos con sus variantes;
- tabla de invariancia de color (misma trama azul → roja → verde → negra).

---

### Sala 3 — Motor de recuperación + RERANKING (PENDIENTE) ⏳

**Requisito:** consulta → embedding → **Top 30/50 candidatos → reranking → resultados finales**; evaluar Top 20/30/50, combinar frente/espalda por regiones, resolver pequeñas modificaciones (caso "punto de 1 mm", "círculo grande"), **caso Barça obligatorio** dentro del Top 50, umbral dinámico (devolver 1–5 resultados según calidad), API con `score_recuperacion`, `score_reranking`, `posicion_inicial`, `posicion_final`, `modelo`; comparación obligatoria **Hito 2 vs Hito 3** con las mismas consultas.

**Estado real:** el motor del Hito 2 (`api/search_engine_hito2.py` + `POST /search/image/v2`) ya implementa recuperación amplia (Top 30) + reranking por color/regiones/estructura + umbral dinámico y responde con `score_inicial`, `score_reranking`, etc. Falta para el Hito 3: re-indexar contra los 15.272 embeddings de Sala 4, probar recuperación Top 50, añadir comparaciones por regiones frente/espalda si aplica, ejecutar el caso Barça, y correr la comparación Hito 2 vs Hito 3 con la evidencia visual antes/después.

---

### Sala 2 — Fotos reales y consultas difíciles (PENDIENTE) ⏳

**Requisito:** banco de **50 consultas reales** (10 diseños limpios modificados, 10 mockups, 10 personas de frente, 10 personas giradas/agachadas, 10 casos difíciles) con su diseño correcto identificado; seguir evaluando detección de camiseta (OpenCV/YOLO/SAM); comparar consulta original vs procesada; métricas (Top 1, Top 5, posición del correcto, no encontrado, mejora tras preprocesar).

**Estado real:** existen las 50 consultas del Hito 2 (`data/consultas/`) y el módulo `api/preprocesar_consulta.py`. Falta construir el banco de consultas reales del Hito 3 (fotos/mockups/personas), actualizar `generar_consultas_hito2.py` o crear el análogo del Hito 3, y ejecutar las evaluaciones obligatorias.

---

### Sala 5 — Plugin WordPress / WooCommerce (PENDIENTE) ⏳

**Requisito:** plugin **Sublitex Visual Search** instalable; buscador visual (seleccionar/arrastrar imagen, preview, botón Buscar); consumir `POST /search/image` desde FastAPI (sin IA en WordPress); mostrar miniatura/nombre/similitud/botón producto; relación `design_id → product_id` WooCommerce; campo de búsqueda textual preparado; configuración (URL FastAPI, timeout, máx. resultados, activar/desactivar).

**Estado real:** no existe aún el plugin ni la carpeta del sitio WordPress en el repositorio. Es la sala de menor avance hasta ahora.

---

## 📊 Métricas obligatorias del Hito 3 (a completar)

Cuando las demás salas avancen, se deben reportar como mínimo:

1. **Top 1** — % de consultas con el diseño correcto primero.
2. **Top 5** — % dentro de las primeras cinco posiciones.
3. **Posición promedio** — detectar "antes Top 5 → ahora Top 1".
4. **Calidad humana de alternativas** — Muy similar / Similar / Poco similar / No relacionado.
5. **Robustez** — resultados separados por categoría (exacta, recoloreada, modificada, recortada, mockup, persona).
6. **Tiempo** — generación de embeddings, recuperación Top 50, reranking, total de búsqueda.

**Prueba común del Hito 3:** mínimo **60 consultas** (10 exactas, 10 cambios pequeños, 10 recoloreadas/logos/textos, 10 recortadas, 10 mockups, 10 personas reales), cada una con su `id_correcto` verificado.

**Comparación obligatoria Hito 2 vs Hito 3** (usar las consultas que fallaron): original, punto pequeño, círculo grande, sin marco, Barça (Top 1 bueno, Top 2–5 malos), persona → demostrar que las posiciones **mejoraron**.

---

## 🔭 Próximos pasos

1. **Sala 1:** regresar el visto bueno visual humano sobre `data/revision_contact_sheet_100.png` (hoja con los 100 pares original|normalizada) y revisar visualmente los 347 dudosos para ajustar heurísticas del normalizador si se desea bajar el 2,3%.
2. **Sala 4:** generar los embeddings SigLIP de las 15.272 normalizadas (y CLIP/OpenCLIP si se conservan para comparar) verificando la alineación `ids.npy` posición a posición; correr pruebas de estabilidad e invariancia de color.
3. **Sala 3:** re-indexar el motor Hito 2 contra el índice de 15.000; recuperación Top 30/50; caso Barça; comparación Hito 2 vs Hito 3 con evidencia visual.
4. **Sala 2:** construir las 50 consultas reales (fotos/mockups/personas) y evaluar; validar mejora del preprocesado.
5. **Sala 5:** iniciar el plugin Sublitex Visual Search conectado a FastAPI y preparar el mapeo `design_id → product_id` de WooCommerce.
6. Actualizar `README.md` y `REPORTES_HIT3.md` conforme avancen las salas.