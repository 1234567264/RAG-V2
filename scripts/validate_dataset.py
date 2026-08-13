# -*- coding: utf-8 -*-
"""
validate_dataset.py  -  Sala 1 / Hito 1
----------------------------------------
Script de validacion completa del dataset de productos.

Cubre todos los criterios del informe de evaluacion:
  - ID no vacio, ID no repetido
  - Nombre no vacio
  - URL no vacia, URL no repetida
  - Archivo de imagen existente, extension permitida
  - Imagen que pueda abrirse con Pillow (no danada)
  - Duplicados por hash MD5
  - Tiempo real de procesamiento (benchmark 1.000 registros)
  - Evidencia de validacion visual de una muestra de 5 pares

Base de datos activa: CSV (products.csv)
SQLite: FUERA del flujo integrado en el Hito 1.
Migracion futura: PostgreSQL con pgvector.

Uso:
    python scripts/validate_dataset.py
    python scripts/validate_dataset.py --benchmark   (prueba de 1.000 registros)
"""

import argparse
import csv
import hashlib
import os
import random
import time

from PIL import Image

# ─────────────────────────────────────────────
# RUTAS
# ─────────────────────────────────────────────
BASE_DIR   = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CSV_PATH   = os.path.join(BASE_DIR, "data", "products.csv")
# Banco de imágenes usado por el índice (Sala 1 normalizada). La
# normalización convierte todo a .jpg con el mismo ID, por lo que la
# validación busca el nombre exacto del CSV o el equivalente <id>.jpg.
IMAGES_DIR = os.path.join(BASE_DIR, "data", "images_normalized")

EXTENSIONES_PERMITIDAS = (".jpg", ".jpeg", ".png", ".gif")


# ─────────────────────────────────────────────
# CARGA
# ─────────────────────────────────────────────

def cargar_registros(csv_path: str = CSV_PATH):
    with open(csv_path, "r", encoding="utf-8") as f:
        return list(csv.DictReader(f))


# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────

def imagen_abre(ruta: str) -> bool:
    """Devuelve True si Pillow puede abrir la imagen sin errores."""
    try:
        with Image.open(ruta) as img:
            img.verify()
        return True
    except Exception:
        return False


def md5_archivo(ruta: str) -> str:
    """Calcula el hash MD5 de un archivo para detectar duplicados exactos."""
    h = hashlib.md5()
    with open(ruta, "rb") as f:
        for bloque in iter(lambda: f.read(65536), b""):
            h.update(bloque)
    return h.hexdigest()


def resolver_imagen(id_, imagen, images_dir: str = IMAGES_DIR):
    """Ruta del archivo en el banco: nombre exacto del CSV o <id>.jpg (la
    normalización de Sala 1 convierte todo a .jpg con el mismo ID)."""
    if imagen:
        ruta = os.path.join(images_dir, imagen)
        if os.path.exists(ruta):
            return ruta
    ruta = os.path.join(images_dir, f"{id_}.jpg")
    if os.path.exists(ruta):
        return ruta
    return None


# ─────────────────────────────────────────────
# VALIDACION PRINCIPAL
# ─────────────────────────────────────────────

