# Esquema Estrella — Data Warehouse de Reserva Inteligente

Documentación completa del esquema estrella definido en `olap/hive/schema_estrella.hql`.

---

## ¿Qué es un esquema estrella?

Un esquema estrella organiza un Data Warehouse en dos tipos de tablas:

- **Tablas de hechos** (*fact tables*): registran eventos del negocio con sus métricas numéricas (cantidades, montos, conteos). Son las tablas grandes, con millones de filas en producción.
- **Tablas de dimensiones** (*dimension tables*): guardan el contexto descriptivo de esos eventos — quién, cuándo, dónde, qué. Son tablas pequeñas que rodean a las de hechos.

El nombre viene del diagrama ER: la tabla de hechos queda en el centro y las dimensiones son los rayos de la estrella.

---

## Modelo operacional (fuente de datos)

El ETL (Apache Spark) extrae datos de estas tablas en PostgreSQL/MongoDB y los carga en Hive:

| Tabla operacional | Campos relevantes |
|---|---|
| `users` | id, email, nombre, rol, activo, fecha_creacion |
| `restaurants` | id, nombre, descripcion, direccion, telefono, admin_id, hora_apertura, hora_cierre, total_mesas |
| `menus` | id, nombre, descripcion, precio, disponible, restaurante_id, tiempo_preparacion, categoria |
| `reservations` | id, usuario_id, restaurante_id, **fecha** (DATE), **hora** (TIME), cantidad_personas, estado, numero_mesa |
| `orders` | id, usuario_id, restaurante_id, **items** (JSON), subtotal, impuesto, total, estado, tipo_entrega, fecha_creacion |

Notas importantes:
- `orders` **no tiene campo `fecha` propio**. La fecha del pedido viene de `fecha_creacion` (heredado de BaseModel).
- `orders.items` es un JSON array `[{"menu_id": 1, "cantidad": 2}, ...]` — solo guarda menu_id y cantidad, **sin precio**.
- El precio por ítem se obtiene en el ETL haciendo JOIN con `menus.precio`.

---

## Dimensiones

### dim_tiempo

Descompone cada fecha+hora en atributos analíticos. Tiene granularidad horaria: una fila por combinación única de fecha y hora del día.

**Clave surrogate:** `tiempo_id = YYYYMMDDHH`
Por ejemplo: `2026051019` = 10 de mayo 2026 a las 19:00.

**Fuente ETL:**
- Para reservas: `reservations.fecha` + `HOUR(reservations.hora)`
- Para pedidos: `DATE(orders.fecha_creacion)` + `HOUR(orders.fecha_creacion)`

**Atributos:** año, trimestre, mes, mes_nombre, semana del año, día, día de semana, hora, es_fin_semana, es_dia_laboral.

Permite agrupar por cualquier granularidad temporal sin hacer cálculos en cada query.

---

### dim_usuario

Perfil de los usuarios del sistema. Incluye tanto clientes como admins.

**Fuente ETL:** `SELECT id, email, nombre, rol, activo, fecha_creacion FROM users`

`password_hash` no se copia al DW por seguridad.

**Seed actual:** 5 usuarios — Admin Postgres (id=1), Cliente Postgres (id=2), Cristiano Ronaldo/admin (id=3), Lionel Messi/cliente (id=4), Andres Iniesta/cliente (id=5).

Las vistas de análisis filtran por `rol = 'cliente'` para métricas de consumo.

---

### dim_restaurante

Datos del restaurante con el nombre del admin desnormalizado para evitar JOINs en las queries OLAP.

**Fuente ETL:** `JOIN restaurants r ON r.admin_id = users.id`

**Seed actual:** 7 restaurantes — sapore tratoria, villa italia, los congos, nacion sushi, hamburguesas 360, La Cancha Grill, El Golazo Bistro.

El campo `admin_nombre` viene de `users.nombre` del admin propietario, guardado directamente en la dimensión.

---

### dim_producto

Platos del menú con su categoría y el nombre del restaurante desnormalizado.

**Fuente ETL:** `JOIN menus m ON m.restaurante_id = restaurants.id`

**Seed actual:** 28 platos (4 por restaurante).

**Categorías presentes en el seed:** principal, pasta, pizza, carne, pescado, sushi, entrada, acompanamiento, ensalada.

La categoría es la columna más usada para análisis de ingresos — permite responder "¿qué tipo de plato vende más?".

**Sobre precio_base:** se toma de `menus.precio` al momento del ETL. Si el precio cambia después, el histírico en el DW reflejará el precio nuevo (limitación del modelo operacional — los pedidos no guardan el precio al momento de la compra).

---

### dim_ubicacion

Dirección del restaurante para análisis geográfico.

