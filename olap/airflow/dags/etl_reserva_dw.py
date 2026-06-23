"""
etl_reserva_dw.py
------------------
DAG diario que orquesta: transformación con Spark + carga al Data Warehouse
(Hive) -> verificación de cambios en el catálogo de menús -> reindexado
condicional de Elasticsearch.

cargar_dw_hive          corre etl_dimensiones_hechos.py con spark-submit local[*]
verificar_cambio_catalogo  compara MAX(fecha_actualizacion) de menus contra la
                           corrida anterior (Airflow Variable); si no cambió,
                           hace short-circuit y se saltan las tareas siguientes
reindexar_elasticsearch    POST a search-service/search/reindex
"""

from datetime import datetime, timedelta

from airflow import DAG
from airflow.models import Variable
from airflow.operators.bash import BashOperator
from airflow.operators.python import ShortCircuitOperator, PythonOperator
from airflow.providers.postgres.hooks.postgres import PostgresHook
from airflow.providers.http.hooks.http import HttpHook

VARIABLE_ULTIMA_ACTUALIZACION = "ultima_fecha_actualizacion_menus"
# Solo el driver de Postgres: la carga a Hive usa pyhive (Python puro), no JDBC,
# asi que no se necesita hive-jdbc (que ademas arrastraba todo Hadoop 2.7.2 y
# hacia la resolucion de dependencias Maven muy lenta).
SPARK_PACKAGES = "org.postgresql:postgresql:42.7.1"


def _verificar_cambio_catalogo(**context):
    hook = PostgresHook(postgres_conn_id="postgres_operacional")
    fila = hook.get_first("SELECT MAX(fecha_actualizacion) FROM menus")
    max_actual = fila[0] if fila else None
    if max_actual is None:
        return False

    valor_guardado = Variable.get(VARIABLE_ULTIMA_ACTUALIZACION, default_var=None)
    max_anterior = datetime.fromisoformat(valor_guardado) if valor_guardado else None

    Variable.set(VARIABLE_ULTIMA_ACTUALIZACION, max_actual.isoformat())

    cambio = max_anterior is None or max_actual > max_anterior
    context["ti"].xcom_push(key="max_fecha_actualizacion", value=max_actual.isoformat())
    return cambio


def _reindexar_elasticsearch(**context):
    hook = HttpHook(method="POST", http_conn_id="search_service")
    respuesta = hook.run(endpoint="/search/reindex")
    respuesta.raise_for_status()
    return respuesta.json()


default_args = {
    "owner": "reserva_inteligente",
    "retries": 3,
    "retry_delay": timedelta(minutes=5),
}

with DAG(
    dag_id="etl_reserva_dw",
    description="Extrae de PostgreSQL, transforma con Spark, carga el DW en Hive y reindexa ES si cambia el catalogo",
    default_args=default_args,
    schedule="@daily",
    start_date=datetime(2026, 1, 1),
    catchup=False,
    max_active_runs=1,
    tags=["olap", "spark", "hive", "elasticsearch"],
) as dag:

    cargar_dw_hive = BashOperator(
        task_id="cargar_dw_hive",
        bash_command=(
            "PYSPARK_PYTHON=python3 PYSPARK_DRIVER_PYTHON=python3 "
            f"spark-submit --master local[*] --packages {SPARK_PACKAGES} "
            "/opt/spark-scripts/etl_dimensiones_hechos.py"
        ),
    )

    # Materializa las 3 vistas OLAP de Hive en tablas analytics_* de PostgreSQL
    # para que Metabase (Req 3) las consuma de forma nativa, sin driver de Hive.
    materializar_vistas_metabase = BashOperator(
        task_id="materializar_vistas_metabase",
        bash_command="python3 /opt/spark-scripts/materializar_vistas_metabase.py",
    )

    verificar_cambio_catalogo = ShortCircuitOperator(
        task_id="verificar_cambio_catalogo",
        python_callable=_verificar_cambio_catalogo,
    )

    reindexar_elasticsearch = PythonOperator(
        task_id="reindexar_elasticsearch",
        python_callable=_reindexar_elasticsearch,
    )

    cargar_dw_hive >> materializar_vistas_metabase >> verificar_cambio_catalogo >> reindexar_elasticsearch
