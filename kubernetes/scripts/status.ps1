# status.ps1 - Verifica el estado del ambiente de Reserva Inteligente en Kubernetes

Write-Host "=====================================" -ForegroundColor Cyan
Write-Host "  Reserva Inteligente - Status Check  " -ForegroundColor Cyan
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host ""

if (-not (Get-Command kubectl -ErrorAction SilentlyContinue)) {
    Write-Host "ERROR: kubectl no instalado" -ForegroundColor Red
    exit 1
}

Write-Host "[1/5] Estado del cluster..." -ForegroundColor Yellow
kubectl cluster-info --request-timeout=5s 2>&1 | Out-Null
if ($LASTEXITCODE -eq 0) {
    Write-Host "OK Kubernetes corriendo" -ForegroundColor Green
} else {
    Write-Host "X Kubernetes NO corriendo" -ForegroundColor Red
    exit 1
}
Write-Host ""

Write-Host "[2/5] Verificando namespace..." -ForegroundColor Yellow
$ns = kubectl get namespace reservainteligente --ignore-not-found=true 2>$null
if ($ns) {
    Write-Host "  OK reservainteligente existe" -ForegroundColor Green
} else {
    Write-Host "  X reservainteligente no existe" -ForegroundColor Red
}
Write-Host ""

Write-Host "[3/5] Estado de los pods..." -ForegroundColor Yellow
kubectl get pods -n reservainteligente
Write-Host ""

Write-Host "[4/5] Servicios..." -ForegroundColor Yellow
Write-Host "  API:        http://localhost:8000 (necesita port-forward)" -ForegroundColor White
Write-Host "  PostgreSQL: localhost:5432" -ForegroundColor White
Write-Host "  MongoDB:    localhost:27017" -ForegroundColor White
Write-Host ""

Write-Host "[5/5] Persistencia..." -ForegroundColor Yellow
kubectl get pvc -n reservainteligente
Write-Host ""
kubectl get pv
Write-Host ""
Write-Host "PostgreSQL: user=postgres, pass=(revisar secret)" -ForegroundColor Gray
Write-Host "MongoDB:    usa mongos-service dentro del cluster o localhost:27017 con port-forward" -ForegroundColor Gray
Write-Host ""
Write-Host "Listo!" -ForegroundColor Green
Write-Host ""