**Fuente ETL:** `SELECT id, id, nombre, direccion, NULL, NULL FROM restaurants`

`latitud` y `longitud` son **NULL** porque el modelo operacional no almacena coordenadas GPS. Se populan manualmente o via geocodificación si se integra el módulo de ruteo. Las vistas funcionan correctamente sin ellas — solo afecta la capacidad de renderizar mapas en Metabase/Superset.

`ubicacion_id` tiene el mismo valor que `restaurante_id`. Es una dimensión separada de `dim_restaurante` para mantener la separación entre análisis de gestión (dim_restaurante) y análisis geográfico (dim_ubicacion).

---

## Tablas de hechos

### fact_reservas

Una fila por reserva. Fuente: tabla `reservations`.

**Con el seed actual:** 9 filas (3 reservas por cada cliente: usuarios 2, 4 y 5).

**Métricas:**
- `cantidad_personas`: número de personas en la reserva (entre 2 y 4 en el seed)
- `es_cancelada`: 1 si el estado es "cancelada". En el seed todas son "reservada", por lo que este campo es 0 en todas las filas.

**Nota sobre numero_mesa:** es NULL en todas las reservas del seed porque el modelo lo asigna solo después de confirmar la reserva.

**Cálculo de tiempo_id:**
```
YEAR(fecha)*1000000 + MONTH(fecha)*10000 + DAY(fecha)*100 + HOUR(hora)
```

---

### fact_pedidos

**Una fila por ítem dentro del pedido** — no una fila por pedido.

El ETL explota el campo JSON `orders.items` y hace JOIN con `menus` para obtener el precio. Un pedido con 3 productos distintos genera 3 filas en esta tabla.

**Con el seed actual:** 12 pedidos → 15 filas (pedidos 1, 3 y 10 tienen 2 ítems; el resto tienen 1).

**Métricas por ítem:**
- `cantidad`: unidades del producto
- `precio_unitario`: de `menus.precio` via JOIN en el ETL
- `subtotal_item`: `cantidad × precio_unitario`

**Métricas por pedido (se repiten en cada fila del mismo pedido):**
- `subtotal_pedido`: `orders.subtotal`
- `impuesto`: `orders.impuesto`
- `total_pedido`: `orders.total`

### El campo es_primer_item

Como `total_pedido` se repite en cada fila del mismo pedido, hacer `SUM(total_pedido)` en una vista lo contaría múltiples veces para pedidos con más de un ítem. Por ejemplo, un pedido con total=$30 y 2 ítems contribuiría $60 al SUM.

El ETL asigna `es_primer_item = 1` solo al ítem con el menor `producto_id` de cada pedido, y `0` al resto. Las vistas que necesitan sumar totales de pedido usan:

```sql
SUM(CASE WHEN es_primer_item = 1 THEN total_pedido ELSE 0 END)
```

Esto garantiza que el total de cada pedido se cuente exactamente una vez.

---

## Vistas OLAP

### v_ingresos_por_mes_categoria

**Pregunta:** ¿cuánto vendió cada categoría de plato en cada mes?

**Tablas:** fact_pedidos + dim_tiempo + dim_producto

**Columnas resultado:**

| columna | descripción |
|---|---|
| anio, mes, mes_nombre | período |
| categoria | categoría del plato |
| total_pedidos | pedidos distintos que incluyeron esta categoría |
| total_unidades_vendidas | suma de cantidades de ítems |
| ingresos_categoria | suma de subtotal_item (cantidad × precio) |
| precio_promedio_item | precio promedio del ítem en ese período |

`ingresos_categoria` usa `SUM(subtotal_item)` — es seguro porque `subtotal_item` es una métrica per-ítem, no se repite.

---

### v_actividad_por_zona

**Pregunta:** ¿qué restaurantes concentran más clientes e ingresos?

**Tablas:** fact_pedidos + dim_ubicacion

**Columnas resultado:**

| columna | descripción |
|---|---|
| ubicacion_id, restaurante_nombre, direccion | identificación del lugar |
| latitud, longitud | null hasta geocodificar |
| clientes_unicos | usuarios distintos que pidieron ahí |
| total_pedidos | pedidos distintos |
| ticket_promedio | total promedio por pedido |
| ingresos_totales | suma de subtotal_item |

`ticket_promedio` usa `es_primer_item` para no inflar el numerador.

---

### v_pedidos_completados_cancelados

**Pregunta:** ¿cuál es la tasa de cancelación por restaurante y mes?

**Tablas:** fact_pedidos + dim_tiempo + dim_restaurante

**Columnas resultado:**

| columna | descripción |
|---|---|
| anio, mes, mes_nombre | período |
| restaurante | nombre del restaurante |
| total_pedidos | todos los pedidos del período |
| pedidos_completados | pedidos con es_entregado=1 |
| pedidos_cancelados | pedidos con es_cancelado=1 |
| tasa_cancelacion_pct | % de pedidos cancelados |

