"""
horarios_pico.py

Combina reservas y pedidos para detectar las horas y días de la semana
con más actividad. Usa UNION ALL en SparkSQL para agregar ambas fuentes
de forma independiente y evitar producto cartesiano.

Ejecutar:
    spark-submit \
      --master spark://spark-master:7077 \
      --packages org.postgresql:postgresql:42.7.1 \
      /opt/spark-scripts/horarios_pico.py
"""

from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    col, hour, dayofweek, date_format,
    lit, when,
)

PG_URL = "jdbc:postgresql://postgres-service:5432/restaurantes_db"
PG_PROPS = {
    "user": "postgres",
    "password": "MySecurePass123!",
    "driver": "org.postgresql.Driver",
}

spark = (
    SparkSession.builder
    .appName("HorariosPico")
    .config("spark.sql.session.timeZone", "UTC")
    .getOrCreate()
)
spark.sparkContext.setLogLevel("WARN")

# --- extracción -----------------------------------------------------------
orders       = spark.read.jdbc(PG_URL, "orders",       properties=PG_PROPS)
reservations = spark.read.jdbc(PG_URL, "reservations", properties=PG_PROPS)

# --- transformación con DataFrames ----------------------------------------
# pedidos: la hora viene de fecha_creacion (timestamp)
pedidos_hora = (
    orders
    .filter(col("estado") != "CANCELADO")
    .withColumn("hora",            hour(col("fecha_creacion")))
    .withColumn("dia_semana_num",  dayofweek(col("fecha_creacion")))
    .withColumn("dia_semana_nombre", date_format(col("fecha_creacion"), "EEEE"))
    .withColumn("es_fin_semana",
        when(dayofweek(col("fecha_creacion")).isin(1, 7), lit(1)).otherwise(lit(0)))
    .withColumn("tipo",              lit("pedido"))
    .withColumn("cantidad_personas", lit(0))
    .select("hora", "dia_semana_num", "dia_semana_nombre", "es_fin_semana",
            "tipo", "cantidad_personas", col("total").alias("monto"))
)

# reservas: la hora viene del campo TIME hora; se castea a hora del día
reservas_hora = (
    reservations
    .withColumn("hora",            hour(col("hora").cast("timestamp")))
    .withColumn("dia_semana_num",  dayofweek(col("fecha").cast("timestamp")))
    .withColumn("dia_semana_nombre", date_format(col("fecha").cast("timestamp"), "EEEE"))
    .withColumn("es_fin_semana",
        when(dayofweek(col("fecha").cast("timestamp")).isin(1, 7), lit(1)).otherwise(lit(0)))
    .withColumn("tipo",  lit("reserva"))
    .withColumn("monto", lit(0.0))
    .select("hora", "dia_semana_num", "dia_semana_nombre", "es_fin_semana",
            "tipo", "cantidad_personas", "monto")
)

# --- análisis con SparkSQL: UNION ALL de ambas fuentes -------------------
actividad = pedidos_hora.unionByName(reservas_hora)
actividad.createOrReplaceTempView("actividad_combinada")

resultado = spark.sql("""
    SELECT
        hora,
        dia_semana_num,
        dia_semana_nombre,
        es_fin_semana,
        COUNT(CASE WHEN tipo = 'reserva' THEN 1 END)       AS total_reservas,
        SUM(CASE WHEN tipo = 'reserva'
                 THEN cantidad_personas ELSE 0 END)        AS personas_reservadas,
        COUNT(CASE WHEN tipo = 'pedido'  THEN 1 END)       AS total_pedidos,
        ROUND(SUM(CASE WHEN tipo = 'pedido'
                       THEN monto ELSE 0 END), 2)          AS ingresos_pedidos
    FROM actividad_combinada
    GROUP BY hora, dia_semana_num, dia_semana_nombre, es_fin_semana
    ORDER BY total_pedidos + total_reservas DESC
""")

resultado.show(truncate=False)
print(f"[horarios_pico] filas generadas: {resultado.count()}")

# --- carga ----------------------------------------------------------------
resultado.write.jdbc(
    PG_URL,
    "analytics_horarios_pico",
    mode="overwrite",
    properties=PG_PROPS,
)
print("[horarios_pico] escritura completada en analytics_horarios_pico")

spark.stop()
