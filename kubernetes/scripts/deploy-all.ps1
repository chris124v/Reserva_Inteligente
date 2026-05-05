# deploy-all.ps1 - Crea y despliega todo el ambiente de Reserva Inteligente en Kubernetes

Write-Host "=====================================" -ForegroundColor Cyan
Write-Host "  Reserva Inteligente - Deployment Script  " -ForegroundColor Cyan
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host ""

if (-not (Get-Command kubectl -ErrorAction SilentlyContinue)) {
    Write-Host "ERROR: kubectl no instalado" -ForegroundColor Red
    exit 1
}

Write-Host "[1/7] Verificando Kubernetes..." -ForegroundColor Yellow
kubectl cluster-info --request-timeout=5s 2>&1 | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Kubernetes no esta corriendo" -ForegroundColor Red
    exit 1
}
Write-Host "OK Kubernetes activo" -ForegroundColor Green
Write-Host ""

$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
$kubernetesPath = Split-Path -Parent $scriptPath
$projectRoot = Split-Path -Parent $kubernetesPath
Set-Location $projectRoot

Write-Host "[2/7] Construyendo imagenes Docker..." -ForegroundColor Yellow
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Host "ERROR: docker no instalado" -ForegroundColor Red
    exit 1
}
# Construir imagen con la etiqueta v7 (usar la misma etiqueta que deployment.yaml)
docker build -t reservainteligente-api:v7 .
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: fallo la construccion de la imagen Docker" -ForegroundColor Red
    exit 1
}
Write-Host "OK Imagen Docker construida" -ForegroundColor Green
Write-Host ""

# Construir imagen del search-service (microservicio separado)
Write-Host "  Search-service (v2)..." -ForegroundColor Cyan
docker build -t reservainteligente-search:v2 -f search_service/Dockerfile .
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: fallo la construccion de la imagen Docker del search-service" -ForegroundColor Red
    exit 1
}
Write-Host "OK Imagen search-service construida" -ForegroundColor Green
Write-Host ""

Set-Location $kubernetesPath

Write-Host "[3/7] Desplegando namespaces..." -ForegroundColor Yellow
kubectl apply -f namespace.yaml
Write-Host "OK Namespace creado" -ForegroundColor Green
Write-Host ""

Write-Host "[4/7] Desplegando configuracion..." -ForegroundColor Yellow
kubectl apply -f config/configmap.yaml
kubectl apply -f config/secret.yaml
Write-Host "OK Configuracion desplegada" -ForegroundColor Green
Write-Host ""

Write-Host "[5/7] Desplegando bases de datos..." -ForegroundColor Yellow
Write-Host "  PostgreSQL..." -ForegroundColor Cyan
kubectl apply -f databases/postgres/
Write-Host "  Redis..." -ForegroundColor Cyan
kubectl apply -f databases/redis/
Write-Host "  Elasticsearch..." -ForegroundColor Cyan
kubectl apply -f databases/elasticsearch/
Write-Host "  MongoDB Sharding..." -ForegroundColor Cyan
kubectl apply -f databases/mongodb/sharding/config-server-statefulset.yaml
kubectl wait --for=condition=ready pod -l app=mongo-configsvr -n reservainteligente --timeout=300s 2>$null
Start-Sleep -Seconds 10
kubectl apply -f databases/mongodb/sharding/shard1-statefulset.yaml
kubectl wait --for=condition=ready pod -l app=mongors1 -n reservainteligente --timeout=300s 2>$null
Start-Sleep -Seconds 10
kubectl apply -f databases/mongodb/sharding/mongos-deployment.yaml
kubectl wait --for=condition=ready pod -l app=mongos -n reservainteligente --timeout=300s 2>$null
Start-Sleep -Seconds 5

# Ejecutar job de inicializacion para configurar replica sets y sharding
Write-Host "  Inicializando configuración de sharding (job)..." -ForegroundColor Cyan
kubectl delete job mongo-init -n reservainteligente --ignore-not-found=true
kubectl apply -f databases/mongodb/sharding/init-sharding-job.yaml
kubectl wait --for=condition=complete job/mongo-init -n reservainteligente --timeout=300s 2>$null
Write-Host "  Job de inicializacion completado" -ForegroundColor Green
Write-Host "OK Bases de datos desplegadas" -ForegroundColor Green
Write-Host ""

Write-Host "[6/7] Esperando a que los pods esten listos..." -ForegroundColor Yellow
Start-Sleep -Seconds 10
kubectl wait --for=condition=ready pod -l app=postgres -n reservainteligente --timeout=300s 2>$null
kubectl apply -f api/main-api/
# Desplegar search-service
kubectl apply -f api/search-service/
kubectl set image deployment/search-service search-service=reservainteligente-search:v2 -n reservainteligente --record || Write-Host "Warning: no se pudo actualizar la imagen del search-service" -ForegroundColor Yellow
kubectl wait --for=condition=ready pod -l app=search-service -n reservainteligente --timeout=120s 2>$null
# Forzar que el Deployment use la imagen recién construída (útil si el manifest tiene la misma u otra etiqueta)
kubectl set image deployment/main-api main-api=reservainteligente-api:v7 -n reservainteligente --record || Write-Host "Warning: no se pudo actualizar la imagen con kubectl set image" -ForegroundColor Yellow
kubectl wait --for=condition=ready pod -l app=main-api -n reservainteligente --timeout=300s 2>$null

# Desplegar/actualizar balancer despues de API y search-service
kubectl apply -f balancer/
kubectl wait --for=condition=ready pod -l app=nginx-balancer -n reservainteligente --timeout=120s 2>$null

Write-Host "  Inicializando esquema PostgreSQL (ORM create_all)..." -ForegroundColor Cyan
$apiPod = kubectl get pods -n reservainteligente -l app=main-api -o jsonpath='{.items[0].metadata.name}'
if ([string]::IsNullOrWhiteSpace($apiPod)) {
    Write-Host "ERROR: no se encontro pod de main-api para inicializar BD" -ForegroundColor Red
    exit 1
}
kubectl exec -n reservainteligente $apiPod -c main-api -- python -m app.database.init_db
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: fallo la inicializacion del esquema PostgreSQL" -ForegroundColor Red
    exit 1
}
Write-Host "  Esquema PostgreSQL inicializado" -ForegroundColor Green
Write-Host "OK Todos los pods estan listos" -ForegroundColor Green
Write-Host ""

Write-Host "[7/7] Deployment completado!" -ForegroundColor Green
Write-Host ""
Write-Host "Conexiones disponibles:" -ForegroundColor Cyan
Write-Host "  API:           http://localhost:8000 (con port-forward)" -ForegroundColor White
Write-Host "  Search docs:   http://localhost:8001/docs (port-forward a search-service)" -ForegroundColor White
Write-Host "  Nginx:         http://localhost:8080 (port-forward a nginx-service)" -ForegroundColor White
Write-Host "  PostgreSQL:    localhost:5432 (postgres/postgres)" -ForegroundColor White
Write-Host "  Redis:         localhost:6379" -ForegroundColor White
Write-Host "  MongoDB:       localhost:27017" -ForegroundColor White
Write-Host "  Elasticsearch: localhost:9200 (con port-forward)" -ForegroundColor White
Write-Host ""
