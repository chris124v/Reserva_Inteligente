# Reserva Inteligente de Restaurantes — Etapa 2

La gestión eficiente de reservas y pedidos en restaurantes requiere una plataforma centralizada que integre autenticación segura, múltiples motores de base de datos, búsqueda avanzada y capacidad de escalar horizontalmente. Este proyecto implementa una API REST profesional que aborda todos estos aspectos mediante un stack tecnológico moderno y patrones de diseño reconocidos en la industria.

En este proyecto se realiza un sistema de backend complejo que integra CI/CD, mongo sharding y replica sets, redis, elastic search, nginx y patrones dao para usar dos BDs.

---

## Integrantes

- Christopher Daniel Vargas Villalta — 2024108443  
- Santiago Espinoza Rendon — 2024156530

---

## Link Video

[Video demostrativo en Google Drive](https://drive.google.com/drive/folders/1tQjWgyzezb5PqcCSK9BTaOXIgAVQ6A0w?usp=sharing)

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

## Estructura del Proyecto

```
Reserva_Inteligente/
├── .env.example
├── .gitignore
├── .github/
│   └── workflows/
│       └── ci-cd.yml
├── Dockerfile
├── docker-compose.yml
├── pytest.ini
├── README.md
│
├── app/
│   ├── __init__.py
│   ├── config.py
│   ├── main.py
│   ├── requirements.txt
│   ├── auth/
│   │   ├── __init__.py
│   │   ├── cognito.py
│   │   └── middleware.py
│   ├── database/
│   │   ├── __init__.py
│   │   ├── connection.py
│   │   ├── elastic.py
│   │   ├── init_db.py
│   │   ├── mongo.py
│   │   ├── redis.py
│   │   └── session.py
│   ├── dao/
│   │   ├── __init__.py
│   │   ├── base_dao.py
│   │   ├── factory.py
│   │   ├── mongodb/
│   │   │   ├── __init__.py
│   │   │   ├── menu_dao.py
│   │   │   ├── order_dao.py
│   │   │   ├── reservation_dao.py
│   │   │   ├── restaurant_dao.py
│   │   │   └── user_dao.py
│   │   └── postgresql/
│   │       ├── __init__.py
│   │       ├── menu_dao.py
│   │       ├── order_dao.py
│   │       ├── reservation_dao.py
│   │       ├── restaurant_dao.py
│   │       └── user_dao.py
│   ├── models/
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── menu.py
│   │   ├── order.py
│   │   ├── reservation.py
│   │   ├── restaurant.py
│   │   └── user.py
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── auth.py
│   │   ├── menus.py
│   │   ├── orders.py
│   │   ├── reservations.py
│   │   ├── restaurants.py
│   │   ├── users.py
│   │   └── ReservaRestaurantes.postman_collection.json
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── menu.py
│   │   ├── order.py
│   │   ├── reservation.py
│   │   ├── restaurant.py
│   │   └── user.py
│   └── services/
│       ├── __init__.py
│       ├── cache_service.py
│       ├── menu_service.py
│       ├── order_service.py
│       ├── reservation_service.py
│       ├── restaurant_service.py
│       ├── search_service.py
│       └── user_service.py
│
├── data/
│   └── seeds/
│       ├── instrucciones_seed.md
│       ├── mongo_cleanup.js
│       ├── mongo_seed.js
│       ├── postgres_cleanup.sql
│       └── postgres_seed.sql
│
├── kubernetes/
│   ├── Instrucciones.md
│   ├── namespace.yaml
│   ├── api/
│   │   ├── Instrucciones.md
│   │   ├── main-api/
│   │   │   ├── deployment.yaml
│   │   │   └── service.yaml
│   │   └── search-service/
│   │       ├── deployment.yaml
│   │       └── service.yaml
│   ├── balancer/
│   │   ├── nginx-configmap.yaml
│   │   ├── nginx-deployment.yaml
│   │   └── nginx-service.yaml
│   ├── config/
│   │   ├── configmap.yaml
│   │   ├── secret.yaml
│   │   └── secretsexample.yaml
│   ├── databases/
│   │   ├── elasticsearch/
│   │   │   ├── pvc.yaml
│   │   │   ├── service.yaml
│   │   │   └── statefulset.yaml
│   │   ├── mongodb/
│   │   │   ├── easy/
│   │   │   │   ├── service.yaml
│   │   │   │   └── statefulset.yaml
│   │   │   ├── sharding/
│   │   │   │   ├── config-server-statefulset.yaml
│   │   │   │   ├── init-sharding-job.yaml
│   │   │   │   ├── init-sharding-job-idempotent.yaml
│   │   │   │   ├── mongos-deployment.yaml
│   │   │   │   └── shard1-statefulset.yaml
│   │   │   └── Pruebas-Sharding.md
│   │   ├── postgres/
│   │   │   ├── service.yaml
│   │   │   └── statefulset.yaml
│   │   └── redis/
│   │       ├── deployment.yaml
│   │       └── service.yaml
│   └── scripts/
│       ├── .gitignore
│       ├── cleanup-all.ps1
│       ├── deploy-all.ps1
│       ├── kind-config.yaml
│       └── status.ps1
│
├── search_service/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── app/
│       ├── main.py
│       ├── routes/
│       │   └── search.py
│       └── services/
│           └── search_service.py
│
└── tests/
    ├── __init__.py
    ├── Instrucciones_tests.md
    ├── conftest.py
    ├── pytest.ini
    ├── data/
    │   ├── menus.json
    │   ├── orders.json
    │   ├── reservations.json
    │   ├── restaurants.json
    │   └── users.json
    ├── integration/
    │   ├── __init__.py
    │   ├── test_api_endpoints.py
    │   ├── test_auth_cognito.py
    │   ├── test_daos.py
    │   ├── test_flows.py
    │   ├── test_mongodb.py
    │   ├── test_nginx.py
    │   ├── test_redis.py
    │   ├── test_search_endpoints.py
    │   └── tests_posgres.py
    └── unit/
        ├── __init__.py
        ├── test_cache_service.py
        ├── test_menu_service.py
        ├── test_order_service.py
        ├── test_reservation_service.py
        ├── test_restaurant_service.py
        ├── test_search_service.py
        ├── test_services.py
        ├── test_user_service.py
        └── test_validation.py
```

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

## Cambiar el Motor de Base de Datos

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

## Ejecutar las Pruebas

Esto tambien se puede comprobar en el CI/CD cuando hacemos el git push entonces o se prueba localmente o lo vemos en el github actions. 

```powershell

# Pruebas unitarias con cobertura superar 90%
python -m pytest --cov=app.services --cov=app.schemas --cov=app.models --cov-report=term-missing tests/unit

# Pruebas de integración
python -m pytest tests/integration/test_api_endpoints.py tests/integration/test_daos.py -v

# Cobertura global
python -m pytest --cov=app --cov-report=term tests/unit tests/integration -q
```

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