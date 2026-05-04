# cleanup-all.ps1 - Elimina y limpia todo 

Write-Host "=====================================" -ForegroundColor Red
Write-Host "  Reserva Inteligente - Cleanup Script  " -ForegroundColor Red
Write-Host "=====================================" -ForegroundColor Red
Write-Host ""
Write-Host "ADVERTENCIA: Esto eliminara TODOS los recursos de Reserva Inteligente" -ForegroundColor Yellow
Write-Host ""

$confirmation = Read-Host "Estas seguro? (escribe SI para confirmar)"

if ($confirmation -ne "SI") {
    Write-Host "Operacion cancelada." -ForegroundColor Green
    exit 0
}

Write-Host ""
Write-Host "Iniciando eliminacion..." -ForegroundColor Red
Write-Host ""

if (-not (Get-Command kubectl -ErrorAction SilentlyContinue)) {
    Write-Host "ERROR: kubectl no instalado" -ForegroundColor Red
    exit 1
}

$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
$kubernetesPath = Split-Path -Parent $scriptPath
Set-Location $kubernetesPath

Write-Host "[1/4] Eliminando API..." -ForegroundColor Yellow
kubectl delete -f api/main-api/ --ignore-not-found=true
Write-Host "OK API eliminada" -ForegroundColor Green
Write-Host ""

Write-Host "[2/4] Eliminando recursos de bases de datos..." -ForegroundColor Yellow
kubectl delete -f databases/postgres/ --ignore-not-found=true
kubectl delete -f databases/mongodb/easy/ --ignore-not-found=true
Write-Host "OK Recursos eliminados" -ForegroundColor Green
Write-Host ""

Write-Host "[3/4] Esperando..." -ForegroundColor Yellow
Start-Sleep -Seconds 10
Write-Host "OK" -ForegroundColor Green
Write-Host ""

Write-Host "[4/4] Eliminando namespace..." -ForegroundColor Yellow
kubectl delete -f namespace.yaml --ignore-not-found=true
Write-Host "OK Namespace eliminado" -ForegroundColor Green
Write-Host ""

Start-Sleep -Seconds 5

Write-Host "=====================================" -ForegroundColor Green
Write-Host "  Limpieza completada!" -ForegroundColor Green
Write-Host "=====================================" -ForegroundColor Green
Write-Host ""
Write-Host "Para redesplegar: .\deploy-all.ps1" -ForegroundColor Cyan
Write-Host ""
