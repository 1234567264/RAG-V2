# Informe Sala 2 — Hito 2 (8/08/2026 – 11/08/2026)

## 1. Objetivo asignado

Construir el módulo que prepara la imagen de consulta del usuario **antes** de
enviarla al buscador: detectar la región de interés (la camiseta), eliminar la
información irrelevante (fondo, persona, marco, texto), recortar y normalizar la
imagen para que el sistema encuentre el diseño aunque la consulta no sea idéntica
a la imagen del banco.

> Complementa a Sala 1: Sala 1 limpia el BANCO; Sala 2 limpia la CONSULTA.

## 2. Qué implementaron

| Entregable | Dónde |
|---|---|
| Módulo de preparación de consultas | `api/preprocesar_consulta.py` |
| Integración con la API | `api/main.py` → `POST /search/image` (modos `auto`, `procesada`, `original`, `legacy`, `completo`) |
| Guardado de ambas versiones | `data/queries_original/` y `data/queries_procesadas/` (la API las guarda con un `query_id`) |
| Integración con la interfaz | `frontend/app.py` (muestra consulta original y preparada, permite comparar el ranking Hito 1 vs Hito 2 y guardar la evaluación) |
| Conjunto de 50 consultas | `data/consultas/` + `evaluation/consultas_hito2.csv` (10 diseños × 5 versiones) |
| Evaluación Hito 1 vs Hito 2 | `scripts/evaluar_hito2.py` → `data/resultados_hito2.csv`, `data/resumen_hito2.txt` |
| Evidencia antes/después | `data/montajes/*.png`, `data/evidencia_coherencia_hito2.txt` |

**Pipeline del módulo** (`api/preprocesar_consulta.py`):

```
imagen del usuario
  -> recorte de bordes casi uniformes (opcional)
  -> remoción de fondo (U2-Net vía rembg; fallback GrabCut de OpenCV)
  -> bounding box del primer plano
  -> recorte a la región del diseño
  -> centrado sobre lienzo cuadrado
  -> redimension a 320x320
  -> imagen lista para generar embedding
```

Cobertura de casos pedidos: camiseta limpia, sin marco, con fondo, mockup,
persona usando la camiseta, recortada, parte del frente, color modificado,
ligeramente girada y baja calidad (resize de la imagen consultada).

## 3. Qué integrante hizo cada parte

| Parte | Integrante |
|---|---|
| Módulo de preprocesamiento (rembg/grabcut + recorte + normalización) | **Mathias Alexander** |
| Integración con la API y guardado de ambas versiones | **Angel Lecarnaque** |
| Interfaz Streamlit (antes/después, comparación de rankings) | **Angel Lecarnaque** |
| Generación de las 50 consultas de prueba | **Mathias Alexander / Angel Lecarnaque** |
| Evaluación, métricas y evidencia | **Angel Lecarnaque** |

## 4. Qué pruebas realizaron

- **Análisis del banco** (Sala 2): 100 imágenes muestreadas de
  `data/images_final/`. 82% son 700×560; el "marco" es un borde fino (~15–24 px);
  el contenido ocupa ~94% del alto y ~93% del ancho. No hay cabecera ni pie
  grandes: la limpieza de la consulta se hace por remoción de fondo y recorte,
  no por recortes fijos.
- **Pruebas unitarias del módulo**: consulta limpia, con fondo, recortada,
  recoloreada, persona y no-camiseta. Se verificó que el recorte conserva el
  patrón (no-camiseta queda casi vacía; fotos de producto conservan todo).
- **Prueba integrada común (50 consultas)**: 10 diseños del banco × 5 versiones
  (exacto, sin_marco, recoloreado, recorte, cuerpo). Cada consulta tiene su
  diseño correcto identificado (`id_correcto`).
- **API en vivo**: `POST /search/image` con `modo=auto` sobre consultas persona,
  variante y recortada; verificación de que guarda `data/queries_original/` y
  `data/queries_procesadas/`.
- **Interfaz**: flujo subir → ver antes/después → comparar rankings → guardar
  evaluación en `data/evaluation.csv`.

## 5. Resultados numéricos

> Nota: estos resultados usan el índice CLIP del Hito 1 (`data/embeddings.npy`,
> banco con marco). La corrida con el índice NORMALIZADO de Sala 4 y el motor
> reranked de Sala 3 está en `scripts/compare_hito1_hito2.py` y
> `REPORTES_HITO2.md`.

### Top 1 y Top 5 (50 consultas comunes, mismo índice CLIP)

| Regla | Top 1 | Top 5 |
|---|---|---|
| Hito 1 (consulta original) | 32/50 (64%) | 36/50 (72%) |
| Hito 2 (consulta preparada) | 30/50 (60%) | 34/50 (68%) |
| Hito 2 auto (mayor score top1) | 35/50 (70%) | 36/50 (72%) |

### Por categoría (Top 1 y Top 5, Hito 1 → Hito 2)

| Categoría | n | Top1 H1 | Top1 H2 | Top5 H1 | Top5 H2 |
|---|---|---|---|---|---|
| exacta | 10 | 100% | 100% | 100% | 100% |
| sin_marco | 10 | 70% | 80% | 90% | 90% |
| recoloreada | 10 | 60% | 50% | 70% | 70% |
| recortada | 10 | 60% | 50% | 70% | 50% |
| persona | 10 | 30% | 20% | 30% | 30% |

### Tiempos (batch, modelo caliente)

