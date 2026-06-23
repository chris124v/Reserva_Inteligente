"""
tendencias_consumo.py

Lee pedidos y menús desde PostgreSQL, explota el JSON de ítems, calcula
ingresos y unidades vendidas por mes y categoría de producto, y escribe
los resultados en la tabla analytics_tendencias_consumo de PostgreSQL.

Ejecutar:
    spark-submit \
      --master spark://spark-master:7077 \
      --packages org.postgresql:postgresql:42.7.1 \
      /opt/spark-scripts/tendencias_consumo.py
"""

from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    col, explode, from_json, year, month,
    round as spark_round,
)
from pyspark.sql.types import (
    ArrayType, StructType, StructField, IntegerType,
)

PG_URL = "jdbc:postgresql://postgres-service:5432/restaurantes_db"
PG_PROPS = {
    "user": "postgres",
    "password": "MySecurePass123!",
    "driver": "org.postgresql.Driver",
}

spark = (
    SparkSession.builder
    .appName("TendenciasConsumo")
    .config("spark.sql.session.timeZone", "UTC")
    .getOrCreate()
)
spark.sparkContext.setLogLevel("WARN")

# --- extracción -----------------------------------------------------------
orders = spark.read.jdbc(PG_URL, "orders", properties=PG_PROPS)
menus  = spark.read.jdbc(PG_URL, "menus",  properties=PG_PROPS)

# --- transformación con DataFrames ----------------------------------------
items_schema = ArrayType(StructType([
    StructField("menu_id",  IntegerType(), nullable=False),
    StructField("cantidad", IntegerType(), nullable=False),
]))

# explota el array JSON de ítems: un pedido con 2 ítems genera 2 filas
pedidos_explotados = (
    orders
    .filter(col("estado") != "CANCELADO")
    .withColumn("item", explode(from_json(col("items"), items_schema)))
    .withColumn("anio", year(col("fecha_creacion")))
    .withColumn("mes",  month(col("fecha_creacion")))
    .withColumn("menu_id_item",  col("item.menu_id"))
    .withColumn("cantidad_item", col("item.cantidad"))
)

# join con menús para obtener precio y categoría
detalle = pedidos_explotados.join(
    menus.select(
        col("id").alias("menu_id"),
        col("categoria"),
        col("precio"),
        col("restaurante_id"),
    ),
    pedidos_explotados.menu_id_item == col("menu_id"),
).withColumn("ingreso_item", col("cantidad_item") * col("precio"))

# --- análisis con SparkSQL ------------------------------------------------
detalle.createOrReplaceTempView("pedidos_detalle")

resultado = spark.sql("""
    SELECT
        anio,
        mes,
        categoria,
        COUNT(DISTINCT pedido_id)      AS num_pedidos,
        SUM(cantidad_item)             AS unidades_vendidas,
        ROUND(SUM(ingreso_item), 2)    AS ingresos,
        ROUND(AVG(precio), 2)          AS precio_promedio
    FROM (
        SELECT
            anio, mes, categoria, precio, cantidad_item, ingreso_item,
            id AS pedido_id
        FROM pedidos_detalle
    ) t
    GROUP BY anio, mes, categoria
    ORDER BY anio, mes, ingresos DESC
""")

resultado.show(truncate=False)
print(f"[tendencias_consumo] filas generadas: {resultado.count()}")

# --- carga ----------------------------------------------------------------
resultado.write.jdbc(
    PG_URL,
    "analytics_tendencias_consumo",
    mode="overwrite",
    properties=PG_PROPS,
)
print("[tendencias_consumo] escritura completada en analytics_tendencias_consumo")

spark.stop()
