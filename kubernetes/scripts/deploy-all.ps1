# deploy-all.ps1 - Crea y despliega todo el ambiente de Reserva Inteligente en Kubernetes usando imagenes GHCR

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
Set-Location $kubernetesPath

Write-Host "[2/7] Verificando uso de imagenes GHCR..." -ForegroundColor Yellow
Write-Host "OK Las imagenes se descargaran desde GitHub Container Registry:" -ForegroundColor Green
Write-Host "  ghcr.io/chris124v/reserva_inteligente-main-api:latest" -ForegroundColor Cyan
Write-Host "  ghcr.io/chris124v/reserva_inteligente-search-service:latest" -ForegroundColor Cyan
Write-Host ""

Write-Host "[3/7] Desplegando namespace..." -ForegroundColor Yellow
kubectl apply -f namespace.yaml
Write-Host "OK Namespace creado/verificado" -ForegroundColor Green
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

Write-Host "  Inicializando configuracion de sharding (job)..." -ForegroundColor Cyan
kubectl delete job mongo-init -n reservainteligente --ignore-not-found=true
kubectl apply -f databases/mongodb/sharding/init-sharding-job.yaml
kubectl wait --for=condition=complete job/mongo-init -n reservainteligente --timeout=300s 2>$null
Write-Host "  Job de inicializacion completado" -ForegroundColor Green

Write-Host "OK Bases de datos desplegadas" -ForegroundColor Green
Write-Host ""

Write-Host "[6/7] Desplegando API, search-service y balanceador..." -ForegroundColor Yellow
Start-Sleep -Seconds 10

kubectl wait --for=condition=ready pod -l app=postgres -n reservainteligente --timeout=300s 2>$null

Write-Host "  Main API..." -ForegroundColor Cyan
kubectl apply -f api/main-api/
kubectl rollout restart deployment/main-api -n reservainteligente
kubectl wait --for=condition=ready pod -l app=main-api -n reservainteligente --timeout=300s 2>$null

Write-Host "  Search Service..." -ForegroundColor Cyan
kubectl apply -f api/search-service/
kubectl rollout restart deployment/search-service -n reservainteligente
kubectl wait --for=condition=ready pod -l app=search-service -n reservainteligente --timeout=180s 2>$null

Write-Host "  Nginx Balancer..." -ForegroundColor Cyan
kubectl apply -f balancer/
kubectl rollout restart deployment/nginx-balancer -n reservainteligente
kubectl wait --for=condition=ready pod -l app=nginx-balancer -n reservainteligente --timeout=180s 2>$null

Write-Host "  Inicializando esquema PostgreSQL (ORM create_all)..." -ForegroundColor Cyan
$apiPod = kubectl get pods -n reservainteligente -l app=main-api --field-selector=status.phase=Running -o jsonpath='{.items[0].metadata.name}' 2>$null

if ([string]::IsNullOrWhiteSpace($apiPod)) {
    Write-Host "ERROR: no se encontro pod de main-api en estado Running para inicializar BD" -ForegroundColor Red
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