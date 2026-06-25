# Guion del video demostrativo — Reserva Inteligente Proyecto II

Duracion total: **12:00 minutos exactos**. Cada seccion tiene su tiempo asignado
y el guion textual de lo que se dice, mas los comandos a ejecutar en pantalla.

---

## Preparacion ANTES de grabar (no sale en el video)

Hacer todo esto con tiempo, para no perder minutos de grabacion esperando que
algo cargue:

1. Cluster completo arriba: `deploy-all.ps1` + `deploy-olap.ps1` corridos sin errores.
2. Tener el DAG `etl_reserva_dw` **ya disparado y en success** desde antes (para
   no esperar los ~15 min que tarda en vivo). Verificar:
   ```powershell
   kubectl exec -n reservainteligente deploy/airflow-scheduler -- airflow dags list-runs -d etl_reserva_dw --output table
   ```
3. Dejar corriendo en terminales aparte (para no perder tiempo abriendolas en cámara):
   ```powershell
   kubectl port-forward svc/hiveserver2 10000:10000 -n reservainteligente
   kubectl port-forward svc/postgres-service 5432:5432 -n reservainteligente
   kubectl port-forward svc/metabase 3000:3000 -n reservainteligente
   kubectl port-forward svc/airflow-webserver 8080:8080 -n reservainteligente
   kubectl port-forward svc/neo4j-service 7474:7474 7687:7687 -n reservainteligente
   kubectl port-forward svc/api-service 8000:80 -n reservainteligente
   ```
4. Pestañas del navegador ya abiertas y logueadas:
   - Metabase (`localhost:3000`) con los 3 dashboards ya armados
   - Airflow UI (`localhost:8080`) en la vista Graph del DAG `etl_reserva_dw`
   - Neo4J Browser (`localhost:7474`) ya logueado
   - El diagrama de arquitectura (imagen) abierto en una pestaña o visor de imagenes
5. Tener `Neo4j/queries.cypher` abierto en el editor para copiar/pegar rapido.
6. Tener una terminal en la raiz del repo con el venv activado, para correr
   `validate_all.py` sin perder tiempo activando el entorno en camara.

---

## 00:00 – 01:30 (1:30) — Introduccion y Arquitectura (Espi)

**Mostrar en pantalla:** el diagrama de arquitectura completo (imagen del documento).

**Guion:**

> "Hola, somos Christopher Vargas y Santiago Espinoza, y este es el Proyecto 2
> de Bases de Datos II: Reserva Inteligente — Analisis y Procesamiento OLAP.
>
> Antes de entrar a cada parte del enunciado, quiero mostrar la arquitectura
> completa del sistema. Tenemos una capa operacional en PostgreSQL que sirve
> los datos de usuarios, restaurantes, menus, pedidos y reservas. Sobre esa
> capa corre un pipeline batch diario orquestado por **Apache Airflow**, que
> dispara **Apache Spark** dos veces, con dos propositos distintos: primero
> para construir el **Data Warehouse** en **Apache Hive sobre HDFS**, con un
> esquema estrella de Kimball, y luego para calcular 3 analisis de negocio
> obligatorios. Esto lo vamos a detallar en un momento.
>
> Esos resultados se materializan de vuelta en PostgreSQL para que
> **Metabase** los consuma de forma nativa y arme los dashboards. En paralelo,
> tenemos **Neo4J**, una base de datos de grafos, que modela las relaciones
> entre usuarios, productos y pedidos para hacer analisis de co-compras,
> usuarios influyentes y rutas de entrega optimas. Todo esto corre desplegado
> en **Kubernetes**, en el namespace `reservainteligente`.
>
> Ahora vamos a recorrer cada uno de los 6 requerimientos del proyecto,
> mostrando el codigo y ejecutando cada parte en vivo."

---

## 01:30 – 02:45 (1:15) — Req 1: Arquitectura OLAP y Almacen de Datos (Chris)

**Mostrar en pantalla:** `olap/hive/schema_estrella.hql` (scroll rapido) y la terminal.

**Guion:**

