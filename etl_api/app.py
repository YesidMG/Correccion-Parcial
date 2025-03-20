from flask import Flask, jsonify
from neo4j import GraphDatabase
import psycopg2
import os
import pandas as pd

app = Flask(__name__)

# 🔹 Conexión a Neo4j
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://neo4j_parcial1:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password")
driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

# 🔹 Conexión a PostgreSQL
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "postgres_parcial1")
POSTGRES_DB = os.getenv("POSTGRES_DB", "etl_db")
POSTGRES_USER = os.getenv("POSTGRES_USER", "admin")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "admin")

try:
    conn = psycopg2.connect(
        host=POSTGRES_HOST,
        database=POSTGRES_DB,
        user=POSTGRES_USER,
        password=POSTGRES_PASSWORD
    )
    print("✅ Conexión exitosa a PostgreSQL")
except Exception as e:
    print(f"❌ Error al conectar: {e}")

# 🔹 Función para crear la tabla si no existe
def create_table():
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS etl_data (
            id SERIAL PRIMARY KEY,
            nombre TEXT,
            popularidad INT,
            velocidad INT,
            paradigma TEXT,
            anio_creacion INT,
            popularidad_categoria TEXT,
            velocidad_categoria TEXT,
            eficiencia FLOAT
        );
    """)
    conn.commit()
    cursor.close()

# 🔹 Función para convertir a camelCase
def to_camel_case(text):
    words = text.split(" ")
    return words[0].lower() + "".join(word.capitalize() for word in words[1:])

@app.route('/api/extract', methods=['GET'])
def extract():
    with driver.session() as session:
        result = session.run("MATCH (l:Lenguaje) RETURN l.id, l.nombre, l.popularidad, l.velocidad, l.paradigma, l.anio_creacion")
        data = [dict(record) for record in result]
        return jsonify(data)

@app.route('/api/transform', methods=['GET'])
def transform():
    create_table()  # 🔹 Asegura que la tabla existe antes de insertar

    with driver.session() as session:
        result = session.run("MATCH (l:Lenguaje) RETURN l.id, l.nombre, l.popularidad, l.velocidad, l.paradigma, l.anio_creacion")
        data = [dict(record) for record in result]

    if not data:
        return jsonify({"error": "No se encontraron datos en Neo4j"}), 500

    # Convertir a DataFrame
    df = pd.DataFrame(data)

    # Aplicar transformaciones
    df["nombre"] = df["l.nombre"].apply(to_camel_case)
    df["popularidad"] = df["l.popularidad"].astype(int)
    df["velocidad"] = df["l.velocidad"].astype(int)
    df["popularidad_categoria"] = df["popularidad"].apply(lambda x: "Poco Usado" if x < 30 else ("Moderado" if x <= 70 else "Muy Popular"))
    df["velocidad_categoria"] = df["velocidad"].apply(lambda x: "Lento" if x < 40 else ("Rápido" if x <= 70 else "Muy Rápido"))
    df["eficiencia"] = (df["popularidad"] + df["velocidad"]) / 2

    # Insertar datos transformados en PostgreSQL
    cursor = conn.cursor()

    # Limpiar datos previos
    cursor.execute("DELETE FROM etl_data;")

    for _, row in df.iterrows():
        cursor.execute("""
            INSERT INTO etl_data (nombre, popularidad, velocidad, paradigma, anio_creacion, popularidad_categoria, velocidad_categoria, eficiencia)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (row["nombre"], row["popularidad"], row["velocidad"], row["l.paradigma"], row["l.anio_creacion"], row["popularidad_categoria"], row["velocidad_categoria"], row["eficiencia"]))

    conn.commit()
    cursor.close()

    return jsonify({"message": "✅ Transformación y carga completadas"})

@app.route('/api/load', methods=['GET'])
def load():
    df = pd.read_sql("SELECT * FROM etl_data", conn)
    df.to_csv("/data/recap.csv", index=False)
    return "✅ Archivo CSV generado en /data/recap.csv"

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000)
