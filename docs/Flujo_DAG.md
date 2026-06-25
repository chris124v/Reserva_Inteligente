# Flujo DAG — Reserva Inteligente

Diagramas del pipeline analítico completo: el DAG de Airflow `etl_reserva_dw`,
la capa de grafos Neo4J y las validaciones automatizadas.

---

## 1. Flujo completo del DAG `etl_reserva_dw` (Airflow `@daily`)

Cadena lineal de 7 tareas. Las tareas Spark corren con `spark-submit --master local[*]`
dentro del contenedor del scheduler. La verificación de catálogo es un
`ShortCircuitOperator`: si el catálogo de menús no cambió, se salta el reindexado.

```mermaid
flowchart TD
    subgraph SRC["Fuentes operacionales"]
        PG[("PostgreSQL operacional<br/>restaurantes_db<br/>users · restaurants · menus · reservas · orders")]
        SS["search-service<br/>(API /search/reindex)"]
        ES[("Elasticsearch<br/>indice de menus")]
    end

    subgraph DAG["DAG etl_reserva_dw — schedule @daily · retries=3 · max_active_runs=1"]
        direction TB
        T1["cargar_dw_hive<br/><i>etl_dimensiones_hechos.py</i><br/>Carga dims + hechos al DW (Hive)"]
        T2["analisis_tendencias_consumo<br/><i>tendencias_consumo.py</i>"]
        T3["analisis_horarios_pico<br/><i>horarios_pico.py</i>"]
        T4["analisis_crecimiento_mensual<br/><i>crecimiento_mensual.py</i>"]
        T5["materializar_vistas_metabase<br/><i>materializar_vistas_metabase.py</i><br/>Vistas Hive → tablas analytics_*"]
        T6{"verificar_cambio_catalogo<br/>ShortCircuitOperator<br/>¿cambió MAX fecha_actualizacion de menus?"}
        T7["reindexar_elasticsearch<br/>POST search-service /search/reindex"]

        T1 --> T2 --> T3 --> T4 --> T5 --> T6
        T6 -->|"Sí cambió"| T7
        T6 -.->|"No cambió → skip"| SKIP["(tareas siguientes omitidas)"]
    end

    subgraph DW["Data Warehouse (esquema estrella en Hive)"]
        HIVE[("reserva_dw<br/>dim_tiempo · dim_usuario · dim_restaurante<br/>dim_producto · dim_ubicacion<br/>fact_pedidos · fact_reservas")]
    end

    subgraph ANALYTICS["Tablas analiticas (PostgreSQL) para Metabase"]
        AT[("analytics_tendencias_consumo<br/>analytics_horarios_pico<br/>analytics_crecimiento_mensual<br/>analytics_ingresos_mes_categoria<br/>analytics_actividad_zona<br/>analytics_pedidos_estado")]
        MB["Metabase<br/>3 dashboards"]
    end

    PG --> T1
    T1 --> HIVE
    PG --> T2 & T3 & T4
    T2 & T3 & T4 --> AT
    HIVE --> T5 --> AT
    AT --> MB
    PG --> T6
    T7 --> SS --> ES
```

**Reglas de dependencia (idempotencia del catálogo):**
`verificar_cambio_catalogo` compara `MAX(fecha_actualizacion)` de `menus` contra el
valor guardado en una *Airflow Variable* (`ultima_fecha_actualizacion_menus`).
Solo si hay un cambio dispara `reindexar_elasticsearch`; si no, hace short-circuit
y evita reindexar Elasticsearch sin necesidad.

---

## 2. Estructura del grafo Neo4J (Req 5 y 6)

Pipeline independiente del DAG: `seed_neo4j.py` carga el grafo desde PostgreSQL.
Las consultas de co-compras, usuarios influyentes y referidos están en
`queries.cypher`; las rutas de entrega en `rutas_entrega.py`.

```mermaid
flowchart LR
    U(("Usuario<br/>39"))
    P(("Pedido<br/>200"))
    R(("Restaurante<br/>20"))
    PR(("Producto<br/>300"))
    Z(("Zona<br/>7"))

    U -->|"REALIZO (200)"| P
    P -->|"EN (200)"| R
    P -->|"CONTIENE {cantidad} (388)"| PR
    PR -->|"PERTENECE_A (300)"| R
    R -->|"UBICADO_EN (20)"| Z
    Z -->|"DISTANCIA_A {km} (30)"| Z
    U -->|"RECOMENDO (21)"| U
```

**Casos de uso sobre el grafo:**
- **Co-compras:** productos comprados juntos vía `(:Pedido)-[:CONTIENE]->(:Producto)`.
- **Usuarios influyentes:** actividad por `(:Usuario)-[:REALIZO]->(:Pedido)`.
- **Red de referidos:** `(:Usuario)-[:RECOMENDO]->(:Usuario)`.
- **Rutas de entrega:** `shortestPath` sobre `(:Zona)-[:DISTANCIA_A]->(:Zona)`.

---

## 3. Validaciones automatizadas (`validate_all.py`)

Orquestador que corre las 4 suites en orden y consolida el reporte.
Requiere port-forwards a neo4j (7687), airflow (8080), postgres (5432) y hive (10000).

```mermaid
flowchart TD
    VA["validate_all.py<br/>→ validate_all_report.json"]

    VA --> V1["validate_neo4j.py<br/>grafo · Cypher · rutas"]
    VA --> V2["validate_airflow.py<br/>API · DAG · runs · tareas"]
    VA --> V3["validate_spark.py<br/>tablas analytics_*"]
    VA --> V4["validate_dw.py<br/>esquema estrella Hive + origen PG"]

    V1 -.->|"Bolt :7687"| N[("Neo4J")]
    V2 -.->|"REST :8080"| AF[("Airflow webserver")]
    V2 -.->|":5432"| PGV[("PostgreSQL")]
    V3 -.->|":5432"| PGV
    V4 -.->|":5432 + Hive :10000"| DWV[("PostgreSQL + Hive")]

    V1 --> R1["✅ 19/19"]
    V2 --> R2["✅ 16/16"]
    V3 --> R3["✅ 9/9"]
    V4 --> R4["✅ 19/19"]
```

