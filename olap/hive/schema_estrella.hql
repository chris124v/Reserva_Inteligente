-- esquema estrella del data warehouse 

CREATE DATABASE IF NOT EXISTS reserva_dw
COMMENT 'data warehouse de reserva inteligente';

USE reserva_dw;

-- ===========================================================================
-- dimensiones
-- ===========================================================================

-- descompone fecha+hora en atributos analíticos para cualquier granularidad
CREATE TABLE IF NOT EXISTS dim_tiempo (
    tiempo_id         INT     COMMENT 'surrogate key YYYYMMDDHH',
    fecha             STRING  COMMENT 'fecha en formato YYYY-MM-DD',
    anio              INT     COMMENT 'año',
    trimestre         INT     COMMENT 'trimestre 1-4',
    mes               INT     COMMENT 'número de mes 1-12',
    mes_nombre        STRING  COMMENT 'nombre del mes',
    semana_anio       INT     COMMENT 'semana del año 1-52',
    dia               INT     COMMENT 'día del mes 1-31',
    dia_semana        INT     COMMENT 'día de la semana: 1=lunes, 7=domingo',
    dia_semana_nombre STRING  COMMENT 'nombre del día',
    hora              INT     COMMENT 'hora del día 0-23',
    es_fin_semana     TINYINT COMMENT '1 si sábado o domingo',
    es_dia_laboral    TINYINT COMMENT '1 si lunes a viernes'
)
COMMENT 'dimensión temporal'
STORED AS ORC
TBLPROPERTIES ('orc.compress'='SNAPPY');

-- perfil de usuarios del sistema (clientes y admins)
CREATE TABLE IF NOT EXISTS dim_usuario (
    usuario_id     INT     COMMENT 'users.id',
    nombre         STRING  COMMENT 'users.nombre',
    email          STRING  COMMENT 'users.email',
    rol            STRING  COMMENT 'cliente o admin',
    activo         TINYINT COMMENT '1 si está activo',
    fecha_registro STRING  COMMENT 'users.fecha_creacion'
)
COMMENT 'dimensión de usuarios'
STORED AS ORC
TBLPROPERTIES ('orc.compress'='SNAPPY');

-- datos del restaurante con nombre del admin desnormalizado
CREATE TABLE IF NOT EXISTS dim_restaurante (
    restaurante_id INT     COMMENT 'restaurants.id',
    nombre         STRING  COMMENT 'restaurants.nombre',
    descripcion    STRING  COMMENT 'restaurants.descripcion',
    direccion      STRING  COMMENT 'restaurants.direccion',
    telefono       STRING  COMMENT 'restaurants.telefono',
    hora_apertura  STRING  COMMENT 'hora de apertura HH:MM',
    hora_cierre    STRING  COMMENT 'hora de cierre HH:MM',
    total_mesas    INT     COMMENT 'restaurants.total_mesas',
    admin_id       INT     COMMENT 'restaurants.admin_id',
    admin_nombre   STRING  COMMENT 'nombre del admin, desnormalizado de users'
)
COMMENT 'dimensión de restaurantes'
STORED AS ORC
TBLPROPERTIES ('orc.compress'='SNAPPY');

-- platos del menú con categoría y nombre de restaurante desnormalizado
CREATE TABLE IF NOT EXISTS dim_producto (
    producto_id            INT     COMMENT 'menus.id',
    nombre                 STRING  COMMENT 'menus.nombre',
    descripcion            STRING  COMMENT 'menus.descripcion',
    categoria              STRING  COMMENT 'menus.categoria: principal, pasta, pizza, carne, pescado, sushi, entrada, acompanamiento, ensalada',
    precio_base            DOUBLE  COMMENT 'menus.precio al momento del etl',
    tiempo_preparacion_min INT     COMMENT 'menus.tiempo_preparacion en minutos',
    disponible             TINYINT COMMENT '1 si está disponible',
    restaurante_id         INT     COMMENT 'menus.restaurante_id',
    restaurante_nombre     STRING  COMMENT 'nombre del restaurante, desnormalizado de restaurants'
)
COMMENT 'dimensión de productos del menú'
STORED AS ORC
TBLPROPERTIES ('orc.compress'='SNAPPY');

