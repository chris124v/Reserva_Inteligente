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

Write-Host "[4/5] Desplegando bases de datos..." -ForegroundColor Yellow
Write-Host "  PostgreSQL..." -ForegroundColor Cyan
kubectl apply -f databases/postgres/
Write-Host "  MongoDB..." -ForegroundColor Cyan
kubectl apply -f databases/mongodb/easy/
Write-Host "OK Bases de datos desplegadas" -ForegroundColor Green
Write-Host ""

Write-Host "[5/5] Esperando a que los pods esten listos..." -ForegroundColor Yellow
Start-Sleep -Seconds 10
kubectl wait --for=condition=ready pod -l app=postgres -n reservainteligente --timeout=300s 2>$null
kubectl wait --for=condition=ready pod -l app=mongo -n reservainteligente --timeout=300s 2>$null
kubectl apply -f api/main-api/
kubectl wait --for=condition=ready pod -l app=main-api -n reservainteligente --timeout=300s 2>$null
Write-Host "OK Todos los pods estan listos" -ForegroundColor Green
Write-Host ""

Write-Host "=====================================" -ForegroundColor Green
Write-Host "  Deployment completado!" -ForegroundColor Green
Write-Host "=====================================" -ForegroundColor Green
Write-Host ""
Write-Host "Conexiones disponibles:" -ForegroundColor Cyan
Write-Host "  API:        http://localhost:8000 (con port-forward)" -ForegroundColor White
Write-Host "  PostgreSQL: localhost:5432 (postgres/postgres)" -ForegroundColor White
Write-Host "  MongoDB:    localhost:27017" -ForegroundColor White
Write-Host ""
