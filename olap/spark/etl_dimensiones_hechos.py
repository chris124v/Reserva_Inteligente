"""
etl_dimensiones_hechos.py
--------------------------
Extrae usuarios, restaurantes, menus, pedidos y reservas desde PostgreSQL,
transforma con Spark DataFrames hacia el esquema estrella de Hive
(dim_tiempo, dim_usuario, dim_restaurante, dim_producto, dim_ubicacion,
fact_reservas, fact_pedidos) y carga el resultado en reserva_dw vía JDBC.

Las dimensiones se sobrescriben con TRUNCATE (preserva el DDL ORC original).
Las fact tables, al estar particionadas por anio/mes, se cargan en dos pasos:
1) Spark escribe el resultado transformado a una tabla de staging sin partición.
2) Una sentencia HiveQL cruda (INSERT OVERWRITE ... PARTITION(anio, mes)) con
   partición dinámica mueve los datos de staging a la tabla final particionada.
Esto es necesario porque el writer JDBC genérico de Spark no sabe emitir
sintaxis de partición dinámica de Hive.

users.rol, orders.estado y orders.tipo_entrega se almacenan en mayúsculas en
Postgres (default de SQLAlchemy Enum); se normalizan a minúsculas aquí para
coincidir con lo que esperan las vistas OLAP de schema_estrella.hql.
reservations.estado ya viene en minúsculas (values_callable explícito en el
modelo), no necesita normalización.

Ejecutar:
    spark-submit \
      --master local[*] \
      --packages org.postgresql:postgresql:42.7.1 \
      /opt/spark-scripts/etl_dimensiones_hechos.py
"""

from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    col, explode, from_json, lit, lower, when, concat_ws, to_timestamp,
    year, month, quarter, weekofyear, dayofmonth, dayofweek, hour,
    date_format, row_number,
)
from pyspark.sql.window import Window
from pyspark.sql.types import ArrayType, StructType, StructField, IntegerType
from pyhive import hive
from decimal import Decimal

PG_URL = "jdbc:postgresql://postgres-service:5432/restaurantes_db"
PG_PROPS = {
    "user": "postgres",
    "password": "MySecurePass123!",
    "driver": "org.postgresql.Driver",
}

# La carga a Hive se hace con pyhive (HiveServer2:10000), no con df.write.jdbc:
# Spark cita identificadores con comillas dobles (estilo ANSI) que Hive rechaza,
# y mode=overwrite recrearia las tablas perdiendo su DDL ORC.
HIVE_HOST = "hiveserver2"
HIVE_PORT = 10000
HIVE_DATABASE = "reserva_dw"

spark = (
    SparkSession.builder
    .appName("ETLDimensionesHechos")
    .config("spark.sql.session.timeZone", "UTC")
    .getOrCreate()
)
spark.sparkContext.setLogLevel("WARN")

# --- extracción -------------------------------------------------------------
users        = spark.read.jdbc(PG_URL, "users",        properties=PG_PROPS)
restaurants  = spark.read.jdbc(PG_URL, "restaurants",  properties=PG_PROPS)
menus        = spark.read.jdbc(PG_URL, "menus",        properties=PG_PROPS)
orders       = spark.read.jdbc(PG_URL, "orders",       properties=PG_PROPS)
reservations = spark.read.jdbc(PG_URL, "reservations", properties=PG_PROPS)


def derivar_tiempo_id(df, col_fecha_hora):
    """Agrega anio/mes/dia/hora_int/tiempo_id (surrogate YYYYMMDDHH) a partir de una columna timestamp."""
    return (
        df
        .withColumn("anio", year(col_fecha_hora))
        .withColumn("mes",  month(col_fecha_hora))
        .withColumn("dia",  dayofmonth(col_fecha_hora))
        .withColumn("hora_int", hour(col_fecha_hora))
        .withColumn(
            "tiempo_id",
            (col("anio") * 1000000 + col("mes") * 10000 + col("dia") * 100 + col("hora_int")).cast("int"),
        )
    )


# --- dim_tiempo: fechas distintas de orders + reservations ------------------
fechas_orders = orders.select(col("fecha_creacion").alias("fecha_hora"))

fechas_reservas = reservations.select(
    to_timestamp(concat_ws(" ", col("fecha").cast("string"), date_format(col("hora"), "HH:mm:ss"))).alias("fecha_hora")
)

todas_fechas = fechas_orders.unionByName(fechas_reservas).distinct()

