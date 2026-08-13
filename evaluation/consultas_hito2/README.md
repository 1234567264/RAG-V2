# Prueba integrada común del Hito 2 (50 consultas)

Este directorio y `evaluation/consultas_hito2.csv` son la PRUEBA
INTEGRADA del Hito 2 (TRABAJO.md: 'Pruebas obligatorias para TODAS
las salas'). Cada consulta tiene previamente identificado el diseño
correcto (`id_correcto`).

## Estado (COMPLETO: 50/50) ✅

| Categoría | Cantidad | Quién aporta | Estado |
|---|---|---|---|
| exacta | 10 | derivada del banco (`data/images_final/`) | listo |
| sin_marco | 10 | recorte de contenido sin marco | listo |
| recoloreada | 10 | rotación de matiz + saturación + brillo | listo |
| recortada | 10 | recorte central al ~55% | listo |
| persona | 10 | mockup: camiseta sobre persona sintética con fondo | listo |

Las 50 imágenes viven en `data/consultas/` (nomenclatura `cNN_categoria.ext`:
`exacto`, `sin_marco`, `recoloreado`, `recorte`, `cuerpo`). El manifiesto es
`evaluation/consultas_hito2.csv`:

```
consulta,categoria,ruta_imagen,id_correcto
c01_exacto.jpg,exacta,data/consultas/c01_exacto.jpg,AIM-P001-001
```

## Cómo regenerar / evaluar

```bash
# Regenera las 50 consultas y el manifiesto
python scripts/generar_consultas_hito2.py

# Evalúa Hito 1 vs Hito 2 sobre las 50 consultas
python scripts/evaluar_hito2.py

# Evidencia (montajes + coherencia)
python scripts/evidencia_hito2.py
```

`scripts/evaluar_hito2.py` toma automáticamente todas las filas del CSV.
