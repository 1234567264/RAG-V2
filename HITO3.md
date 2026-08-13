# HITO 3 — Escala real, reranking y conexión WordPress
**Fechas:** 11/08/2026 al 14/08/2026

---

## 🎯 Visión General
Escalar el buscador visual desde 1.000 hasta aproximadamente **15.000 diseños reales** y mejorar su calidad para que no solo encuentre el diseño correcto, sino que mantenga ese diseño en las primeras posiciones aunque la consulta tenga modificaciones, recortes, cambios de color, logos, fotografías reales o una persona usando la camiseta.
Al mismo tiempo, se iniciará la integración con **WordPress/WooCommerce** mediante un plugin que consuma el mismo motor inteligente.

### Problemas que debe resolver este Hito:
* Pequeñas modificaciones pueden hacer caer el diseño correcto del Top 1 al Top 3, 4 o 5.
* Los resultados Top 2–5 muchas veces no tienen semejanza visual real.
* El sistema actualmente devuelve los vectores matemáticamente más cercanos, aunque algunos no sean útiles.
* Falta probar el comportamiento sobre una biblioteca mucho mayor.
* Las fotografías de personas, perspectivas, arrugas y vistas parciales siguen siendo casos difíciles.
* WordPress todavía no consume directamente el buscador.

### Resultados Esperados:
* Biblioteca normalizada de aprox. 15.000 diseños.
* Embeddings correspondientes a todo el banco.
* Recuperación inicial de Top 30–50 candidatos.
* Reranking de esos candidatos.
* Top final visualmente más coherente.
* Capacidad de devolver menos de cinco resultados si no existen cinco suficientemente similares.
* Pruebas con fotografías reales y personas usando camisetas.
* Comparación objetiva Hito 2 vs Hito 3.
* Primer plugin WordPress conectado a FastAPI.

---

## 📦 SALA 1 — Biblioteca real de 15.000 diseños
**Objetivo:** Escalar y validar la biblioteca que utilizarán las demás salas.

### Actividades:
1. **Incorporar el banco completo:** Procesar aprox. 15.000 diseños manteniendo:
   * ID único, nombre, proveedor, URL, imagen original e imagen normalizada.
   * Estructura recomendada: `data/images_original/` y `data/images_normalized/` (No modificar ni sobrescribir los originales).
2. **Aplicar automáticamente la normalización del Hito 2:** A todas las imágenes (eliminar marco cuando corresponda, eliminar cabecera/pie, reducir elementos externos, conservar frente y espalda, centrar diseño, mantener proporción uniforme).
3. **Validación automática:** Reportar productos totales, imágenes originales, imágenes normalizadas, IDs duplicados, archivos dañados, faltantes, nombres vacíos, URLs repetidas y duplicados exactos mediante hash.
4. **Validación humana:** Seleccionar aleatoriamente 100 imágenes normalizadas y clasificarlas en: *correcta*, *usable con pequeña falla*, *incorrecta*.
5. **Medición:** Reportar tamaño total del banco, tiempo total de normalización, promedio por imagen y cantidad de errores.

### Entregable Sala 1:
* Banco aproximado de 15.000 productos.
* `products.csv`.
* Imágenes normalizadas.
* Script de validación.
* Resultado de las 100 revisiones humanas.
* Informe de errores.
* **Pregunta principal:** ¿Podemos mantener una biblioteca limpia y consistente de 15.000 diseños sin intervención manual significativa?

---

## 🔍 SALA 4 — Embeddings a escala y estabilidad visual
**Objetivo:** Generar los embeddings de las 15.000 imágenes y determinar qué representación visual mantiene mejor identificado un diseño cuando sufre modificaciones.