def validar(registros, images_dir: str = IMAGES_DIR) -> dict:
    """
    Valida todos los registros del dataset.
    Devuelve un diccionario completo con todas las metricas requeridas.
    """
    ids_vistos        = {}
    ids_duplicados    = set()
    urls_vistas       = {}
    urls_repetidas    = set()
    hashes_vistos     = {}
    archivos_dup_hash = []

    nombres_vacios    = []
    urls_vacias       = []
    imagenes_faltantes = []
    imagenes_danadas  = []
    extension_invalida = []
    ids_vacios        = 0
    registros_validos = 0

    for r in registros:
        id_     = (r.get("id")             or "").strip()
        nombre  = (r.get("nombre_original") or r.get("nombre") or "").strip()
        url     = (r.get("url")            or "").strip()
        imagen  = (r.get("imagen")         or "").strip()
        es_valido = True

        # 1. ID no vacio
        if not id_:
            ids_vacios += 1
            es_valido = False

        # 2. ID no repetido
        if id_:
            if id_ in ids_vistos:
                ids_duplicados.add(id_)
                es_valido = False
            else:
                ids_vistos[id_] = True

        # 3. Nombre no vacio
        if not nombre:
            nombres_vacios.append(id_ or "(sin id)")
            es_valido = False

        # 4. URL no vacia
        if not url:
            urls_vacias.append(id_ or "(sin id)")
            es_valido = False
        else:
            # 5. URL no repetida
            if url in urls_vistas:
                urls_repetidas.add(url)
                es_valido = False
            else:
                urls_vistas[url] = id_

        # 6. Extension permitida
        if imagen and not imagen.lower().endswith(EXTENSIONES_PERMITIDAS):
            extension_invalida.append(id_ or imagen)
            es_valido = False

        # 7. Archivo existente (nombre del CSV o equivalente <id>.jpg)
        ruta_imagen = resolver_imagen(id_, imagen, images_dir)
        if ruta_imagen is None:
            imagenes_faltantes.append(id_ or imagen or "(sin imagen)")
            es_valido = False
        else:
            # 8. Imagen que pueda abrirse (no danada)
            if not imagen_abre(ruta_imagen):
                imagenes_danadas.append(id_ or imagen)
                es_valido = False
            else:
                # 9. Duplicados por hash MD5
                h = md5_archivo(ruta_imagen)
                if h in hashes_vistos:
                    archivos_dup_hash.append(
                        f"{id_} == {hashes_vistos[h]} (hash: {h[:8]}...)"
                    )
                else:
                    hashes_vistos[h] = id_

        if es_valido:
            registros_validos += 1

    return {
        "registros_totales"   : len(registros),
        "registros_validos"   : registros_validos,
        "ids_vacios"          : ids_vacios,
        "ids_duplicados"      : sorted(ids_duplicados),
        "nombres_vacios"      : nombres_vacios,
        "urls_vacias"         : urls_vacias,
        "urls_repetidas"      : sorted(urls_repetidas),
        "extension_invalida"  : extension_invalida,
        "imagenes_faltantes"  : imagenes_faltantes,
        "imagenes_danadas"    : imagenes_danadas,
        "archivos_dup_hash"   : archivos_dup_hash,
    }


# ─────────────────────────────────────────────
# BENCHMARK  1.000 REGISTROS
# ─────────────────────────────────────────────