dim_tiempo_df = (
    derivar_tiempo_id(todas_fechas, col("fecha_hora"))
    .withColumn("trimestre", quarter(col("fecha_hora")))
    .withColumn("semana_anio", weekofyear(col("fecha_hora")))
    .withColumn("mes_nombre", date_format(col("fecha_hora"), "MMMM"))
    # Spark: dayofweek domingo=1..sabado=7 -> remapeo a lunes=1..domingo=7
    .withColumn("dia_semana", ((dayofweek(col("fecha_hora")) + 5) % 7) + 1)
    .withColumn("dia_semana_nombre", date_format(col("fecha_hora"), "EEEE"))
    .withColumn("es_fin_semana", when(col("dia_semana") >= 6, 1).otherwise(0).cast("int"))
    .withColumn("es_dia_laboral", when(col("dia_semana") <= 5, 1).otherwise(0).cast("int"))
    .withColumn("fecha", date_format(col("fecha_hora"), "yyyy-MM-dd"))
    .withColumn("hora", col("hora_int"))
    .select("tiempo_id", "fecha", "anio", "trimestre", "mes", "mes_nombre", "semana_anio",
            "dia", "dia_semana", "dia_semana_nombre", "hora", "es_fin_semana", "es_dia_laboral")
    .dropDuplicates(["tiempo_id"])
)

# --- dim_usuario --------------------------------------------------------------
dim_usuario_df = users.select(
    col("id").alias("usuario_id"),
    col("nombre"),
    col("email"),
    lower(col("rol").cast("string")).alias("rol"),
    when(col("activo") == True, 1).otherwise(0).cast("int").alias("activo"),  # noqa: E712
    date_format(col("fecha_creacion"), "yyyy-MM-dd").alias("fecha_registro"),
)

# --- dim_restaurante (admin_nombre desnormalizado) ---------------------------
admins = users.select(col("id").alias("admin_id_join"), col("nombre").alias("admin_nombre"))

dim_restaurante_df = (
    restaurants
    .join(admins, restaurants.admin_id == admins.admin_id_join, "left")
    .select(
        restaurants["id"].alias("restaurante_id"),
        restaurants["nombre"],
        restaurants["descripcion"],
        restaurants["direccion"],
        restaurants["telefono"],
        date_format(restaurants["hora_apertura"], "HH:mm").alias("hora_apertura"),
        date_format(restaurants["hora_cierre"], "HH:mm").alias("hora_cierre"),
        restaurants["total_mesas"],
        restaurants["admin_id"],
        col("admin_nombre"),
    )
)

# --- dim_producto (restaurante_nombre desnormalizado) ------------------------
restaurantes_nombre = restaurants.select(
    col("id").alias("restaurante_id_join"), col("nombre").alias("restaurante_nombre")
)

dim_producto_df = (
    menus
    .join(restaurantes_nombre, menus.restaurante_id == restaurantes_nombre.restaurante_id_join, "left")
    .select(
        menus["id"].alias("producto_id"),
        menus["nombre"],
        menus["descripcion"],
        menus["categoria"],
        menus["precio"].alias("precio_base"),
        menus["tiempo_preparacion"].alias("tiempo_preparacion_min"),
        when(menus["disponible"] == True, 1).otherwise(0).cast("int").alias("disponible"),  # noqa: E712
        menus["restaurante_id"],
        col("restaurante_nombre"),
    )
)

# --- dim_ubicacion (lat/lon null, no existen en el modelo operacional) ------
dim_ubicacion_df = restaurants.select(
    col("id").alias("ubicacion_id"),
    col("id").alias("restaurante_id"),
    col("nombre").alias("restaurante_nombre"),
    col("direccion"),
    lit(None).cast("double").alias("latitud"),
    lit(None).cast("double").alias("longitud"),
)

# --- fact_reservas -------------------------------------------------------------
reservas_enriquecidas = derivar_tiempo_id(
    reservations.withColumn(
        "fecha_hora", to_timestamp(concat_ws(" ", col("fecha").cast("string"), date_format(col("hora"), "HH:mm:ss")))
    ),
    col("fecha_hora"),
)

fact_reservas_df = reservas_enriquecidas.select(
    col("id").alias("reserva_id"),
    col("tiempo_id"),
    col("usuario_id"),
    col("restaurante_id"),
    col("restaurante_id").alias("ubicacion_id"),
    date_format(col("hora"), "HH:mm").alias("hora_reserva"),
    col("hora_int").alias("hora_reserva_int"),
    col("cantidad_personas"),
    col("numero_mesa"),
    col("estado"),
    when(col("estado") == "cancelada", 1).otherwise(0).cast("int").alias("es_cancelada"),
    col("anio"),
    col("mes"),
)

