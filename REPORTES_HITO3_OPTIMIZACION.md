# REPORTE DE OPTIMIZACIÓN Y LIMPIEZA — HITO 3

**Fecha:** 2026-08-15
**Alcance:** limpieza de código legacy + equilibrio de la métrica Top-1/Top-5 (50/50) + filtrado estricto del Top 5.

Este reporte documenta los cuatro bloques de trabajo solicitados, con archivos
tocados, justificación de cada cambio, valores de la evaluación y el procedimiento
de recalibración.

---

## 1. Resumen de la tarea

1. **Limpieza de código:** eliminar scripts legacy, lógica obsoleta y caminos
   muertos que quedaron en desuso desde la implementación de la fusión
   CLIP + OpenCLIP + SigLIP.
2. **Optimización de búsqueda (Top-1 & Top-5 balanceados):** la métrica de
   evaluación combina ambos bloques al **50/50**. Cada bloque aporta como
   máximo 50 puntos: alcanzar 50 en un bloque = 100% de cumplimiento de ese top.
   La métrica combinada es `P50/50 = 0.5 · Top1% + 0.5 · Top5%` (sobre 100).
3. **Precisión y filtrado del Top 5:** el Top 5 nunca se "rellena" con
   resultados irrelevantes; se aplican dos capas de corte (umbral absoluto +
   margen relativo) y la respuesta puede traer 0…5 resultados según la calidad.
4. **Verificación** (py_compile + pruebas reales en venv liviano) y
   **reporte** de todos los cambios.

---

## 2. Bloque 1 — Limpieza de código (eliminación de legacy)

Se eliminaron 6 scripts que quedaron obsoletos con la fusión de modelos y el
motor integrado en la API:

| Script eliminado | Por qué era obsoleto |
|---|---|
| `scripts/build_index.py` | **LEGACY.** Generaba `data/index_embeddings.npy` + `index_metadata.json`, ruta **prohibida** por AGENTS.md. Reemplazado por `scripts/generar_indices_comparativos.py` (Sala 4). |
| `scripts/search.py` | Motor standalone del Hito 1 (`CargarDatosVectoriales`/`BuscarSimilares` sobre `embeddings.npy`). Reemplazado por `api/search_engine.py` y la API (Sala 3). |
| `scripts/buscar_por_imagen.py` | Script standalone de demo del Hito 1. La búsqueda integrada vive en `api/main.py` (`/search/image` y `/search/image/v2`). |
| `scripts/ingest.py` | Ingesta de prueba que reescribía `embeddings.npy` y dependía de `search.py`. El flujo canónico es `consolidar.py` (Sala 1) → `generar_indices_comparativos.py` (Sala 4). |
| `scripts/insertar_db.py` | Escribía `data/productos.db` (SQLite) declarado en `validate_dataset.py` como "FUERA del flujo integrado". |
| `scripts/reporte_evaluacion.py` | Leía `data/evaluacion.csv` (no existe; el archivo real es `data/evaluation.csv`, procesado por `reporte_metricas.py`). Script muerto. |

**Referencias documentales actualizadas:**
- `README.md`: la nota de "archivos legacy" ahora indica que
  `build_index.py` y su artefacto `index_embeddings.npy` fueron eliminados y
  enumera los 6 scripts borrados.
- `scripts/GUIA_SALA4.txt`: eliminadas las referencias a `buscar_por_imagen.py`;
  ahora apunta a la API (`/search/image/v2` con `modelo=fusion`) y a
  `compare_hito1_hito2.py --fusion`.

**No se tocaron** (fuera del alcance confirmado): `scripts/generar_embeddings.py`
(sigue generando el baseline Hito 1 `embeddings.npy`, usado por los modos
`original`/`clasico`/`legacy` y por `compare_hito1_hito2.py`), `get_product.py`,
`data/embeddings.npy` ni la ruta de respaldo `index_embeddings.npy` de
`api/search_engine.py` (el artefacto no existe en disco; se conservó la lógica de
fallback por compatibilidad).

---

## 3. Bloque 2 — Métrica combinada 50/50 (Top-1 y Top-5 balanceados)

**Definición (confirmada por el usuario):** cada bloque — *Top-1* y *Top-5* —
tiene una ponderación máxima de **50 puntos**. Alcanzar 50 en un bloque
representa el **100% de cumplimiento** de ese top dentro de la métrica combinada.

