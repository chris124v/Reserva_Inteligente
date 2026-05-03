# Imagen base con Python 3.11
FROM python:3.11-slim

# Establecer directorio de trabajo (el paquete `app` vive bajo /src/app)
WORKDIR /src

# Raíz de imports: debe coincidir con el ConfigMap (PYTHONPATH) en Kubernetes
ENV PYTHONPATH=/src

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements.txt
COPY app/requirements.txt /tmp/requirements.txt

# Instalar dependencias Python
RUN pip install --no-cache-dir -r /tmp/requirements.txt

# Copiar todo el proyecto para conservar el paquete app
COPY . /src/

# Exponer puerto
EXPOSE 8000

# Comando para iniciar la aplicación
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]