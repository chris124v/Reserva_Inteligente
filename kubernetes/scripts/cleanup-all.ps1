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

Write-Host "[1/7] Deteniendo stack operacional..." -ForegroundColor Yellow
Stop-Workload -Kind deployment -Name main-api
Stop-Workload -Kind deployment -Name search-service
Stop-Workload -Kind deployment -Name nginx-balancer
Stop-Workload -Kind deployment -Name mongos
Stop-Workload -Kind statefulset -Name mongo-configsvr
Stop-Workload -Kind statefulset -Name mongors1
Stop-Workload -Kind statefulset -Name postgres
Stop-Workload -Kind deployment -Name redis
Stop-Workload -Kind statefulset -Name elasticsearch
Write-Host "OK Stack operacional detenido" -ForegroundColor Green
Write-Host ""

Write-Host "[2/7] Deteniendo Spark..." -ForegroundColor Yellow
Stop-Workload -Kind deployment -Name spark-master
Stop-Workload -Kind deployment -Name spark-worker
Write-Host "OK Spark detenido" -ForegroundColor Green
Write-Host ""

Write-Host "[3/7] Deteniendo Hive y HDFS..." -ForegroundColor Yellow
Stop-Workload -Kind deployment -Name hiveserver2
Stop-Workload -Kind deployment -Name hive-metastore
Stop-Workload -Kind statefulset -Name hive-metastore-db
Stop-Workload -Kind statefulset -Name hdfs-datanode
Stop-Workload -Kind statefulset -Name hdfs-namenode
Write-Host "OK Hive y HDFS detenidos" -ForegroundColor Green
Write-Host ""

Write-Host "[4/7] Deteniendo Airflow..." -ForegroundColor Yellow
Stop-Workload -Kind deployment -Name airflow-webserver
Stop-Workload -Kind deployment -Name airflow-scheduler
Stop-Workload -Kind statefulset -Name airflow-postgres
Write-Host "OK Airflow detenido" -ForegroundColor Green
Write-Host ""

Write-Host "[5/7] Deteniendo Metabase y Neo4J..." -ForegroundColor Yellow
Stop-Workload -Kind deployment -Name metabase
Stop-Workload -Kind statefulset -Name neo4j
Write-Host "OK Metabase y Neo4J detenidos" -ForegroundColor Green
Write-Host ""

Write-Host "[6/7] Limpiando jobs de inicializacion..." -ForegroundColor Yellow
kubectl delete job mongo-init -n reservainteligente --ignore-not-found=true
kubectl delete job airflow-init -n reservainteligente --ignore-not-found=true
Write-Host "OK Jobs eliminados" -ForegroundColor Green
Write-Host ""

Write-Host "[7/7] Conservando namespace y volumenes persistentes" -ForegroundColor Yellow
Write-Host "OK namespace reservainteligente y PVC/PV se mantienen" -ForegroundColor Green
Write-Host ""

Write-Host "=====================================" -ForegroundColor Green
Write-Host "  Workloads detenidos!" -ForegroundColor Green
Write-Host "=====================================" -ForegroundColor Green
Write-Host ""
Write-Host "Para volver a levantar el stack operacional: .\deploy-all.ps1" -ForegroundColor Cyan
Write-Host "Para volver a levantar OLAP + Spark:        .\deploy-olap.ps1" -ForegroundColor Cyan
Write-Host ""
