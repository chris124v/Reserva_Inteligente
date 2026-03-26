# Reserva_Inteligente

La gestión de reservas en restaurantes presenta desafíos significativos en la actualidad. Los establecimientos necesitan administrar de manera eficiente múltiples aspectos operacionales: el registro de usuarios (tanto clientes como administradores), la verificación de disponibilidad de mesas, la gestión de menús y productos, y la coordinación de pedidos con opción de recogida. Sin una solución centralizada, estas operaciones se vuelven complejas y propensas a errores, afectando tanto la experiencia del cliente como la productividad del restaurante.
Por otro lado, existe la necesidad de garantizar la seguridad y el control de acceso en el sistema. Es fundamental implementar mecanismos de autenticación robustos que permitan diferenciar entre clientes regulares y administradores de restaurantes, protegiendo la información sensible y asegurando que cada usuario tenga acceso únicamente a las funcionalidades que le corresponden. Una plataforma integrada que combine gestión de usuarios, autenticación segura, administración de restaurantes, menús y reservas es esencial para modernizar y optimizar las operaciones de los establecimientos gastronómicos.

---

## Integrantes

* Christopher Daniel Vargas Villalta, 2024108443
* Santiago Espinoza Rendon, 2024156530

--- 

## Technology Stack

### Backend y API

- **Python**: Usar version fija 3.13.7 y un .venv para manejar todas las dependencias ahi.

- **FastAPI**: Framework web moderno y de alto rendimiento para construir APIs REST en Python, con validación automática de datos y documentación interactiva.

### Autenticación y Seguridad
- **AWS Cognito**: Servicio de autenticación y autorización completamente administrado que proporciona gestión centralizada de identidades, JWT y control de acceso basado en roles (RBAC). 

### Base de Datos
- **PostgreSQL**: Sistema de gestión de bases de datos relacional robusto y confiable para almacenar usuarios, restaurantes, menús y reservas. Utilizamos SQLAlchemy para reducir complejidad a la hora de crear la BD.

### Contenedorización y Orquestación
- **Docker**: Plataforma de contenedorización para empaquetar la aplicación y la base de datos de manera aislada y reproducible.
- **Docker Compose**: Herramienta para definir y ejecutar aplicaciones multi-contenedor, facilitando la orquestación de todos los servicios.

### Testing
- **Postman**: Herramienta para testing manual y automatizado de endpoints de la API, permitiendo validar funcionalidad, rendimiento y casos de uso.
- **Pytest**: Framework de testing en Python para implementar pruebas unitarias e integración.

---

## Instructivo de Uso

### Instalacion de Dependencias

Requisitos Previos:

* Docker instalado
* Cuenta AWS 
* Python 3.13.7
* Git
* VS Code 

#### Paso 1: Github

Clonar repo :

``` 
git clone https://github.com/chris124v/Reserva_Inteligente.git

```

#### Paso 2: Crear y Activar entorno virtual

```
python -m venv .venv

.venv\Scripts\Activate.ps1

```

Se deberia ver (.venv) en su terminal

#### Paso 3: Instalar Dependencias

Update pip y ejecutar requirements.txt

```
pip install --upgrade pip

python -m pip install -r app\requirements.txt
```

#### Paso 4: Inicializar el contenedor 

Para ejecutarlo:

```
docker-compose up --build
```

Para borrarlo: 

```
docker-compose down -v
```

--- 

### Division

#### Chris 

* Carpeta Database = Conexiones --- RRR
* Carpeta Models = Esquemas BD --- RRR
* Carpeta Auth = Uso y conexion de JWT -- RRR
* Carpeta Routes = Implementacion EndPoints - R
* Archivos de config y main - R

#### Espi

* Carpeta Schemas = Validacion de datos
* Carpeta Services = Logica de Negocio
* Carpeta Tests = Pruebas Unitarias