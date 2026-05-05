# cleanup-all.ps1 - Detiene los workloads sin borrar PVC/PV

Write-Host "=====================================" -ForegroundColor Red
Write-Host "  Reserva Inteligente - Stop Script  " -ForegroundColor Red
Write-Host "=====================================" -ForegroundColor Red
Write-Host ""
Write-Host "ADVERTENCIA: Esto detendra los workloads y conservara namespace/PVC/PV" -ForegroundColor Yellow
Write-Host ""

$confirmation = Read-Host "Estas seguro? (escribe SI para detener los workloads)"

if ($confirmation -ne "SI") {
    Write-Host "Operacion cancelada." -ForegroundColor Green
    exit 0
}

Write-Host ""
Write-Host "Iniciando detencion..." -ForegroundColor Red
Write-Host ""

if (-not (Get-Command kubectl -ErrorAction SilentlyContinue)) {
    Write-Host "ERROR: kubectl no instalado" -ForegroundColor Red
    exit 1
}

function Stop-Workload {
    param(
        [string]$Kind,
        [string]$Name
    )

    $resource = kubectl get $Kind $Name -n reservainteligente --ignore-not-found=true 2>$null
    if ($LASTEXITCODE -eq 0 -and $resource) {
        kubectl scale "$Kind/$Name" -n reservainteligente --replicas=0 | Out-Null
        Write-Host "  OK $Kind/$Name escalado a 0" -ForegroundColor Green
    } else {
        Write-Host "  Omitiendo $Kind/$Name" -ForegroundColor DarkGray
    }
}

$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
$kubernetesPath = Split-Path -Parent $scriptPath
Set-Location $kubernetesPath

Write-Host "[1/4] Deteniendo workloads..." -ForegroundColor Yellow
Stop-Workload -Kind deployment -Name main-api
Stop-Workload -Kind deployment -Name mongos
Stop-Workload -Kind statefulset -Name mongo-configsvr
Stop-Workload -Kind statefulset -Name mongors1
Stop-Workload -Kind statefulset -Name postgres
Stop-Workload -Kind deployment -Name redis
Write-Host "OK Workloads detenidos" -ForegroundColor Green
Write-Host ""

Write-Host "[2/4] Limpiando job de inicializacion..." -ForegroundColor Yellow
kubectl delete job mongo-init -n reservainteligente --ignore-not-found=true
Write-Host "OK Job eliminado" -ForegroundColor Green
Write-Host ""

Write-Host "[3/4] Esperando..." -ForegroundColor Yellow
Start-Sleep -Seconds 5
Write-Host "OK" -ForegroundColor Green
Write-Host ""

Write-Host "[4/4] Conservando namespace y volumenes persistentes" -ForegroundColor Yellow
Write-Host "OK namespace reservainteligente y PVC/PV se mantienen" -ForegroundColor Green
Write-Host ""

Write-Host "=====================================" -ForegroundColor Green
Write-Host "  Workloads detenidos!" -ForegroundColor Green
Write-Host "=====================================" -ForegroundColor Green
Write-Host ""
Write-Host "Para volver a levantar: .\deploy-all.ps1" -ForegroundColor Cyan
Write-Host ""