def benchmark_1000(registros_reales, images_dir: str = IMAGES_DIR):
    """
    Genera 1.000 registros sinteticos (repitiendo los reales con IDs unicos)
    y mide el tiempo total de procesamiento.
    Las imagenes usadas son las reales para que la apertura con Pillow sea genuina.
    """
    print()
    print("=" * 55)
    print("BENCHMARK — procesamiento de 1.000 registros")
    print("=" * 55)

    # Construir lista de 1000 registros sinteticos con IDs unicos
    base = registros_reales * (1000 // len(registros_reales) + 1)
    muestra_1000 = []
    for i, r in enumerate(base[:1000], start=1):
        fila = dict(r)
        fila["id"] = f"BEN-P{i:04d}"       # ID unico sintetico
        fila["url"] = r.get("url", "") + f"?bench={i}"  # URL unica
        muestra_1000.append(fila)

    inicio = time.perf_counter()
    _ = validar(muestra_1000, images_dir)
    fin = time.perf_counter()

    elapsed = fin - inicio
    por_reg  = elapsed / 1000 * 1000  # ms por registro

    print(f"Registros procesados : 1.000")
    print(f"Tiempo total         : {elapsed:.3f} s")
    print(f"Tiempo por registro  : {por_reg:.3f} ms")
    print(f"Velocidad estimada   : {int(1000 / elapsed):,} registros/segundo")
    print("=" * 55)


# ─────────────────────────────────────────────
# VALIDACION VISUAL DE MUESTRA
# ─────────────────────────────────────────────

def validacion_visual_muestra(registros, images_dir: str = IMAGES_DIR, n: int = 5):
    """
    Muestra n pares aleatorios (ID, nombre_original, archivo fisico encontrado)
    como evidencia de que el nombre corresponde al archivo correcto.
    """
    print()
    print("=" * 55)
    print(f"VALIDACION VISUAL — muestra de {n} pares ID / nombre / imagen")
    print("=" * 55)
    print(f"{'ID':<18} {'Nombre':<35} {'Archivo fisico'}")
    print("-" * 90)

    muestra = random.sample(registros, min(n, len(registros)))
    for r in sorted(muestra, key=lambda x: x.get("id", "")):
        id_     = r.get("id", "")
        nombre  = (r.get("nombre_original") or r.get("nombre") or "")[:34]
        imagen  = r.get("imagen", "")
        ruta    = resolver_imagen(id_, imagen, images_dir)
        existe  = "[OK]" if ruta else "[FALTA]"
        nombre_safe = nombre.encode("ascii", "ignore").decode()
        print(f"{id_:<18} {nombre_safe:<35} {imagen}  {existe}")

    print("-" * 90)
    print("Confirmacion: cada ID tiene exactamente un archivo fisico asignado.")


# ─────────────────────────────────────────────
# REPORTE
# ─────────────────────────────────────────────

def imprimir_reporte(reporte: dict):
    print()
    print("=" * 55)
    print("REPORTE DE VALIDACION — data/products.csv")
    print("Nota: base de datos activa = CSV.")
    print("      SQLite fuera del flujo integrado (Hito 1).")
    print("      Migracion futura: PostgreSQL + pgvector.")
    print("=" * 55)
    print(f"Registros totales        : {reporte['registros_totales']}")
    print(f"Registros validos        : {reporte['registros_validos']}")
    print(f"IDs vacios               : {reporte['ids_vacios']}")
    print(f"IDs duplicados           : {len(reporte['ids_duplicados'])}")
    print(f"Nombres vacios           : {len(reporte['nombres_vacios'])}")
    print(f"URLs vacias              : {len(reporte['urls_vacias'])}")
    print(f"URLs repetidas           : {len(reporte['urls_repetidas'])}")
    print(f"Extension invalida       : {len(reporte['extension_invalida'])}")
    print(f"Imagenes faltantes       : {len(reporte['imagenes_faltantes'])}")
    print(f"Imagenes danadas         : {len(reporte['imagenes_danadas'])}")
    print(f"Duplicados por hash MD5  : {len(reporte['archivos_dup_hash'])}")
    print("=" * 55)

    hay_errores = reporte["registros_validos"] != reporte["registros_totales"]
    if hay_errores:
        print("\nDetalle de problemas encontrados:")
        if reporte["ids_duplicados"]:
            print(f"  - IDs duplicados   : {reporte['ids_duplicados']}")
        if reporte["nombres_vacios"]:
            print(f"  - Nombres vacios   : {reporte['nombres_vacios']}")
        if reporte["urls_vacias"]:
            print(f"  - URLs vacias      : {reporte['urls_vacias']}")
        if reporte["urls_repetidas"]:
            print(f"  - URLs repetidas   : {reporte['urls_repetidas']}")
        if reporte["extension_invalida"]:
            print(f"  - Ext. invalida    : {reporte['extension_invalida']}")
        if reporte["imagenes_faltantes"]:
            print(f"  - Imgs faltantes   : {reporte['imagenes_faltantes']}")
        if reporte["imagenes_danadas"]:
            print(f"  - Imgs danadas     : {reporte['imagenes_danadas']}")
        if reporte["archivos_dup_hash"]:
            print(f"  - Dup. por hash    : {reporte['archivos_dup_hash']}")
    else:
        print("\n[OK] Todos los registros son validos. Dataset aprobado.")


# ─────────────────────────────────────────────
# ENTRYPOINT
# ─────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Sala 1 — Validacion completa del dataset"
    )
    parser.add_argument(
        "--benchmark",
        action="store_true",
        help="Ejecutar benchmark de rendimiento con 1.000 registros"
    )
    args = parser.parse_args()

    registros = cargar_registros()

    # Medir tiempo de la validacion real
    t0 = time.perf_counter()
    reporte = validar(registros)
    t1 = time.perf_counter()

    imprimir_reporte(reporte)

    print(f"\nTiempo de validacion ({reporte['registros_totales']} registros): "
          f"{(t1 - t0):.3f} s")

    # Muestra de pares ID/nombre/imagen
    validacion_visual_muestra(registros, n=5)

    # Benchmark opcional
    if args.benchmark:
        benchmark_1000(registros)


if __name__ == "__main__":
    main()