> "El primer requerimiento pide un esquema estrella en un Data Warehouse open
> source. Implementamos esto con Apache Hive sobre HDFS, siguiendo el modelo
> de Kimball: 5 tablas de dimension — tiempo, usuario, restaurante, producto
> y ubicacion — que ya vienen desnormalizadas, es decir, sin necesidad de
> hacer JOINs para leer atributos descriptivos como el nombre de un
> restaurante o la categoria de un producto. Y 2 tablas de hechos,
> `fact_pedidos` y `fact_reservas`, que solo guardan las metricas numericas
> — totales, cantidades, estados — con referencias hacia esas dimensiones, y
> estan particionadas por año y mes para que las consultas analiticas solo
> lean el pedazo de datos que necesitan, en vez de escanear todo el
> historico. Sobre esas tablas construimos 7 vistas OLAP para los analisis
> agregados."

**Comando (terminal con port-forward de HiveServer2 ya activo):**

```powershell
kubectl exec -n reservainteligente deploy/hiveserver2 -- /opt/hive/bin/hive -e "USE reserva_dw; SHOW TABLES;"
```

> "Aqui vemos las 14 tablas y vistas del warehouse: 5 dimensiones, 2 hechos y
> 7 vistas OLAP, exactamente lo que pide el requerimiento."

---

## 02:45 – 04:00 (1:15) — Req 2: Procesamiento con Apache Spark (Chris)

**Mostrar en pantalla:** `olap/spark/crecimiento_mensual.py` (la parte del `LAG()`).

**Guion:**

> "El segundo requerimiento pide procesar los datos con Spark DataFrames y
> SparkSQL. Como dije, Spark se usa dos veces con dos propositos distintos.
> Primero, para construir el esquema estrella que acabamos de ver: lee de
> PostgreSQL, desnormaliza y le da forma a los datos para que encajen en
> Hive — ahi no calcula ningun resultado de negocio, solo transforma.
>
> Y por separado, en 3 scripts independientes, hace los 3 analisis
> obligatorios que el requerimiento pide y que si calculan algo:
> `tendencias_consumo` agrupa los items de cada pedido por mes y categoria,
> para saber que se vende mas y cuando. `horarios_pico` junta pedidos y
> reservas para encontrar las horas y dias con mas actividad. Y
> `crecimiento_mensual` usa una Window Function `LAG()` para comparar cada
> mes contra el mes inmediatamente anterior y calcular el porcentaje de
> crecimiento, sin necesidad de self-joins. Estos 3 escriben directo a
> PostgreSQL, sin pasar por Hive en ningun momento."

**Comando (terminal con port-forward de Postgres activo):**

```powershell
kubectl exec -n reservainteligente postgres-0 -- psql -U postgres -d restaurantes_db -c "SELECT anio, mes, ingresos_mes, crecimiento_ingresos_pct FROM analytics_crecimiento_mensual ORDER BY anio, mes;"
```

> "Aqui vemos el crecimiento mes a mes real: por ejemplo junio creció un
> 56% en ingresos respecto a mayo. Estos 3 analisis ahora corren
> automaticamente dentro del DAG de Airflow, que vamos a ver en un momento."

---

## 04:00 – 05:15 (1:15) — Req 3: Visualizacion de Datos con Metabase (Chris)

**Mostrar en pantalla:** Metabase en el navegador, los 3 dashboards.

**Guion:**

> "El tercer requerimiento pide una herramienta de visualizacion libre con al
> menos 3 dashboards: ingresos por mes y categoria, actividad de clientes por
> zona, y pedidos completados versus cancelados. Elegimos Metabase porque se
> conecta nativamente a PostgreSQL sin necesidad de un driver JDBC de Hive —
> las vistas de Hive se materializan en tablas `analytics_*` en PostgreSQL, y
> Metabase las lee de ahi directamente."

**Accion:** Navegar entre los 3 dashboards mostrando cada grafico.

> "Aqui esta el dashboard de ingresos por mes y categoria, con las barras
> agrupadas por categoria de producto. Este es el de actividad por zona,
> mostrando clientes unicos y pedidos por restaurante. Y este ultimo muestra
> pedidos completados versus cancelados por mes, con la tasa de cancelacion."

---

## 05:15 – 06:45 (1:30) — Req 4: Orquestacion con Apache Airflow (Chris)

**Mostrar en pantalla:** Airflow UI, vista Graph del DAG `etl_reserva_dw`.