-- dirección del restaurante; lat/long null hasta geocodificar
CREATE TABLE IF NOT EXISTS dim_ubicacion (
    ubicacion_id       INT     COMMENT 'igual a restaurante_id',
    restaurante_id     INT     COMMENT 'restaurants.id',
    restaurante_nombre STRING  COMMENT 'restaurants.nombre',
    direccion          STRING  COMMENT 'restaurants.direccion',
    latitud            DOUBLE  COMMENT 'latitud gps — null, no existe en el modelo operacional',
    longitud           DOUBLE  COMMENT 'longitud gps — null, no existe en el modelo operacional'
)
COMMENT 'dimensión de ubicaciones geográficas'
STORED AS ORC
TBLPROPERTIES ('orc.compress'='SNAPPY');

-- ===========================================================================
-- tablas de hechos
-- ===========================================================================

-- una fila por reserva; fuente: tabla reservations
CREATE TABLE IF NOT EXISTS fact_reservas (
    reserva_id        INT     COMMENT 'reservations.id',
    tiempo_id         INT     COMMENT 'fk → dim_tiempo, de reservations.fecha + hora',
    usuario_id        INT     COMMENT 'fk → dim_usuario',
    restaurante_id    INT     COMMENT 'fk → dim_restaurante',
    ubicacion_id      INT     COMMENT 'fk → dim_ubicacion, igual a restaurante_id',
    hora_reserva      STRING  COMMENT 'reservations.hora en formato HH:MM',
    hora_reserva_int  INT     COMMENT 'hora como entero 0-23',
    cantidad_personas INT     COMMENT 'métrica: reservations.cantidad_personas',
    numero_mesa       INT     COMMENT 'reservations.numero_mesa, null si no confirmada',
    estado            STRING  COMMENT 'reservada o cancelada',
    es_cancelada      TINYINT COMMENT 'métrica: 1 si cancelada, 0 si no'
)
COMMENT 'hechos de reservas — una fila por reserva'
PARTITIONED BY (anio INT, mes INT)
STORED AS ORC
TBLPROPERTIES ('orc.compress'='SNAPPY');

-- una fila por ítem de pedido; orders.items se explota del json
-- es_primer_item evita inflar sumas de total_pedido cuando un pedido tiene varios ítems
CREATE TABLE IF NOT EXISTS fact_pedidos (
    pedido_id       INT     COMMENT 'orders.id',
    tiempo_id       INT     COMMENT 'fk → dim_tiempo, de DATE(orders.fecha_creacion)',
    usuario_id      INT     COMMENT 'fk → dim_usuario',
    restaurante_id  INT     COMMENT 'fk → dim_restaurante',
    producto_id     INT     COMMENT 'fk → dim_producto, de items[].menu_id',
    ubicacion_id    INT     COMMENT 'fk → dim_ubicacion, igual a restaurante_id',
    tipo_entrega    STRING  COMMENT 'domicilio, recogida o en_restaurante',
    cantidad        INT     COMMENT 'métrica: items[].cantidad',
    precio_unitario DOUBLE  COMMENT 'métrica: menus.precio obtenido via join en el etl',
    subtotal_item   DOUBLE  COMMENT 'métrica: cantidad × precio_unitario',
    subtotal_pedido DOUBLE  COMMENT 'métrica: orders.subtotal, se repite por ítem',
    impuesto        DOUBLE  COMMENT 'métrica: orders.impuesto, se repite por ítem',
    total_pedido    DOUBLE  COMMENT 'métrica: orders.total, se repite por ítem',
    estado          STRING  COMMENT 'pendiente, confirmado, en_preparacion, listo, entregado, cancelado',
    es_cancelado    TINYINT COMMENT 'métrica: 1 si cancelado',
    es_entregado    TINYINT COMMENT 'métrica: 1 si entregado',
    es_primer_item  TINYINT COMMENT 'bandera del etl: 1 para el primer ítem del pedido (menor producto_id)'
)
COMMENT 'hechos de pedidos — una fila por ítem de pedido, explotado del json items'
PARTITIONED BY (anio INT, mes INT)
STORED AS ORC
TBLPROPERTIES ('orc.compress'='SNAPPY');

-- ===========================================================================
-- vistas olap
-- ===========================================================================

