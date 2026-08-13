# Protocolo de las 20 pruebas — Sala 2

Objetivo: demostrar que el sistema recupera correctamente imágenes similares.
Las 20 consultas se dividen en 4 grupos de 5.

## Grupos

| Grupo | Cantidad | Qué son | Qué se espera |
|---|---|---|---|
| A | 5 | Imágenes que YA están en la biblioteca | El Top 1 debe ser la misma imagen (score ~1.0) |
| B | 5 | Imágenes externas muy parecidas a algún diseño | Al menos 1 resultado del Top 5 visualmente relacionado |
| C | 5 | Imágenes diferentes (otros colores/composiciones) | Algunos resultados pueden ser útiles, otros no |
| D | 5 | Imágenes que NO son camisetas (paisajes, personas, texto) | Scores menores; marcar como Incorrecto |

## Cómo preparar las imágenes de prueba

- Grupo A: copiar 5 archivos de `data/images/`.
- Grupo B: capturas o descargas de camisetas parecidas (pueden ser otras
  variantes del mismo proveedor o diseños similares).
- Grupo C: camisetas de otros equipos/estilos.
- Grupo D: fotos que no sean camisetas.

Colocarlas en `evaluation/test_images/`.

## Cómo evaluar

1. Levantar la API: `uvicorn api.main:app --port 8000`
2. Levantar la interfaz: `streamlit run frontend/app.py`
3. Subir cada imagen de prueba, una por una.
4. Por cada resultado del Top 5 marcar:
   - **Correcto** → coincide con el diseño consultado (mismo diseño, mismo equipo, variante clara).
   - **Útil, pero no duplicado** → relacionado en estilo/color/composición, pero no es el mismo diseño.
   - **Incorrecto** → no tiene relación.
5. Escribir una observación corta (ej. "Colores y líneas similares").
6. Clic en "Guardar evaluación de esta consulta".

Cada consulta agrega 5 filas a `data/evaluation.csv`.

## Reporte final

```
python scripts/reporte_metricas.py
```

Verificar que el resultado cumpla el mínimo del supervisor:
- 20 consultas evaluadas.
- Al menos 70% con resultados razonablemente relacionados (Top 5 útil).
