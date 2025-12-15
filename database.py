import os
import psycopg2
import logging

logger = logging.getLogger(__name__)

def get_connection():
    try:
        return psycopg2.connect(
            host=os.getenv("DB_HOST", "localhost"),
            port=os.getenv("DB_PORT", "5432"),
            user=os.getenv("DB_USER", "postgres"),
            password=os.getenv("DB_PASSWORD", ""),
            dbname=os.getenv("DB_NAME", "toxicidad_db"),
        )
    except Exception as e:
        logger.error(f"Error fatal conectando a PostgreSQL: {e}")
        raise e


def init_db():
    try:
        conn = get_connection()
        cur = conn.cursor()

        cur.execute("""
            CREATE TABLE IF NOT EXISTS predicciones (
                id SERIAL PRIMARY KEY,
                texto TEXT NOT NULL,
                toxicidad SMALLINT NOT NULL,
                probabilidad REAL NOT NULL,
                fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        logger.error(f"Error creando tablas: {e}")
        raise e


def guardar_prediccion(texto: str, toxicidad: int, probabilidad: float):
    try:
        conn = get_connection()
        cur = conn.cursor()

        cur.execute(
            """
            INSERT INTO predicciones (texto, toxicidad, probabilidad)
            VALUES (%s, %s, %s)
            """,
            (texto, toxicidad, probabilidad)
        )

        conn.commit()
        cur.close()
        conn.close()
        logger.info(f"Guardado en BD -> Tox: {toxicidad}, Prob: {probabilidad:.2f}")
    except Exception as e:
        logger.error(f"Error al guardar predicción en BD (No crítico): {e}")