-- ingresos por mes y categoría de producto → dashboard 1
CREATE OR REPLACE VIEW v_ingresos_por_mes_categoria AS
SELECT
    t.anio,
    t.mes,
    t.mes_nombre,
    p.categoria,
    COUNT(DISTINCT f.pedido_id)      AS total_pedidos,
    SUM(f.cantidad)                  AS total_unidades_vendidas,
    ROUND(SUM(f.subtotal_item), 2)   AS ingresos_categoria,
    ROUND(AVG(f.precio_unitario), 2) AS precio_promedio_item
FROM fact_pedidos f
JOIN dim_tiempo   t ON f.tiempo_id   = t.tiempo_id
JOIN dim_producto p ON f.producto_id = p.producto_id
WHERE f.es_cancelado = 0
GROUP BY t.anio, t.mes, t.mes_nombre, p.categoria;

-- actividad por restaurante con ticket promedio e ingresos → dashboard 2
CREATE OR REPLACE VIEW v_actividad_por_zona AS
SELECT
    u.ubicacion_id,
    u.restaurante_nombre,
    u.direccion,
    u.latitud,
    u.longitud,
    COUNT(DISTINCT fp.usuario_id)                                                   AS clientes_unicos,
    COUNT(DISTINCT fp.pedido_id)                                                    AS total_pedidos,
    ROUND(SUM(CASE WHEN fp.es_primer_item = 1 THEN fp.total_pedido ELSE 0 END) /
          COUNT(DISTINCT fp.pedido_id), 2)                                          AS ticket_promedio,
    ROUND(SUM(fp.subtotal_item), 2)                                                 AS ingresos_totales
FROM fact_pedidos fp
JOIN dim_ubicacion u ON fp.ubicacion_id = u.ubicacion_id
WHERE fp.es_cancelado = 0
GROUP BY u.ubicacion_id, u.restaurante_nombre, u.direccion, u.latitud, u.longitud;

-- pedidos completados vs cancelados por restaurante y mes → dashboard 3
CREATE OR REPLACE VIEW v_pedidos_completados_cancelados AS
SELECT
    t.anio,
    t.mes,
    t.mes_nombre,
    r.nombre                                                          AS restaurante,
    COUNT(DISTINCT f.pedido_id)                                       AS total_pedidos,
    COUNT(DISTINCT CASE WHEN f.es_entregado = 1 THEN f.pedido_id END) AS pedidos_completados,
    COUNT(DISTINCT CASE WHEN f.es_cancelado  = 1 THEN f.pedido_id END) AS pedidos_cancelados,
    ROUND(
        COUNT(DISTINCT CASE WHEN f.es_cancelado = 1 THEN f.pedido_id END) * 100.0 /
        COUNT(DISTINCT f.pedido_id)
    , 2)                                                              AS tasa_cancelacion_pct
FROM fact_pedidos f
JOIN dim_tiempo      t ON f.tiempo_id      = t.tiempo_id
JOIN dim_restaurante r ON f.restaurante_id = r.restaurante_id
GROUP BY t.anio, t.mes, t.mes_nombre, r.nombre;

-- actividad por hora y día de semana; combina reservas y pedidos con union all
CREATE OR REPLACE VIEW v_horarios_pico AS
SELECT
    hora,
    dia_semana_nombre,
    es_fin_semana,
    COUNT(DISTINCT reserva_id)           AS total_reservas,
    COALESCE(SUM(cantidad_personas), 0)  AS personas_reservadas,
    COUNT(DISTINCT pedido_id)            AS total_pedidos,
    ROUND(COALESCE(SUM(ingresos), 0), 2) AS ingresos_hora
FROM (
    SELECT
        t.hora, t.dia_semana_nombre, t.es_fin_semana,
        fr.reserva_id, fr.cantidad_personas,
        CAST(NULL AS INT)    AS pedido_id,
        CAST(NULL AS DOUBLE) AS ingresos
    FROM fact_reservas fr
    JOIN dim_tiempo t ON fr.tiempo_id = t.tiempo_id
    UNION ALL
    SELECT
        t.hora, t.dia_semana_nombre, t.es_fin_semana,
        CAST(NULL AS INT) AS reserva_id, CAST(NULL AS INT) AS cantidad_personas,
        fp.pedido_id,
        CASE WHEN fp.es_primer_item = 1 THEN fp.total_pedido ELSE 0 END AS ingresos
    FROM fact_pedidos fp
    JOIN dim_tiempo t ON fp.tiempo_id = t.tiempo_id
    WHERE fp.es_cancelado = 0
) combined
GROUP BY hora, dia_semana_nombre, es_fin_semana;