### Actividades:
1. **Utilizar el modelo ganador del Hito 2:** (Conservar ambos si quedaron muy próximos para evaluar sistema combinado).
2. **Generar embeddings de las 15.000 imágenes:** Procesamiento por lotes. Reportar cantidad, dimensiones, fallidos, tiempo total, tiempo por imagen y tamaño del índice. Verificar: `número de productos = número de IDs = número de embeddings`.
3. **Prueba de estabilidad:** Seleccionar mínimo 20 diseños conocidos. Crear variantes (original, punto pequeño, círculo grande, recoloreado, cambio de texto, cambio de logo, recorte parcial, giro ligero). Registrar posición, score, si aparece Top 1/Top 5 o si desaparece.
4. **Probar invariancia de color:** Determinar dependencia del color frente a la trama (ej. misma trama azul → roja → verde → negra).
5. **Entregar resultados a Sala 3:** Permitir solicitar Top 30 o Top 50 candidatos utilizando estos embeddings.

### Entregable Sala 4:
* Índice de aprox. 15.000 embeddings.
* Tabla de estabilidad.
* Resultados por tipo de modificación.
* Tiempo de generación.
* Recomendación técnica para el reranking.
* **Pregunta principal:** ¿Qué tan estable es la representación del diseño cuando modificamos elementos que no deberían cambiar su identidad?

---

## ⚙️ SALA 3 — Motor de recuperación + RERANKING
**Objetivo principal:** Mejorar el ranking. El sistema ya no debe considerar que los primeros cinco embeddings matemáticamente más cercanos son necesariamente los mejores resultados.

### Nuevo flujo obligatorio:
* **Antes:** Consulta → embedding → Top 5
* **Ahora:** Consulta → embedding → Top 30/50 candidatos → reranking → resultados finales

### Actividades:
1. **Recuperación amplia:** Evaluar Top 20, 30, 50 para determinar cuál ofrece suficientes candidatos sin aumentar demasiado el tiempo.
2. **Implementar reranking:** Investigar y probar combinaciones de: embedding global, similitud de trama, similitud estructural, frente, espalda, geometría, distribución gráfica, color con menor peso, segundo modelo visual y comparación por regiones (No asumir los pesos, probar configuraciones).
3. **Frente y espalda:** Comparar independientemente cuando sea posible (frente consulta ↔ frente candidato, espalda consulta ↔ espalda candidato) y combinar.
4. **Resolver el problema de pequeños cambios:** Usar casos obligatorios (original, punto 1 mm, círculo grande, color, logo) y comparar posición antes y después del reranking.
5. **Caso Barça (Prueba obligatoria):** Consulta camiseta del FC Barcelona. Analizar Top 50 (misma camiseta, otras del Barça, tramas parecidas, colores parecidos) y aplicar reranking comparando Top 5 antes y después.
6. **No forzar cinco resultados:** Sistema capaz de devolver 1, 2, 3, 4 o 5 resultados según calidad. Si no superan un umbral basado en pruebas (no arbitrario), no deben mostrarse.
7. **API:** Actualizar `POST /search/image` para devolver: `id`, `score_recuperacion`, `score_reranking`, `posicion_inicial`, `posicion_final`, `modelo`, `nombre`, `imagen`, `url`.
8. **Medición:** Comparar exactamente las mismas consultas Hito 2 vs Hito 3.

### Entregable Sala 3:
* Recuperación Top 30/50.
* Reranker.
* API actualizada.
* Tabla antes/después.
* Caso Barça.
* Pruebas de pequeñas modificaciones.
* Tiempo de consulta.
* Evidencia visual de mejora.
* **Pregunta principal:** ¿Podemos mantener el diseño correcto arriba y conseguir que los resultados alternativos realmente se parezcan?

---

## 📸 SALA 2 — Fotos reales y consultas difíciles
**Objetivo:** Evaluar el buscador en condiciones próximas al uso real (fotografías, screenshots, jugadores, modelos, camisetas dobladas, de costado, parcialmente visibles).