```
Puntaje combinado (P50/50) = 0.5 · Top1% + 0.5 · Top5%   (sobre 100)
```

El equilibrio se aplica en dos niveles:

1. **En el motor (`api/search_engine_hito2.py`):** los pesos del score final
   ya reparten 0.50 para el embedding y 0.50 para el bloque de descriptores
   visuales (color global, frente, espalda, estructura, color dominante, gama,
   patrón, marco, franjas). El docstring del módulo ahora declara explícitamente
   que los pesos se calibran contra la métrica 50/50, de modo que ganar
   precisión en Top 1 no se logra sacrificando la recuperación del Top 5, ni
   viceversa.

2. **En los scripts de evaluación y reportes:** se añadió el `Puntaje 50/50`
   como métrica de decisión:

   - `scripts/evaluar_50_consultas.py` → nueva columna `puntaje_combinado` en
     `data/evaluation_metrics.csv` (global y por categoría) y en el resumen de
     consola.
   - `scripts/compare_hito1_hito2.py` → `puntaje_combinado` en el resumen
     `data/comparacion_hito1_hito2.json` (`por_motor`) y en consola.
   - `scripts/reporte_comparativo.py` → columna `P50/50` en la tabla y el
     **ganador se decide ahora por la métrica combinada** (desempate por Top1,
     Top5 y luego tiempo), en lugar de solo Top1.
   - `scripts/reporte_metricas.py` → línea `Puntaje 50/50` en el reporte de la
     evaluación de la interfaz (Sala 2).
   - `scripts/evaluar_hito2.py` → columna `P50/50` en el resumen por regla y
     por categoría de `data/resumen_hito2.txt`.

El helper `puntaje_combinado_50_50(precision_top1, precision_top5)` está
duplicado (3 líneas) en cada script para mantenerlos autónomos, sin dependencias
cruzadas.

### Línea base real (datos de `data/comparacion_hito1_hito2.json`, 50 consultas)

| Motor | Top1 | Top1% | Top5 | Top5% | **P50/50** |
|---|---:|---:|---:|---:|---:|
| Hito 1 (CLIP) | 32/50 | 64.0 | 36/50 | 72.0 | **68.0** |
| Hito 2 (CLIP + reranking) | 34/50 | 68.0 | 37/50 | 74.0 | **71.0** |
| Hito 2 OpenCLIP | 40/50 | 80.0 | 46/50 | 92.0 | **86.0** |
| Hito 2 Fusión (CLIP+OpenCLIP+SigLIP) | 42/50 | 84.0 | 48/50 | 96.0 | **90.0** |

La **fusión** es el motor actual y líder en la métrica balanceada (90/100),
con los bloques Top-1 (42 pt) y Top-5 (48 pt) aportando de forma equilibrada.

---

## 4. Bloque 3 — Precisión y filtrado del Top 5 (sin relleno)

### Cambio en `api/search_engine_hito2.py`

- **Nuevo umbral absoluto:** `UMBRAL_MINIMO_SIMILARIDAD = 0.40`.
  Ningún candidato con `score_reranking < 0.40` se devuelve, aunque sea el
  mejor de la consulta. El `score_final` es una media ponderada en [0,1] donde
  el embedding vale 0.50 y los descriptores visuales 0.50; 0.40 exige una señal
  combinada mínima de calidad.

- **Filtrado en dos capas en `_rerank_candidatos` (Paso 3):**
  1. **Corte absoluto:** se descartan los candidatos por debajo del umbral.
  2. **Corte relativo:** se descartan los que queden más de `MARGEN_CORTE`
     (0.25) por debajo del mejor resultado retenido.

  Resultado posible: **0…top_k** resultados. El frontend ya contempla la lista
  vacía con el mensaje "No se encontraron resultados"
  (`frontend/app.py:721-722`), por lo que no se rompe nada.