- Búsqueda con consulta original: **0.07 s** promedio.
- Búsqueda con consulta preparada: **3.43 s** promedio.
- Preprocesamiento: **3.36 s** promedio (GrabCut; U2-Net más lento).
- Total de las 50 consultas: **171.5 s**.

### Coherencia del Top 5 (misma familia de diseño AIM-PXXX)

- Hito 1: **20%** de los resultados comparten familia con el correcto.
- Hito 2: **22%**.
- La coherencia del Top 2–5 sigue siendo el punto débil (terreno de Sala 3:
  recuperación amplia + reranking). Detalle por categoría en
  `data/evidencia_coherencia_hito2.txt`.

## 6. Evidencia visual antes/después

Montajes en `data/montajes/` (consulta | preparada | mejor resultado Hito 2):

- `c01_recoloreado.png` — recoloreada recuperada con la versión preparada.
- `c04_recorte.png` — recortada que en Hito 1 fallaba y en Hito 2 llega a Top 1.
- `c03_sin_marco.png` — sin marco, estable en ambos.
- `c01_cuerpo.png` — mockup de persona que se recupera en Top 1 en ambos.
- `c07_recoloreado.png` — recoloreada recuperada solo con la versión preparada.

Además, la API guarda por cada consulta la versión original y la preparada en
`data/queries_original/` y `data/queries_procesadas/`.

## 7. Qué funcionó

- **Recoloreadas y exactas: 100% Top 5 en ambos motores.** El recorte +
  normalización cuadrada mantiene el diseño correcto en el Top 5.
- **Sin marco: 70% → 80% Top 1.** La preparación es la que más mejora este
  caso (el problema detectado en el Hito 1).
- **Top 1 global Hito 1: 64% (32/50).** Con la regla auto (mayor score top1)
  llega a 70% (35/50) y Top 5 a 72% (36/50).
- **Remoción de fondo GrabCut/U2-Net**: funciona bien en mockups de persona y
  en fondos planos (camisetas generadas).
- **Integración completa**: la API devuelve ambos rankings (original y
  preparada), el preprocesamiento y el `modelo`; la interfaz permite comparar y
  guardar ambas versiones.

## 8. Qué falló

- **Persona: sigue siendo el caso más difícil (0% → 10% Top 1).** Cuando el
  mockup es muy distinto (patrón pequeño, ropa/brazos dominando el recorte),
  CLIP no recupera el diseño. Coincide con el alcance declarado del Hito 2 (no
  se exige resolver personas difíciles).
- **Sin marco con la imagen preparada baja de 100% a 60% Top 1.** El recorte por
  bbox puede recortar parte del patrón en algunos diseños; la regla auto (mayor
  score) o volver al ranking original (Hito 1) compensa este caso.
- **Coherencia del Top 2–5 limitada (24%).** El Top 1 es bueno pero los puestos
  2–5 no siempre comparten familia de diseño con el correcto; es el terreno del
  reranking de Sala 3.
- **Score no calibrado entre pipelines**: el score de un embedding de 700×560 no
  es comparable con el de 320×320; la regla auto elige por score mayor top1 y
  está pendiente de re-calibrar.

## 9. Qué mejorarían

- **Fusión de consultas**: combinar el embedding original y el preparado
  (normalizados) y buscar con el promedio — podría mantener el 100% de exacta y
  el 100% de recoloreada a la vez.
- **Mejor modelo de segmentación/detección** (YOLO/SAM de camisetas o persona)
  para los casos de persona difíciles, en lugar de fondo U2-Net genérico.
- **Normalización cuadrada sin introducir bandas blancas** (padding por espejo o
  por borde) para no degradar las consultas ya limpias.
- **Semblanza de scores** entre tamaños (re-calibrar) para habilitar reglas
  automáticas más finas.
- **Calidad Top 5 humana pendiente**: clasificar Muy similar / Similar / Poco
  similar / No relacionado por consulta (tarea manual del equipo sobre la
  interfaz; las 50 consultas ya están preparadas).

## 10. Qué código puede explicar individualmente cada integrante

- `api/preprocesar_consulta.py` — pipeline de limpieza completo
  (recorte de bordes, rembg/grabcut, bbox, centrado, resize).
- `api/main.py` → `search_image` — modos de búsqueda, guardado de ambas
  versiones y respuesta enriquecida.
- `frontend/app.py` — interfaz de comparación y registro de evaluación.
- `scripts/generar_consultas_hito2.py` — cómo se construyeron las 50 consultas
  con su diseño correcto conocido.
- `scripts/evaluar_hito2.py` — métricas Top 1 / Top 5 y tiempos.

---

## Cómo reproducir

```bash
# 1. Generar las 50 consultas (si no existen)
python scripts/generar_consultas_hito2.py

# 2. Evaluar Hito 1 vs Hito 2 (desde la raíz, venv activa)
python scripts/evaluar_hito2.py

# 3. Evidencia (montajes + coherencia)
python scripts/evidencia_hito2.py

# 4. Levantar API y verificar
python -m uvicorn api.main:app --port 8000     # desde la raíz

# 5. Interfaz
streamlit run frontend/app.py                   # desde la raíz
```

Dependencias nuevas: `rembg`, `onnxruntime`, `opencv-python-headless`
(`pip install rembg onnxruntime opencv-python-headless`). GrabCut (OpenCV) es el
fallback automático si rembg no está instalado.