# --- fact_pedidos: explota items JSON, une con menus, deriva es_primer_item -
items_schema = ArrayType(StructType([
    StructField("menu_id",  IntegerType(), nullable=False),
    StructField("cantidad", IntegerType(), nullable=False),
]))

pedidos_explotados = derivar_tiempo_id(
    orders
    .withColumn("item", explode(from_json(col("items"), items_schema)))
    .withColumn("menu_id_item",  col("item.menu_id"))
    .withColumn("cantidad_item", col("item.cantidad")),
    col("fecha_creacion"),
)

menus_precio = menus.select(
    col("id").alias("menu_id_join"),
    col("precio"),
)

detalle = pedidos_explotados.join(
    menus_precio, pedidos_explotados.menu_id_item == menus_precio.menu_id_join,
)

# es_primer_item: bandera para no inflar sumas de total_pedido al agrupar por pedido
ventana_pedido = Window.partitionBy(detalle["id"]).orderBy(detalle["menu_id_item"])
detalle_con_flag = detalle.withColumn("rn", row_number().over(ventana_pedido))

fact_pedidos_df = detalle_con_flag.select(
    col("id").alias("pedido_id"),
    col("tiempo_id"),
    col("usuario_id"),
    col("restaurante_id"),
    col("menu_id_item").alias("producto_id"),
    col("restaurante_id").alias("ubicacion_id"),
    lower(col("tipo_entrega").cast("string")).alias("tipo_entrega"),
    col("cantidad_item").alias("cantidad"),
    col("precio").alias("precio_unitario"),
    (col("cantidad_item") * col("precio")).alias("subtotal_item"),
    col("subtotal").alias("subtotal_pedido"),
    col("impuesto"),
    col("total").alias("total_pedido"),
    lower(col("estado").cast("string")).alias("estado"),
    when(lower(col("estado").cast("string")) == "cancelado", 1).otherwise(0).cast("int").alias("es_cancelado"),
    when(lower(col("estado").cast("string")) == "entregado", 1).otherwise(0).cast("int").alias("es_entregado"),
    when(col("rn") == 1, 1).otherwise(0).cast("int").alias("es_primer_item"),
    col("anio"),
    col("mes"),
)

# --- carga a Hive ----------------------------------------------------------
# Se recolectan las filas al driver (el volumen es pequeño: seed de decenas de
# filas) y se insertan con HiveQL nativo vía pyhive. Las dimensiones se
# sobrescriben con TRUNCATE (preserva el DDL ORC). Las fact tables, al estar
# particionadas, pasan por una tabla de staging sin partición y luego un
# INSERT OVERWRITE con partición dinámica.


def _sql_literal(v):
    """Representa un valor Python como literal SQL de Hive."""
    if v is None:
        return "NULL"
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float, Decimal)):
        return str(v)
    s = str(v).replace("\\", "\\\\").replace("'", "\\'")
    return f"'{s}'"


def _insert_values(cursor, tabla, columnas, rows):
    """INSERT INTO TABLE <tabla> VALUES (...),(...) con todas las filas en una sentencia."""
    if not rows:
        print(f"[etl_dimensiones_hechos] {tabla}: sin filas, se omite insert")
        return
    tuplas = [
        "(" + ", ".join(_sql_literal(r[c]) for c in columnas) + ")"
        for r in rows
    ]
    cursor.execute(f"INSERT INTO TABLE {tabla} VALUES " + ", ".join(tuplas))


DIM_TIEMPO_COLS = ["tiempo_id", "fecha", "anio", "trimestre", "mes", "mes_nombre",
                   "semana_anio", "dia", "dia_semana", "dia_semana_nombre", "hora",
                   "es_fin_semana", "es_dia_laboral"]
DIM_USUARIO_COLS = ["usuario_id", "nombre", "email", "rol", "activo", "fecha_registro"]
DIM_RESTAURANTE_COLS = ["restaurante_id", "nombre", "descripcion", "direccion", "telefono",
                        "hora_apertura", "hora_cierre", "total_mesas", "admin_id", "admin_nombre"]
DIM_PRODUCTO_COLS = ["producto_id", "nombre", "descripcion", "categoria", "precio_base",
                     "tiempo_preparacion_min", "disponible", "restaurante_id", "restaurante_nombre"]
DIM_UBICACION_COLS = ["ubicacion_id", "restaurante_id", "restaurante_nombre", "direccion",
                      "latitud", "longitud"]