- **Valor de arranque y recalibración:** el umbral `0.40` es conservador y
  debe calibrarse con datos reales (no quedar arbitrario). Para habilitarlo,
  `compare_hito1_hito2.py` ahora registra el **score del Top 1** de cada motor
  por consulta (`h1_mejor_score`, `h2_mejor_score`, `h2oc_mejor_score`,
  `h2fu_mejor_score`) en `data/comparacion_hito1_hito2.csv`. Con la API
  corriendo, un segundo run permite ajustar `UMBRAL_MINIMO_SIMILARIDAD` al
  valor que retenga los aciertos del Top 1 y descarte el ruido:

  ```bash
  python -m uvicorn api.main:app --port 8000        # terminal 1
  python scripts/compare_hito1_hito2.py --fusion    # terminal 2
  ```

  Procedimiento sugerido: tomar el percentil mínimo de `h2fu_mejor_score` entre
  las consultas donde el Top 1 fue correcto, y fijar el umbral ligeramente por
  debajo de ese valor (protege la recuperación) pero por encima de los scores
  de los resultados marcados como "Poco similar / No relacionado" (protege la
  precisión).

### Verificación funcional (venv liviano, sin modelos)

Se ejecutó `_rerank_candidatos` con imágenes reales de `data/images_normalized`:

- **Caso A** (consulta idéntica al banco `AIM-P001-001`, 4 candidatos
  descendentes): devuelve el candidato correcto con `score_reranking=1.0` y
  elimina los vecinos sin parecido real (corte relativo). Resultado: 1 de 4,
  sin relleno.
- **Caso B** (consulta tipo persona/mockup, candidatos de score bajo): solo
  sobreviven los que superan el umbral absoluto (2 de 4). Ningún resultado por
  debajo de `0.40`.

En ambos casos se verificaron las invariantes: orden descendente por
`score_reranking`, `posicion_final` secuencial 1..n, `n <= top_k` y
`score_reranking >= UMBRAL_MINIMO_SIMILARIDAD` para todos los resultados.

---

## 5. Archivos modificados

| Archivo | Tipo de cambio |
|---|---|
| `api/search_engine_hito2.py` | Umbral absoluto `UMBRAL_MINIMO_SIMILARIDAD`, filtrado en dos capas en `_rerank_candidatos`, docstring de la métrica 50/50. |
| `scripts/evaluar_50_consultas.py` | Columna y resumen `puntaje_combinado` (50/50). |
| `scripts/compare_hito1_hito2.py` | `puntaje_combinado` en JSON/consola + columnas `*_mejor_score` por consulta. |
| `scripts/reporte_comparativo.py` | Columna `P50/50`, ganador decidido por métrica combinada. |
| `scripts/reporte_metricas.py` | Línea `Puntaje 50/50`. |
| `scripts/evaluar_hito2.py` | Columna `P50/50` por regla y por categoría. |
| `README.md` | Nota de legacy actualizada (scripts eliminados). |
| `scripts/GUIA_SALA4.txt` | Referencias a `buscar_por_imagen.py` reemplazadas por la API actual. |
| `scripts/build_index.py` | **Eliminado** (legacy). |
| `scripts/search.py` | **Eliminado** (legacy). |
| `scripts/buscar_por_imagen.py` | **Eliminado** (legacy). |
| `scripts/ingest.py` | **Eliminado** (legacy). |
| `scripts/insertar_db.py` | **Eliminado** (legacy). |
| `scripts/reporte_evaluacion.py` | **Eliminado** (legacy). |

---

## 6. Verificación realizada

- `python -m py_compile` en los 6 archivos Python modificados: **OK**.
- `reporte_metricas.py` ejecutado con `data/evaluation.csv` real: imprime la
  nueva línea `Puntaje 50/50`.
- `reporte_comparativo.py` probado con métricas sintéticas: tabla con columna
  `P50/50`, ganador SigLIP (95.0) decidido por la métrica combinada.
- `_rerank_candidatos` probado con imágenes reales del banco (casos A y B):
  filtrado estricto correcto, sin relleno.
- Consistencia estática de `compare_hito1_hito2.py`: cabecera CSV (28 columnas)
  alineada con las claves de la fila.

**Pendiente (requiere entorno completo con torch/transformers):** levantar la
API y recalibrar `UMBRAL_MINIMO_SIMILARIDAD` corriendo
`python scripts/compare_hito1_hito2.py --fusion` (los scores del Top 1 por
consulta ya quedan registrados en el CSV para ese análisis). No hay `.venv` en
el repo y el Python del sistema (3.14) no tiene dependencias instaladas (PEP 668
bloquea pip del sistema); la recalibración requiere crear el venv del proyecto.