Todos los conteos usan `COUNT(DISTINCT pedido_id)` — no hay inflación por ítems.

---

### v_horarios_pico

**Pregunta:** ¿a qué hora del día y qué día de la semana hay más actividad?

**Tablas:** UNION ALL de fact_reservas y fact_pedidos, ambos con dim_tiempo

**Columnas resultado:**

| columna | descripción |
|---|---|
| hora | hora del día 0-23 |
| dia_semana_nombre | lunes, martes, etc. |
| es_fin_semana | 1 si sábado o domingo |
| total_reservas | reservas en esa hora/día |
| personas_reservadas | suma de cantidad_personas |
| total_pedidos | pedidos en esa hora/día |
| ingresos_hora | ingresos de pedidos en esa hora |

**Decisión de diseño — UNION ALL vs LEFT JOIN doble:**

Un `LEFT JOIN` desde `dim_tiempo` hacia `fact_reservas` y `fact_pedidos` al mismo tiempo crea un producto cartesiano. Si a las 19:00 hay 3 reservas y 5 pedidos, el JOIN genera 3×5=15 filas y `SUM(cantidad_personas)` se multiplica por 5 — resultado incorrecto.

La solución es `UNION ALL`: cada fuente aporta sus filas de forma independiente antes de agregar. El bloque de pedidos usa `es_primer_item` para contar `total_pedido` una sola vez por pedido.

---

### v_frecuencia_uso_usuario

**Pregunta:** ¿qué tan frecuente es cada cliente? ¿quién gasta más?

**Tablas:** dim_usuario + subquery de fact_pedidos + subquery de fact_reservas

**Columnas resultado:**

| columna | descripción |
|---|---|
| usuario_id, nombre, email | identificación |
| total_pedidos | pedidos realizados |
| total_reservas | reservas realizadas |
| total_interacciones | suma de ambos |
| gasto_total | monto total gastado en pedidos |
| gasto_promedio_pedido | promedio por pedido |
| primera_interaccion | fecha del primer pedido |
| ultima_interaccion | fecha del último pedido |

**Decisión de diseño — subqueries independientes:**

El patrón `dim_usuario LEFT JOIN fact_pedidos LEFT JOIN fact_reservas` genera un producto cartesiano: si el usuario tiene M pedidos y N reservas, el JOIN da M×N filas. Con 4 pedidos y 3 reservas, `SUM(total_pedido)` se inflaría 3 veces.

La solución es agregar pedidos y reservas por separado en subqueries, luego unir los resultados agregados a `dim_usuario`. Cada subquery produce una sola fila por usuario antes del JOIN.

---

### v_tendencias_consumo

**Pregunta:** ¿qué categorías de platos están creciendo o bajando con el tiempo?

**Tablas:** fact_pedidos + dim_tiempo + dim_producto

**Columnas resultado:** anio, mes, mes_nombre, categoria, restaurante_nombre, unidades_vendidas, ingresos, num_pedidos, clientes_unicos.

Input principal para el análisis de tendencias de consumo en Spark. Con datos de múltiples meses, Spark puede calcular la variación porcentual mes a mes por categoría.

---

### v_crecimiento_mensual

**Pregunta:** ¿cuánto se facturó en total por mes?

**Tablas:** fact_pedidos + dim_tiempo

**Columnas resultado:** anio, mes, mes_nombre, ingresos_mes, pedidos_mes, clientes_activos_mes, unidades_vendidas_mes.

Input para el análisis de crecimiento Month-over-Month (MoM) en Spark. Spark lee esta vista y aplica la función de ventana `LAG()` para calcular el porcentaje de crecimiento respecto al mes anterior.

`ingresos_mes` usa `es_primer_item` para contar `total_pedido` exactamente una vez por pedido.

---

## Cómo ejecutar

```bash
# copiar el script al pod de HiveServer2
kubectl cp olap/hive/schema_estrella.hql \
  reservainteligente/<pod-hiveserver2>:/tmp/schema_estrella.hql

# ejecutar con beeline
kubectl exec -n reservainteligente -it <pod-hiveserver2> -- \
  /opt/hive/bin/beeline -u jdbc:hive2://localhost:10000 \
  -f /tmp/schema_estrella.hql
```

---

## Notas de almacenamiento

- **Formato ORC:** columnar y comprimido con SNAPPY. Hive solo lee las columnas que necesita cada query.
- **Particionado por `(anio, mes)`:** una query de "ingresos de enero 2025" solo lee los archivos de esa partición, no todo el histórico.
- **Base de datos:** `reserva_dw`, separada de la BD operacional.
