"""
materializar_vistas_metabase.py
--------------------------------
Lee las 3 vistas OLAP de Hive que alimentan los dashboards de Metabase y
materializa su resultado en tablas analytics_* de PostgreSQL. Asi Metabase las
consume de forma nativa (PostgreSQL es fuente nativa de Metabase) sin necesidad
de un driver JDBC de Hive.

No usa Spark: pyhive lee de HiveServer2 y psycopg2 escribe a PostgreSQL. El
volumen es pequeño (resultados agregados de las vistas), asi que cabe en memoria.

Forma parte del DAG de Airflow (tarea materializar_vistas_metabase), que corre
despues de poblar el DW. Tambien se puede ejecutar suelto:
    python3 /opt/spark-scripts/materializar_vistas_metabase.py
"""

from pyhive import hive
import psycopg2

HIVE_HOST = "hiveserver2"
HIVE_PORT = 10000
HIVE_DATABASE = "reserva_dw"

PG_DSN = dict(
    host="postgres-service", port=5432, dbname="restaurantes_db",
    user="postgres", password="MySecurePass123!",
)

# vista Hive -> tabla destino en PostgreSQL (una por dashboard de Metabase)
VISTAS = {
    "v_ingresos_por_mes_categoria":     "analytics_ingresos_mes_categoria",
    "v_actividad_por_zona":             "analytics_actividad_zona",
    "v_pedidos_completados_cancelados": "analytics_pedidos_estado",
}


def _pg_type(hive_type):
    """Mapea el type_code de pyhive (ej. 'INT_TYPE', 'DOUBLE_TYPE') a un tipo de PostgreSQL."""
    t = (hive_type or "").upper()
    if any(x in t for x in ("INT", "BIGINT", "SMALLINT", "TINYINT")):
        return "BIGINT"
    if any(x in t for x in ("DOUBLE", "FLOAT", "DECIMAL", "NUMERIC")):
        return "DOUBLE PRECISION"
    return "TEXT"


def materializar():
    hive_conn = hive.Connection(
        host=HIVE_HOST, port=HIVE_PORT, database=HIVE_DATABASE, auth="NONE", username="hive",
    )
    pg_conn = psycopg2.connect(**PG_DSN)
    pg_conn.autocommit = True
    try:
        hcur = hive_conn.cursor()
        hcur.execute(f"USE {HIVE_DATABASE}")
        pcur = pg_conn.cursor()

        for vista, tabla in VISTAS.items():
            hcur.execute(f"SELECT * FROM {vista}")
            rows = hcur.fetchall()

            # pyhive antepone "<vista>." al nombre de cada columna; se recorta
            columnas = [
                (desc[0].split(".")[-1], _pg_type(desc[1]))
                for desc in hcur.description
            ]
            col_defs = ", ".join(f'"{nombre}" {tipo}' for nombre, tipo in columnas)
            col_names = ", ".join(f'"{nombre}"' for nombre, _ in columnas)
            placeholders = ", ".join(["%s"] * len(columnas))

            pcur.execute(f"DROP TABLE IF EXISTS {tabla}")
            pcur.execute(f"CREATE TABLE {tabla} ({col_defs})")
            if rows:
                pcur.executemany(
                    f"INSERT INTO {tabla} ({col_names}) VALUES ({placeholders})", rows
                )
            print(f"[materializar_vistas_metabase] {tabla}: {len(rows)} filas desde {vista}")

        hcur.close()
        pcur.close()
    finally:
        hive_conn.close()
        pg_conn.close()


if __name__ == "__main__":
    materializar()