**Guion:**

> "El cuarto requerimiento pide un DAG en Airflow que integre extraccion de
> PostgreSQL, transformacion con Spark, carga en el Data Warehouse, y
> reindexado de Elasticsearch si cambia el catalogo de productos.
>
> Este es nuestro DAG, `etl_reserva_dw`, con 7 tareas encadenadas. Primero
> `cargar_dw_hive`, que extrae de PostgreSQL y carga el esquema estrella en
> Hive. Luego los 3 analisis de Spark que acabamos de ver. Despues
> `materializar_vistas_metabase`, que copia las vistas de Hive a PostgreSQL.
> Y al final, la parte condicional: `verificar_cambio_catalogo` compara la
> fecha de actualizacion de los menus contra la corrida anterior usando una
> Variable de Airflow; si no cambio nada, usa un `ShortCircuitOperator` para
> saltarse la ultima tarea. Si si cambio, dispara `reindexar_elasticsearch`,
> que hace un POST al search-service para reconstruir el indice."

**Accion:** Hacer click en una corrida exitosa (Run) para mostrar las 7 tareas en verde.

> "Aqui se ve una corrida completa con las 7 tareas en exito. El DAG corre
> automaticamente `@daily`, y tambien lo podemos disparar a mano:"

**Comando:**

```powershell
kubectl exec -n reservainteligente deploy/airflow-scheduler -- airflow dags list-runs -d etl_reserva_dw --output table
```

> "Y aca vemos el historial: no solo corridas manuales, sino corridas de tipo
> `scheduled`, que confirman que el pipeline corre solo todos los dias."

---

## 06:45 – 08:45 (2:00) — Req 5: Neo4J para Analisis de Grafos y Rutas (Espi)

**Mostrar en pantalla:** Neo4J Browser.

**Guion:**

> "El quinto requerimiento pide modelar usuarios, productos y pedidos en un
> grafo con Neo4J, identificar patrones de co-compra y usuarios influyentes,
> y simular rutas de entrega con geonodos y relaciones de distancia.
>
> Nuestro grafo tiene 5 tipos de nodos: Usuario, Restaurante, Producto,
> Pedido y Zona; y 7 tipos de relaciones, incluyendo `RECOMENDO` entre
> usuarios, que modela una red de referidos, y `DISTANCIA_A` entre zonas, que
> tiene el peso en kilometros para calcular rutas."

**Comando 1 — vista visual del grafo:**

```cypher
MATCH (z1:Zona)-[r:DISTANCIA_A]->(z2:Zona) RETURN z1, r, z2
```

> "Estas son las 7 zonas geograficas y sus distancias — los geonodos que pide
> el requerimiento."

**Comando 2 — co-compras (los 5 productos mas comprados juntos):**

```cypher
MATCH (p1:Producto)<-[:CONTIENE]-(o:Pedido)-[:CONTIENE]->(p2:Producto)
WHERE p1.id < p2.id AND o.estado <> 'cancelado'
WITH p1.nombre AS producto_1, p2.nombre AS producto_2, count(o) AS veces_juntos
ORDER BY veces_juntos DESC LIMIT 5
RETURN producto_1, producto_2, veces_juntos;
```

> "Esta consulta responde directamente el primer bullet del requerimiento:
> los 5 productos mas comprados juntos."

**Comando 3 — usuarios que recomiendan a otros:**

```cypher
MATCH (u:Usuario)-[:RECOMENDO]->(referido:Usuario)
RETURN u.nombre AS usuario, count(referido) AS usuarios_recomendados
ORDER BY usuarios_recomendados DESC LIMIT 5;
```

> "Y esta es la red de referidos: usuarios que trajeron a otros usuarios al
> sistema, el segundo bullet del requerimiento."

**Comando 4 — camino minimo entre zonas:**

```cypher
MATCH path = shortestPath(
    (origen:Zona {nombre: "Calle Roma"})-[:DISTANCIA_A*]->(destino:Zona {nombre: "Muelle"})
)
RETURN [n IN nodes(path) | n.nombre] AS ruta,
       reduce(dist = 0, r IN relationships(path) | dist + r.km) AS km_total;
```

