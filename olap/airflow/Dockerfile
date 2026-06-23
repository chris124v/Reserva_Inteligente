# Imagen de Airflow con PySpark, conector de Hive y los DAGs/scripts ya incluidos.
# Evita depender de kubectl cp/exec en runtime para que el DAG corra de forma reproducible.
FROM apache/airflow:2.10.5-python3.11

# PySpark necesita un JRE para levantar la JVM que corre Spark en local[*]
USER root
RUN apt-get update \
    && apt-get install -y --no-install-recommends default-jdk \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*
ENV JAVA_HOME=/usr/lib/jvm/default-java

USER airflow

COPY olap/airflow/requirements.txt /requirements.txt
RUN pip install --no-cache-dir -r /requirements.txt

COPY olap/airflow/dags/ ${AIRFLOW_HOME}/dags/
COPY olap/spark/ /opt/spark-scripts/