### Actividades:
1. **Crear banco de pruebas:** Mínimo 50 consultas reales (10 limpios modificados, 10 mockups, 10 personas de frente, 10 personas giradas/agachadas, 10 casos difíciles). Cada imagen debe tener identificado su diseño correcto.
2. **Mejorar detección de camiseta:** Continuar evaluando OpenCV, YOLO, segmentación, SAM u otras alternativas justificadas. Flujo: `foto → detectar camiseta → recortar región → normalizar → buscar`.
3. **Comparar consulta original vs procesada:** Registrar cuál funciona mejor.
4. **Casos parciales:** Incluir solo pecho, espalda, de costado, parcialmente cubierta, arrugas, baja resolución.
5. **Evaluación:** Registrar Top 1, Top 5, posición del diseño correcto, no encontrado y mejora después de preprocesar.

### Entregable Sala 2:
* Banco de 50 consultas.
* Procesamiento antes/después.
* Métricas.
* Casos que funcionan y casos que continúan fallando.
* Evidencias visuales.
* **Pregunta principal:** ¿Hasta qué punto una fotografía real puede transformarse en una consulta útil para encontrar el diseño original?

---

## 🔌 SALA 5 — Plugin WordPress / WooCommerce
**Integrantes:** Los dos estudiantes que anteriormente trabajaron con plugins.
**Objetivo:** Construir el primer puente entre el motor inteligente y la plataforma de e-commerce (Sin implementar IA dentro de WordPress).

### Arquitectura:
`WordPress` → `Plugin` → `FastAPI` → `Motor visual` → `Plugin` → `Resultados WooCommerce`

### Actividades:
1. **Crear plugin propio:** Nombre provisional *Sublitex Visual Search* (instalable como plugin normal de WP).
2. **Crear buscador visual:** Permitir seleccionar/arrastrar imagen, mostrar preview y botón Buscar.
3. **Consumir FastAPI:** Enviar imagen mediante `POST /search/image` (sin generar embeddings en WordPress).
4. **Mostrar resultados:** Miniatura, nombre, similitud y botón para abrir producto.
5. **Relación con WooCommerce:** Preparar relación `design_id → product_id WooCommerce`. La API devuelve el `design_id` y WordPress encuentra el producto.
6. **Preparar búsqueda textual:** Agregar campo visual "Buscar diseños..." (preparar interfaz para el siguiente hito).
7. **Administración del plugin:** Configuración para URL de FastAPI, timeout, cantidad máx. de resultados y activar/desactivar búsqueda visual.

### Entregable Sala 5:
* Plugin instalable.
* Buscador visual dentro de WordPress.
* Conexión real con FastAPI.
* Resultados vinculados a WooCommerce.
* Configuración básica y demostración funcional.
* **Pregunta principal:** ¿Puede WordPress consumir el motor inteligente sin duplicar dentro de WordPress la lógica de IA?

---

## 🧪 PRUEBA COMÚN DEL HITO 3
Todas las salas utilizarán un conjunto conocido de **mínimo 60 consultas**:
* 10 exactas
* 10 cambios pequeños
* 10 recoloreadas/logos/textos
* 10 recortadas
* 10 mockups
* 10 personas reales

### Métricas Obligatorias:
1. **Top 1:** % de consultas donde el diseño correcto aparece primero.
2. **Top 5:** % donde aparece dentro de las primeras cinco posiciones.
3. **Posición promedio:** Para detectar cambios (ej. antes Top 5 → ahora Top 1).
4. **Calidad humana de alternativas:** Clasificar cada Top alternativo en *Muy similar*, *Similar*, *Poco similar*, *No relacionado*.
5. **Robustez:** Separar resultados según categoría de consulta.
6. **Tiempo:** Medir generación de embeddings, recuperación Top 50, reranking y tiempo total.

### Comparación obligatoria Hito 2 vs Hito 3:
Demostrar la mejora de posiciones con casos problemáticos (ej. original, punto pequeño, círculo grande, sin marco, Barça, persona).

### Criterio de Éxito:
Sobre una biblioteca cercana a **15.000 diseños**, el motor mantiene una buena recuperación frente a modificaciones y fotografías reales, mejora la coherencia visual mediante reranking y ya puede consumirse desde WordPress mediante un plugin independiente. Demostrar mejora medible respecto al Hito 2.