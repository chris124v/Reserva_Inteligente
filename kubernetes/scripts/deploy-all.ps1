# deploy-all.ps1 - Crea y despliega todo el ambiente de Reserva Inteligente en Kubernetes

Write-Host "=====================================" -ForegroundColor Cyan
Write-Host "  Reserva Inteligente - Deployment Script  " -ForegroundColor Cyan
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host ""

if (-not (Get-Command kubectl -ErrorAction SilentlyContinue)) {
    Write-Host "ERROR: kubectl no instalado" -ForegroundColor Red
    exit 1
}

Write-Host "[1/5] Verificando Kubernetes..." -ForegroundColor Yellow
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

Write-Host "[2/5] Desplegando namespaces..." -ForegroundColor Yellow
kubectl apply -f namespace.yaml
Write-Host "OK Namespace creado" -ForegroundColor Green
Write-Host ""

Write-Host "[3/5] Desplegando configuracion..." -ForegroundColor Yellow
kubectl apply -f config/configmap.yaml
kubectl apply -f config/secret.yaml
Write-Host "OK Configuracion desplegada" -ForegroundColor Green
Write-Host ""

Write-Host "[4/6] Desplegando bases de datos..." -ForegroundColor Yellow
Write-Host "  PostgreSQL..." -ForegroundColor Cyan
kubectl apply -f databases/postgres/
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

Write-Host "[5/6] Esperando a que los pods esten listos..." -ForegroundColor Yellow
Start-Sleep -Seconds 10
kubectl wait --for=condition=ready pod -l app=postgres -n reservainteligente --timeout=300s 2>$null
kubectl apply -f api/main-api/
kubectl wait --for=condition=ready pod -l app=main-api -n reservainteligente --timeout=300s 2>$null

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

Write-Host "[6/6] Deployment completado!" -ForegroundColor Green
Write-Host ""
Write-Host "Conexiones disponibles:" -ForegroundColor Cyan
Write-Host "  API:        http://localhost:8000 (con port-forward)" -ForegroundColor White
Write-Host "  PostgreSQL: localhost:5432 (postgres/postgres)" -ForegroundColor White
Write-Host "  MongoDB:    localhost:27017" -ForegroundColor White
Write-Host ""