COLUMNAS_FACT_RESERVAS = [
    "reserva_id", "tiempo_id", "usuario_id", "restaurante_id", "ubicacion_id",
    "hora_reserva", "hora_reserva_int", "cantidad_personas", "numero_mesa",
    "estado", "es_cancelada", "anio", "mes",
]
COLUMNAS_FACT_PEDIDOS = [
    "pedido_id", "tiempo_id", "usuario_id", "restaurante_id", "producto_id", "ubicacion_id",
    "tipo_entrega", "cantidad", "precio_unitario", "subtotal_item", "subtotal_pedido",
    "impuesto", "total_pedido", "estado", "es_cancelado", "es_entregado", "es_primer_item",
    "anio", "mes",
]

DDL_STAGING_FACT_RESERVAS = (
    "CREATE TABLE staging_fact_reservas ("
    "reserva_id INT, tiempo_id INT, usuario_id INT, restaurante_id INT, ubicacion_id INT, "
    "hora_reserva STRING, hora_reserva_int INT, cantidad_personas INT, numero_mesa INT, "
    "estado STRING, es_cancelada TINYINT, anio INT, mes INT)"
)
DDL_STAGING_FACT_PEDIDOS = (
    "CREATE TABLE staging_fact_pedidos ("
    "pedido_id INT, tiempo_id INT, usuario_id INT, restaurante_id INT, producto_id INT, "
    "ubicacion_id INT, tipo_entrega STRING, cantidad INT, precio_unitario DOUBLE, "
    "subtotal_item DOUBLE, subtotal_pedido DOUBLE, impuesto DOUBLE, total_pedido DOUBLE, "
    "estado STRING, es_cancelado TINYINT, es_entregado TINYINT, es_primer_item TINYINT, "
    "anio INT, mes INT)"
)


def _cargar_fact_particionada(cursor, staging, ddl_staging, tabla_final, df, columnas):
    """staging sin partición -> INSERT OVERWRITE con partición dinámica (anio, mes al final)."""
    rows = df.select(*columnas).collect()
    cursor.execute(f"DROP TABLE IF EXISTS {staging}")
    cursor.execute(ddl_staging)
    _insert_values(cursor, staging, columnas, rows)
    cursor.execute(
        f"INSERT OVERWRITE TABLE {tabla_final} PARTITION(anio, mes) "
        f"SELECT {', '.join(columnas)} FROM {staging}"
    )
    cursor.execute(f"DROP TABLE {staging}")
    print(f"[etl_dimensiones_hechos] {tabla_final}: {len(rows)} filas cargadas")


# auth="NONE" usa transporte SASL PLAIN (con username), que es lo que espera
# HiveServer2 con hive.server2.authentication=NONE (su default). "NOSASL" cerraria
# la conexion con "TSocket read 0 bytes" por mismatch de transporte.
conn = hive.Connection(
    host=HIVE_HOST, port=HIVE_PORT, database=HIVE_DATABASE, auth="NONE", username="hive",
)
cursor = conn.cursor()
try:
    # USE explicito: el parametro database= de pyhive no siempre fija el contexto
    # de la sesion, lo que hace que las tablas se busquen en 'default' y fallen.
    cursor.execute(f"USE {HIVE_DATABASE}")
    cursor.execute("SET hive.exec.dynamic.partition.mode=nonstrict")

    for tabla, df, cols in [
        ("dim_tiempo", dim_tiempo_df, DIM_TIEMPO_COLS),
        ("dim_usuario", dim_usuario_df, DIM_USUARIO_COLS),
        ("dim_restaurante", dim_restaurante_df, DIM_RESTAURANTE_COLS),
        ("dim_producto", dim_producto_df, DIM_PRODUCTO_COLS),
        ("dim_ubicacion", dim_ubicacion_df, DIM_UBICACION_COLS),
    ]:
        filas = df.select(*cols).collect()
        cursor.execute(f"TRUNCATE TABLE {tabla}")
        _insert_values(cursor, tabla, cols, filas)
        print(f"[etl_dimensiones_hechos] {tabla}: {len(filas)} filas cargadas")

    _cargar_fact_particionada(
        cursor, "staging_fact_reservas", DDL_STAGING_FACT_RESERVAS,
        "fact_reservas", fact_reservas_df, COLUMNAS_FACT_RESERVAS,
    )
    _cargar_fact_particionada(
        cursor, "staging_fact_pedidos", DDL_STAGING_FACT_PEDIDOS,
        "fact_pedidos", fact_pedidos_df, COLUMNAS_FACT_PEDIDOS,
    )
finally:
    cursor.close()
    conn.close()

spark.stop()
