import csv
import os
import sqlite3
 
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
RUTA_CSV = os.path.join(BASE_DIR, "data", "products.csv")
RUTA_DB = os.path.join(BASE_DIR, "data", "productos.db")
 
 
def crear_tabla(conn):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS productos (
            id TEXT PRIMARY KEY,
            proveedor TEXT NOT NULL,
            pagina INTEGER,
            imagen TEXT NOT NULL,
            nombre_original TEXT,
            url TEXT
        )
    """)
    conn.commit()
 
 
def insertar_datos(conn):
    with open(RUTA_CSV, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        filas = list(reader)
 
    insertados = 0
    duplicados = 0
 
    for fila in filas:
        try:
            conn.execute(
                """
                INSERT INTO productos (id, proveedor, pagina, imagen, nombre_original, url)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    fila["id"],
                    fila["proveedor"],
                    fila["pagina"],
                    fila["imagen"],
                    fila["nombre_original"],
                    fila["url"],
                ),
            )
            insertados += 1
        except sqlite3.IntegrityError:
            # El id ya existía (duplicado) -> se omite en vez de romper el script
            duplicados += 1
 
    conn.commit()
    print(f"✅ Insertados: {insertados}")
    if duplicados:
        print(f"⚠️  Omitidos por duplicado: {duplicados}")
 
 
def main():
    conn = sqlite3.connect(RUTA_DB)
    crear_tabla(conn)
    insertar_datos(conn)
    conn.close()
    print(f"🎉 Base de datos lista en: {RUTA_DB}")
 
 
if __name__ == "__main__":
    main()