# Análisis y Procesamiento OLAP - Proyecto 2

## Objetivo

Implementar capacidades de análisis de datos mediante soluciones OLAP, procesamiento con Spark, rutas de entrega optimizadas, análisis de grafos con Neo4J y visualización con herramientas libres. Integrar pipeline de orquestación con Apache Airflow.

---

## Componentes y Requerimientos

### 1. Arquitectura OLAP y Almacén de Datos (20%)

- Crear esquema estrella o copo de nieve consolidando datos históricos de reservas, productos, pedidos y usuarios
- Implementar Data Warehouse con Apache Hive (open-source)
- Crear mínimo 5 cubos/vistas OLAP para análisis agregados por:
  - Tiempo
  - Ubicación
  - Tipo de producto
  - Frecuencia de uso

### 2. Procesamiento con Apache Spark (20%)

- Procesar grandes volúmenes de órdenes, productos y reservas
- Implementar transformaciones con Spark DataFrames y SparkSQL
- Realizar 3 tipos de análisis obligatorios:
  - Tendencias de consumo
  - Horarios pico
  - Crecimiento mensual (MoM)

### 3. Visualización de Datos (15%)

- Usar herramienta libre: Apache Superset, Metabase o Redash
- Construir 3 dashboards obligatorios:
  - **Dashboard 1:** Ingresos por mes y categoría de producto
  - **Dashboard 2:** Actividad de clientes por zona geográfica
  - **Dashboard 3:** Estadísticas de pedidos completados vs cancelados

### 4. Orquestación con Apache Airflow (15%)

Diseñar DAG que integre:
- Extracción de datos de MongoDB o PostgreSQL
- Transformación con Spark
- Carga en Data Warehouse
- Reindexado de ElasticSearch (si catálogo de productos cambia)

### 5. Uso de Neo4J para Análisis de Grafos y Rutas (15%)

- Modelar relaciones entre usuarios, productos y pedidos en grafo
- Identificar patrones de co-compra y usuarios influyentes
- Simular y optimizar rutas de entrega con geonodos
- Crear consultas Cypher para:
  - Los 5 productos más comprados juntos
  - Usuarios que recomiendan a otros
  - Caminos mínimos entre ubicaciones para reparto eficiente

### 6. Asignación de Rutas de Entrega (10%)

- Diseñar módulo para simular rutas de entrega con geolocalización
- Usar heurísticas: algoritmo vecino más cercano o consultas Neo4J
- Mostrar rutas optimizadas y asignaciones por repartidor

---

## Pruebas y Validaciones

- Verificar integridad de datos en warehouse
- Validar ejecución periódica del pipeline Airflow
- Validar resultados Spark y Neo4J con consultas y reportes exportables

---

## Entregables

- [ ] Código fuente y DAG de Airflow
- [ ] Scripts o notebooks de Spark
- [ ] Dashboards configurados y exportables
- [ ] Consultas Cypher y estructura del grafo
- [ ] Capturas de pantalla o video demostrativo
- [ ] Documentación técnica en PDF (flujo de datos, decisiones de diseño, ejemplos)

---

## Rúbrica de Evaluación

| Componente | Ponderación | Criterios |
|------------|-------------|-----------|
| Data Warehouse y OLAP | 20% | Modelación correcta y funcionalidad |
| Procesamiento Spark | 20% | Transformaciones y análisis realizados |
| Visualización | 15% | Dashboards informativos y bien presentados |
| Airflow | 15% | DAG funcional, modular y programado |
| Neo4J | 15% | Consultas útiles, grafo representativo, análisis y rutas |
| Enrutamiento | 10% | Lógica coherente y rutas óptimas simuladas |
| Documentación | 5% | Claridad, diagramas y explicación completa |

---

## División de Tareas (2 personas)

### Joche - Data & Backend
1. Data Warehouse + Esquema Estrella
2. Apache Spark (transformaciones y análisis)
3. Neo4J (modelado de grafo y consultas Cypher)
4. Apache Airflow (DAG orquestador)

### Compañero - Visualización & Enrutamiento
1. Visualización (Superset/Metabase/Redash)
2. Enrutamiento de entregas
3. Documentación técnica final

---

## Flujo Completo de Datos

```
API Actual (MongoDB/PostgreSQL)
    ↓
Airflow (extrae diariamente)
    ↓
Spark (transforma: tendencias, horarios, crecimiento)
    ↓
Data Warehouse Hive (almacena histórico)
    ↓
Neo4J (analiza relaciones y rutas)
    ↓
Superset/Metabase (visualiza en dashboards)
    ↓
Gerentes/Usuarios (toman decisiones basadas en datos)
```

---

## Fecha de Entrega

Entrega en formato comprimido antes de las **10:00 p.m.** del día acordado.

**Penalización:** 5% por cada 24 horas de retraso.

---

## Notas Importantes

- **NO cambiar código actual de la API** - Proyecto 2 es independiente
- Agregar nuevos servicios Docker (Hive, Spark, Airflow, Neo4J, Superset)
- Airflow lee de fuentes operacionales, carga en warehouse
- Dashboards y análisis se hacen del warehouse, no de la API directa
- Geolocalización (lat/long) será necesaria para enrutamiento eficiente