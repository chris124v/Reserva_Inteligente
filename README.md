# Reserva Inteligente de Restaurantes — Etapa 2

La gestión eficiente de reservas y pedidos en restaurantes requiere una plataforma centralizada que integre autenticación segura, múltiples motores de base de datos, búsqueda avanzada y capacidad de escalar horizontalmente. Este proyecto implementa una API REST profesional que aborda todos estos aspectos mediante un stack tecnológico moderno y patrones de diseño reconocidos en la industria.

En este proyecto se realiza un sistema de backend complejo que integra CI/CD, mongo sharding y replica sets, redis, elastic search, nginx y patrones dao para usar dos BDs.

---

## Integrantes

- Christopher Daniel Vargas Villalta — 2024108443  
- Santiago Espinoza Rendon — 2024156530

---

## Link Video

En este link estaria todo, el video, el pdf y todo el codigo.

[Video demostrativo en Google Drive](https://drive.google.com/drive/folders/1JhWkfgqhB1LY0vh_wJm4GzSwQ3yHh7LF?usp=sharing)

---

## Stack Tecnológico

### Backend y API
- **Python 3.11** — Versión utilizada en el pipeline CI/CD y contenedores Docker.
- **FastAPI** — Framework web de alto rendimiento para construir APIs REST con validación automática de datos via Pydantic y documentación interactiva en `/docs`.

### Autenticación y Seguridad
- **AWS Cognito** — Servicio de autenticación completamente administrado. Gestiona el registro de usuarios, emisión y validación de tokens JWT con control de acceso basado en roles (RBAC).

### Bases de Datos
- **PostgreSQL 15** — Motor relacional principal. Se usa con SQLAlchemy ORM para mapeo objeto-relacional.
- **MongoDB 7** — Motor NoSQL orientado a documentos. Se usa con PyMongo y soporte de Sharding + Replica Set en Kubernetes.
- **Patrón DAO** — Permite cambiar entre PostgreSQL y MongoDB modificando únicamente la variable `DATABASE_TYPE` en el `.env`, sin tocar el código de negocio.

### Cache
- **Redis 7** — Base de datos en memoria usada como capa de caché. Almacena respuestas frecuentes con TTL configurable para reducir la carga sobre la base de datos principal. Implementa el patrón Cache-Aside.

### Búsqueda
- **ElasticSearch 8.15** — Motor de búsqueda de texto completo. Los menús se indexan automáticamente y se exponen mediante un microservicio independiente (`search_service`) con endpoints de búsqueda por texto y categoría.

### Contenedorización y Orquestación
- **Docker** — Contenerización de todos los servicios con imágenes reproducibles.
- **Docker Compose** — Ambiente de desarrollo local con PostgreSQL y el API principal.
- **Kubernetes** — Orquestación en producción. Gestiona réplicas, escalado horizontal, almacenamiento persistente y recuperación automática de fallos.

### CI/CD
- **GitHub Actions** — Pipeline automatizado que ejecuta pruebas y publica imágenes Docker en cada `push` a `main`. El pipeline tiene dos jobs: pruebas (con cobertura ≥ 90%) y construcción/publicación de imágenes.
- **GitHub Container Registry (GHCR)** — Almacén de imágenes Docker accesible en `ghcr.io/owner/repo`.

### Balanceo de Carga
- **Nginx** — Actúa como reverse proxy y balanceador de carga. Es el único punto de entrada al sistema (puerto 80). Enruta `/api/**` al API principal y `/search/**` al microservicio de búsqueda.

### Testing
- **Pytest + pytest-cov** — Framework de pruebas con medición de cobertura. El proyecto mantiene cobertura global superior al 90%.

---

## Arquitectura del Sistema

El sistema se compone de los siguientes microservicios y componentes:

```
Cliente HTTP
    ↓
Nginx (Balanceador :80)
    ├── /api/**  → API Principal FastAPI (2+ réplicas)
    │               ├── AWS Cognito (autenticación JWT)
    │               ├── PostgreSQL / MongoDB (persistencia)
    │               └── Redis (caché)
    └── /search/** → Search Service FastAPI
                        └── ElasticSearch (índice de menús)

CI/CD: GitHub Actions → GHCR (imágenes Docker)
Orquestación: Kubernetes (namespace: reservainteligente)
```

---

## Roles y Permisos

El sistema maneja dos roles en la BD local (`users.rol`):

| Rol | Permisos |
|-----|----------|
| `cliente` | Crear reservas y pedidos. Ver sus propios datos. |
| `admin` | Crear y gestionar restaurantes y menús propios. Ver pedidos y reservas de sus restaurantes. |

- **Registro como cliente:** `POST /auth/register` sin enviar `rol`.
- **Registro como admin:** `POST /auth/register` con `rol: "admin"` y el campo `admin_code` si `ADMIN_REGISTRATION_CODE` está configurado en el `.env`.
- **Master Admin:** Para que un admin gestione otros usuarios (update/delete), debe enviar el header `X-Master-Admin-Code` con el valor de `MASTER_ADMIN_CODE` del `.env`.

---

## Instrucciones de Ejecución

### Requisitos Previos

- Python 3.11
- Docker y Docker Compose
- kubectl y kind (para Kubernetes)
- Cuenta AWS con Cognito configurado
- Git

### Paso 1: Clonar el Repositorio

```powershell
git clone https://github.com/chris124v/Reserva_Inteligente.git
cd Reserva_Inteligente
```

### Paso 2: Configurar Variables de Entorno y Secret

Copiar el archivo de ejemplo y completar con los valores reales:

```powershell
copy .env.example .env
```

Variables importantes del `.env`:

```dotenv
DATABASE_TYPE=postgresql          # o mongodb para usar MongoDB
DATABASE_USER=postgres
DATABASE_PASSWORD=tu_password
DATABASE_NAME=restaurantes_db
MONGODB_URI=mongodb://localhost:27017
AWS_COGNITO_REGION=us-east-2
AWS_COGNITO_USER_POOL_ID=us-east-2_xxxxxxxx
AWS_COGNITO_CLIENT_ID=xxxxxxxxxxxxxxxxxx
REDIS_HOST=redis-service
REDIS_TTL=60
ELASTICSEARCH_URL=http://elasticsearch:9200
```

Hacer lo mismo con el archivo secret.yaml, agregarlo con los datos reales en la ruta kubernetes/config/secret.yaml. Basandose en el archivo de ejemplo pero con datos reales.

### Paso 3: Crear y Activar el Entorno Virtual

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install --upgrade pip
pip install -r app/requirements.txt
```

### Paso 4: Ejecutar en Kubernetes (Ambiente Completo)

El ambiente de Kubernetes incluye todos los servicios: API, MongoDB con Sharding, Redis, ElasticSearch y Nginx.

Estos serian comandos manuales

```powershell
# Crear el namespace
kubectl apply -f kubernetes/namespace.yaml

# Desplegar configuración
kubectl apply -f kubernetes/config/

# Desplegar bases de datos
kubectl apply -f kubernetes/databases/mongodb/sharding/
kubectl apply -f kubernetes/databases/postgres/
kubectl apply -f kubernetes/databases/redis/
kubectl apply -f kubernetes/databases/elasticsearch/

# Desplegar APIs
kubectl apply -f kubernetes/api/main-api/
kubectl apply -f kubernetes/api/search-service/

# Desplegar balanceador
kubectl apply -f kubernetes/balancer/
```

Con este script de inicializacion todo queda listo siguiendo este flujo en la terminal: 

### 1. Desplegar (deploy-all.ps1)

```powershell
.\deploy-all.ps1
```
Despliega todo: namespace, configuracion, bases de datos y API.

### 2. Limpiar (cleanup-all.ps1)

```powershell

Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
powershell -ExecutionPolicy Bypass -File .\cleanup-all.ps1

.\cleanup-all.ps1
```
Elimina todos los recursos. Pide confirmacion antes por si las dudas. Ese primer execution policy es por si no funciona con un solo comando.

### 3. Estado (status.ps1)

```powershell
.\status.ps1
```
Verifica el estado del ambiente completo.

Para acceder al sistema desde la máquina local:

```powershell
kubectl port-forward service/nginx-service 8080:80 -n reservainteligente
```

Luego acceder en `http://localhost/api/docs` y `http://localhost/search/docs`.

---

## Paso 5: Cambiar el Motor de Base de Datos

El patrón DAO permite cambiar entre PostgreSQL y MongoDB sin modificar el código:

```dotenv
# En el .env:
DATABASE_TYPE=mongodb      # usa MongoDB
DATABASE_TYPE=postgresql   # usa PostgreSQL
```

Cambir eso mismo en el kubernetes/config/configmap.yaml

```dotenv
# En el configmap.yaml:
DATABASE_TYPE=mongodb      # usa MongoDB
DATABASE_TYPE=postgresql   # usa PostgreSQL
```

Para aplicar cambios de un solo
```powershell
kubectl apply -f kubernetes/config/configmap.yaml
```

Tambien podemos hacer git push para subir todo a GHCR y despues hacer deploy all y funcionaria bien.

---

## Paso 6: Ejecutar las Pruebas

Esto tambien se puede comprobar en el CI/CD cuando hacemos el git push entonces o se prueba localmente o lo vemos en el github actions. 

```powershell

# Pruebas unitarias con cobertura superar 90%
python -m pytest --cov=app.services --cov=app.schemas --cov=app.models --cov-report=term-missing tests/unit

# Pruebas de integración
python -m pytest tests/integration/test_api_endpoints.py tests/integration/test_daos.py -v

# Cobertura global
python -m pytest --cov=app --cov-report=term tests/unit tests/integration -q
```

## Paso 7: Desplegar Neo4J (Análisis de Grafos y Rutas)

Neo4J es la base de datos de grafos usada para modelar relaciones entre usuarios, productos y pedidos, identificar patrones de co-compra y calcular rutas de entrega óptimas.

### Prerequisitos

- `deploy-all.ps1` ya ejecutado (PostgreSQL con datos cargados)
- Python 3.11
- Helm instalado:

```powershell
winget install Helm.Helm
# Cerrar y abrir PowerShell nuevo, luego verificar:
helm version
```

> **Nota:** Si `helm` no se reconoce después de instalar, descargarlo manualmente desde PowerShell como administrador:
> ```powershell
> curl.exe -Lo helm.zip https://get.helm.sh/helm-v3.14.0-windows-amd64.zip
> Expand-Archive -Path helm.zip -DestinationPath helm-tmp
> Move-Item .\helm-tmp\windows-amd64\helm.exe "C:\Windows\System32\helm.exe"
> Remove-Item helm.zip, helm-tmp -Recurse
> ```

### Desplegar con el script

```powershell
cd kubernetes\scripts
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\deploy-neo4j.ps1
```

El script hace automáticamente:
1. Agrega el repositorio Helm oficial de Neo4J
2. Instala Neo4J en el namespace `reservainteligente`
3. Instala las dependencias Python (`neo4j`, `psycopg2-binary`)
4. Carga el grafo desde PostgreSQL (`neo4j/seed_neo4j.py`)

### Acceder a Neo4J Browser

```powershell
kubectl port-forward svc/neo4j 7474:7474 7687:7687 -n reservainteligente
```

Luego abrir `http://localhost:7474` con usuario `neo4j` y contraseña `Neo4jPass123!`.

### Verificar que el grafo cargó correctamente

Ejecutar en Neo4J Browser:

```cypher
MATCH (n) RETURN labels(n), count(n)
```

Debe mostrar: Usuario (5), Restaurante (7), Producto (28), Pedido (12), Zona (7).

### Dependencias Python del módulo Neo4J

```powershell
pip install -r neo4j/requirements.txt
```

### Estructura del grafo

```
(Usuario)-[:REALIZO]->(Pedido)-[:EN]->(Restaurante)
(Pedido)-[:CONTIENE {cantidad}]->(Producto)
(Producto)-[:PERTENECE_A]->(Restaurante)
(Restaurante)-[:UBICADO_EN]->(Zona)
(Zona)-[:DISTANCIA_A {km}]->(Zona)
```

Las consultas Cypher para co-compras, usuarios influyentes y rutas mínimas se encuentran en `neo4j/queries.cypher`.

---

## Paso 8: Seeding de la BD

Primero crear 5 usuarios.

Dos admins y 3 clientes. A partir de eso se puede correr una seed con datos de prueba que se encuentra en la carpeta data.
Entrar a instrucciones_seed.md para ejecutar cada archivo de seeding tanto para postgres como para mongodb.

---

## Endpoints Principales

| Método | Ruta | Descripción | Auth |
|--------|------|-------------|------|
| POST | `/auth/register` | Registrar usuario | No |
| POST | `/auth/login` | Iniciar sesión | No |
| GET | `/restaurants/` | Listar restaurantes | No |
| POST | `/restaurants/` | Crear restaurante | Admin |
| GET | `/menus/` | Listar menús | No |
| POST | `/menus/` | Crear menú | Admin |
| POST | `/reservations/` | Crear reserva | Cliente |
| GET | `/reservations/` | Ver mis reservas | Cliente |
| POST | `/orders/` | Crear pedido | Cliente |
| GET | `/search/menus?q=texto` | Buscar menús | No |
| GET | `/search/menus/category/{cat}` | Filtrar por categoría | No |
| POST | `/search/reindex` | Reindexar menús | No |

---

## Paso 9: Desplegar OLAP, Spark, Hive y Airflow

Este paso despliega el stack de análisis de datos: HDFS, Hive, Spark y Airflow.

```powershell
cd kubernetes\scripts
.\deploy-olap.ps1
```

### Port-forwards necesarios para OLAP

```powershell
# Airflow UI
kubectl port-forward -n reservainteligente svc/airflow-webserver 8080:8080
# Metabase UI
kubectl port-forward -n reservainteligente svc/metabase 3000:3000
# HiveServer2
kubectl port-forward -n reservainteligente svc/hiveserver2 10000:10000
# Spark Master UI
kubectl port-forward -n reservainteligente svc/spark-master 8081:8080
```

### Disparar el pipeline manualmente

```powershell
kubectl exec -n reservainteligente deployment/airflow-scheduler -- airflow dags trigger etl_reserva_dw
```

O desde la UI de Airflow en `http://localhost:8080` (usuario: `admin`, password: `admin`).

---

## Paso 10: Pruebas y Validaciones

Las validaciones verifican la integridad del sistema completo: Neo4J, pipeline de Airflow, análisis Spark y Data Warehouse.

### Requisitos

```powershell
pip install neo4j psycopg2-binary requests pyhive thrift
```

### Port-forwards necesarios

Abrir cada uno en una terminal separada:

```powershell
# Neo4J
kubectl port-forward svc/neo4j-service 7474:7474 7687:7687 -n reservainteligente
# Airflow
kubectl port-forward svc/airflow-webserver 8080:8080 -n reservainteligente
# PostgreSQL
kubectl port-forward svc/postgres-service 5432:5432 -n reservainteligente
# HiveServer2
kubectl port-forward svc/hiveserver2 10000:10000 -n reservainteligente
```

### Correr todas las validaciones de una vez

```powershell
python validate_all.py
```

### O correr cada validación individualmente

```powershell
# 1. Neo4J — grafo, consultas Cypher, rutas de entrega
$env:NEO4J_PASSWORD="Neo4jPass123!"
python Neo4j/validate_neo4j.py

# 2. Airflow — pipeline ETL y schedule @daily
python olap/validate_airflow.py

# 3. Spark — análisis de tendencias, horarios pico y crecimiento mensual
python olap/validate_spark.py

# 4. Data Warehouse — integridad de tablas analytics_* y esquema estrella
python olap/validate_dw.py
```

### Reportes exportables

Cada script genera un reporte JSON en su carpeta:

| Script | Reporte |
|--------|---------|
| `Neo4j/validate_neo4j.py` | `Neo4j/validation_report.json` |
| `olap/validate_airflow.py` | `olap/validate_airflow_report.json` |
| `olap/validate_spark.py` | `olap/validate_spark_report.json` |
| `olap/validate_dw.py` | `olap/validate_dw_report.json` |
| `validate_all.py` | `validate_all_report.json` |