> "Y por ultimo, el camino minimo entre dos zonas usando `shortestPath` de
> Cypher, que es la base de la optimizacion de rutas que vamos a ver en el
> siguiente requerimiento."

---

## 08:45 – 09:45 (1:00) — Req 6: Asignacion de Rutas de Entrega (Espi)

**Mostrar en pantalla:** terminal con `curl`, o Postman/navegador.

**Guion:**

> "El sexto requerimiento pide simular y optimizar rutas de entrega con
> geolocalizacion de clientes, usando vecino mas cercano o consultas en
> Neo4J. Implementamos esto como un endpoint REST en nuestra API, ademas de
> un script standalone."

**Comando:**

```powershell
curl "http://localhost:8000/routes/delivery?repartidores=2"
```

> "El endpoint consulta Neo4J para traer los pedidos a domicilio pendientes,
> los agrupa por restaurante de origen, los reparte entre repartidores con
> round-robin, y para cada uno aplica el algoritmo de vecino mas cercano: en
> cada paso va al cliente mas cercano que aun no visito, usando las
> distancias reales que calculamos con `shortestPath` de Neo4J. El resultado
> muestra cada repartidor con su ruta optimizada y los kilometros totales."

---

## 09:45 – 11:00 (1:15) — Pruebas y Validaciones

**Mostrar en pantalla:** terminal corriendo `validate_all.py`.

**Guion:**

> "Por ultimo, el proyecto exige validar la integridad del warehouse, la
> ejecucion periodica de Airflow, y los resultados de Spark y Neo4J con
> consultas y reportes exportables. Para esto construimos 5 scripts de
> validacion: uno por cada capa, y un orquestador que los corre todos."

**Comando:**

```powershell
python validate_all.py
```

> "Cada script imprime un resumen detallado y exporta un reporte JSON como
> evidencia. Vemos que Neo4J valida 19 de 19 verificaciones: integridad del
> grafo, las consultas Cypher del requerimiento 5, y el modulo de rutas del
> requerimiento 6. Airflow valida 16 de 16: conectividad, configuracion del
> DAG, historial de corridas automaticas, y el estado de las 7 tareas. Spark
> valida 9 de 9: que los 3 analisis generaron datos correctos. Y el Data
> Warehouse valida 19 de 19: las tablas analytics en PostgreSQL, los datos
> origen, y las 7 tablas del esquema estrella en Hive. En total, 63 de 63
> validaciones exitosas en las 4 capas del proyecto."

---

## 11:00 – 12:00 (1:00) — Cierre (Chris)

**Mostrar en pantalla:** de vuelta al diagrama de arquitectura.

**Guion:**

> "En resumen: implementamos un Data Warehouse con esquema estrella en Hive
> sobre HDFS, un pipeline de Spark con los 3 analisis obligatorios
> orquestado diariamente por Airflow, 3 dashboards interactivos en Metabase,
> un grafo en Neo4J para co-compras, usuarios influyentes y rutas de
> entrega optimizadas con vecino mas cercano, y un set de validaciones
> automatizadas que confirman que las 4 capas del sistema funcionan
> correctamente de punta a punta. Todo desplegado y orquestado en
> Kubernetes. Gracias por su atencion."

---

## Checklist de tiempos (para practicar antes de grabar)

| Segmento | Inicio | Duracion | Fin |
|---|---|---|---|
| Intro + Arquitectura | 00:00 | 1:30 | 01:30 |
| Req 1 — OLAP/Hive | 01:30 | 1:15 | 02:45 |
| Req 2 — Spark | 02:45 | 1:15 | 04:00 |
| Req 3 — Metabase | 04:00 | 1:15 | 05:15 |
| Req 4 — Airflow | 05:15 | 1:30 | 06:45 |
| Req 5 — Neo4J | 06:45 | 2:00 | 08:45 |
| Req 6 — Rutas de entrega | 08:45 | 1:00 | 09:45 |
| Pruebas y Validaciones | 09:45 | 1:15 | 11:00 |
| Cierre | 11:00 | 1:00 | 12:00 |

**Recomendacion:** cronometrarse leyendo el guion en voz alta una vez sin
pantalla, ajustar el texto si algun bloque se pasa de su tiempo, y solo
despues grabar con pantalla compartida.
