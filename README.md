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
- **FastAPI**: Framework web moderno y de alto rendimiento para construir APIs REST en Python, con validación automática de datos y documentación interactiva.

### Autenticación y Seguridad
- **AWS Cognito**: Servicio de autenticación y autorización completamente administrado que proporciona gestión centralizada de identidades, JWT y control de acceso basado en roles (RBAC). Ofrece un nivel gratuito de hasta 50,000 usuarios activos mensuales.

### Base de Datos
- **PostgreSQL**: Sistema de gestión de bases de datos relacional robusto y confiable para almacenar usuarios, restaurantes, menús y reservas.

### Contenedorización y Orquestación
- **Docker**: Plataforma de contenedorización para empaquetar la aplicación y la base de datos de manera aislada y reproducible.
- **Docker Compose**: Herramienta para definir y ejecutar aplicaciones multi-contenedor, facilitando la orquestación de todos los servicios.

### Testing
- **Postman**: Herramienta para testing manual y automatizado de endpoints de la API, permitiendo validar funcionalidad, rendimiento y casos de uso.
- **Pytest**: Framework de testing en Python para implementar pruebas unitarias e integración con cobertura de código mínimo del 90%.

