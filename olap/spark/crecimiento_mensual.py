"""
crecimiento_mensual.py

Calcula el total de ingresos, pedidos y clientes activos por mes y aplica
la función de ventana LAG() para obtener el porcentaje de crecimiento
mes a mes (MoM). Demuestra Window Functions en SparkSQL.

Ejecutar:
    spark-submit \
      --master spark://spark-master:7077 \
      --packages org.postgresql:postgresql:42.7.1 \
      /opt/spark-scripts/crecimiento_mensual.py
"""

from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    col, year, month, round as spark_round,
)

PG_URL = "jdbc:postgresql://postgres-service:5432/restaurantes_db"
PG_PROPS = {
    "user": "postgres",
    "password": "MySecurePass123!",
    "driver": "org.postgresql.Driver",
}

spark = (
    SparkSession.builder
    .appName("CrecimientoMensual")
    .config("spark.sql.session.timeZone", "UTC")
    .getOrCreate()
)
spark.sparkContext.setLogLevel("WARN")

# --- extracción -----------------------------------------------------------
orders = spark.read.jdbc(PG_URL, "orders", properties=PG_PROPS)

# --- transformación con DataFrames ----------------------------------------
pedidos_mes = (
    orders
    .filter(col("estado") != "CANCELADO")
    .withColumn("anio", year(col("fecha_creacion")))
    .withColumn("mes",  month(col("fecha_creacion")))
)

pedidos_mes.createOrReplaceTempView("pedidos_por_mes")

# --- análisis con SparkSQL: agregación mensual + LAG para crecimiento MoM -
totales = spark.sql("""
    SELECT
        anio,
        mes,
        COUNT(id)                    AS pedidos_mes,
        COUNT(DISTINCT usuario_id)   AS clientes_activos,
        ROUND(SUM(total), 2)         AS ingresos_mes,
        ROUND(AVG(total), 2)         AS ticket_promedio
    FROM pedidos_por_mes
    GROUP BY anio, mes
    ORDER BY anio, mes
""")
totales.createOrReplaceTempView("totales_mensuales")

# LAG() calcula el valor del mes anterior dentro de la misma ventana ordenada
resultado = spark.sql("""
    SELECT
        anio,
        mes,
        pedidos_mes,
        clientes_activos,
        ingresos_mes,
        ticket_promedio,
        LAG(ingresos_mes) OVER (ORDER BY anio, mes) AS ingresos_mes_anterior,
        LAG(pedidos_mes)  OVER (ORDER BY anio, mes) AS pedidos_mes_anterior,
        ROUND(
            (ingresos_mes - LAG(ingresos_mes) OVER (ORDER BY anio, mes)) * 100.0 /
            NULLIF(LAG(ingresos_mes) OVER (ORDER BY anio, mes), 0)
        , 2) AS crecimiento_ingresos_pct,
        ROUND(
            (pedidos_mes - LAG(pedidos_mes) OVER (ORDER BY anio, mes)) * 100.0 /
            NULLIF(LAG(pedidos_mes) OVER (ORDER BY anio, mes), 0)
        , 2) AS crecimiento_pedidos_pct
    FROM totales_mensuales
    ORDER BY anio, mes
""")

resultado.show(truncate=False)
print(f"[crecimiento_mensual] filas generadas: {resultado.count()}")

# --- carga ----------------------------------------------------------------
resultado.write.jdbc(
    PG_URL,
    "analytics_crecimiento_mensual",
    mode="overwrite",
    properties=PG_PROPS,
)
print("[crecimiento_mensual] escritura completada en analytics_crecimiento_mensual")

spark.stop()