-- gasto y frecuencia por cliente; subqueries independientes evitan producto cartesiano
CREATE OR REPLACE VIEW v_frecuencia_uso_usuario AS
SELECT
    u.usuario_id,
    u.nombre,
    u.email,
    COALESCE(pd.total_pedidos, 0)      AS total_pedidos,
    COALESCE(rv.total_reservas, 0)     AS total_reservas,
    COALESCE(pd.total_pedidos, 0) +
    COALESCE(rv.total_reservas, 0)     AS total_interacciones,
    COALESCE(pd.gasto_total, 0.0)      AS gasto_total,
    pd.gasto_promedio_pedido           AS gasto_promedio_pedido,
    pd.primera_interaccion             AS primera_interaccion,
    pd.ultima_interaccion              AS ultima_interaccion
FROM dim_usuario u
LEFT JOIN (
    SELECT
        fp.usuario_id,
        COUNT(DISTINCT fp.pedido_id)                                                AS total_pedidos,
        ROUND(SUM(CASE WHEN fp.es_primer_item = 1 THEN fp.total_pedido ELSE 0 END), 2) AS gasto_total,
        ROUND(SUM(CASE WHEN fp.es_primer_item = 1 THEN fp.total_pedido ELSE 0 END) /
              COUNT(DISTINCT fp.pedido_id), 2)                                      AS gasto_promedio_pedido,
        MIN(t.fecha)                                                                AS primera_interaccion,
        MAX(t.fecha)                                                                AS ultima_interaccion
    FROM fact_pedidos fp
    JOIN dim_tiempo t ON fp.tiempo_id = t.tiempo_id
    GROUP BY fp.usuario_id
) pd ON u.usuario_id = pd.usuario_id
LEFT JOIN (
    SELECT usuario_id, COUNT(DISTINCT reserva_id) AS total_reservas
    FROM fact_reservas
    GROUP BY usuario_id
) rv ON u.usuario_id = rv.usuario_id
WHERE u.rol = 'cliente';

-- unidades e ingresos por mes, categoría y restaurante → input para spark tendencias
CREATE OR REPLACE VIEW v_tendencias_consumo AS
SELECT
    t.anio,
    t.mes,
    t.mes_nombre,
    p.categoria,
    p.restaurante_nombre,
    SUM(f.cantidad)                AS unidades_vendidas,
    ROUND(SUM(f.subtotal_item), 2) AS ingresos,
    COUNT(DISTINCT f.pedido_id)    AS num_pedidos,
    COUNT(DISTINCT f.usuario_id)   AS clientes_unicos
FROM fact_pedidos f
JOIN dim_tiempo   t ON f.tiempo_id   = t.tiempo_id
JOIN dim_producto p ON f.producto_id = p.producto_id
WHERE f.es_cancelado = 0
GROUP BY t.anio, t.mes, t.mes_nombre, p.categoria, p.restaurante_nombre;

-- totales mensuales agregados → spark aplica lag() para calcular crecimiento mom
CREATE OR REPLACE VIEW v_crecimiento_mensual AS
SELECT
    t.anio,
    t.mes,
    t.mes_nombre,
    ROUND(SUM(CASE WHEN f.es_primer_item = 1 THEN f.total_pedido ELSE 0 END), 2) AS ingresos_mes,
    COUNT(DISTINCT f.pedido_id)                                                   AS pedidos_mes,
    COUNT(DISTINCT f.usuario_id)                                                  AS clientes_activos_mes,
    SUM(f.cantidad)                                                               AS unidades_vendidas_mes
FROM fact_pedidos f
JOIN dim_tiempo t ON f.tiempo_id = t.tiempo_id
WHERE f.es_cancelado = 0
GROUP BY t.anio, t.mes, t.mes_nombre;
