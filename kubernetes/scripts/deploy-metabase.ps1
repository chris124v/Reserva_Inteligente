# deploy-metabase.ps1 - Despliega Metabase (visualizacion / dashboards del Req 3)

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  Reserva Inteligente - Metabase Deploy      " -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

if (-not (Get-Command kubectl -ErrorAction SilentlyContinue)) {
    Write-Host "ERROR: kubectl no instalado" -ForegroundColor Red
    exit 1
}

kubectl cluster-info --request-timeout=5s 2>&1 | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Kubernetes no esta corriendo" -ForegroundColor Red
    exit 1
}

$scriptPath     = Split-Path -Parent $MyInvocation.MyCommand.Path
$kubernetesPath = Split-Path -Parent $scriptPath
Set-Location $kubernetesPath

Write-Host "[1/2] Aplicando PV/PVC, Deployment y Service de Metabase..." -ForegroundColor Yellow
kubectl apply -f olap/metabase/metabase-pv-pvc.yaml
kubectl apply -f olap/metabase/metabase-deployment.yaml
kubectl apply -f olap/metabase/metabase-service.yaml
Write-Host "OK Manifests aplicados" -ForegroundColor Green
Write-Host ""

Write-Host "[2/2] Esperando que Metabase este listo (arranque ~1-3 min)..." -ForegroundColor Yellow
kubectl wait --for=condition=available deployment/metabase -n reservainteligente --timeout=300s
if ($LASTEXITCODE -ne 0) {
    Write-Host "ADVERTENCIA: Metabase no levanto en tiempo (no bloquea el deploy)" -ForegroundColor Yellow
    Write-Host "  kubectl logs -l app=metabase -n reservainteligente" -ForegroundColor Yellow
} else {
    Write-Host "OK Metabase listo en puerto 3000" -ForegroundColor Green
}
Write-Host ""

Write-Host "============================================" -ForegroundColor Green
Write-Host "  Metabase desplegado!                       " -ForegroundColor Green
Write-Host "============================================" -ForegroundColor Green
Write-Host ""
Write-Host "UI de Metabase (con port-forward):" -ForegroundColor Cyan
Write-Host "  kubectl port-forward -n reservainteligente svc/metabase 3000:3000" -ForegroundColor DarkGray
Write-Host "  http://localhost:3000" -ForegroundColor White
Write-Host ""
Write-Host "Configuracion inicial (primera vez en la UI):" -ForegroundColor Cyan
Write-Host "  1. Crear usuario admin" -ForegroundColor DarkGray
Write-Host "  2. Conectar base de datos PostgreSQL:" -ForegroundColor DarkGray
Write-Host "       Host: postgres-service   Puerto: 5432" -ForegroundColor DarkGray
Write-Host "       BD: restaurantes_db      Usuario: postgres" -ForegroundColor DarkGray
Write-Host "  3. Construir 3 dashboards sobre las tablas:" -ForegroundColor DarkGray
Write-Host "       analytics_ingresos_mes_categoria   (Ingresos por mes y categoria)" -ForegroundColor DarkGray
Write-Host "       analytics_actividad_zona           (Actividad por zona)" -ForegroundColor DarkGray
Write-Host "       analytics_pedidos_estado           (Completados vs cancelados)" -ForegroundColor DarkGray
Write-Host ""
Write-Host "  Nota: estas tablas las genera el DAG de Airflow (tarea materializar_vistas_metabase)." -ForegroundColor DarkGray
Write-Host "  Si no existen aun, dispara el DAG: kubectl exec -n reservainteligente deploy/airflow-scheduler -- airflow dags trigger etl_reserva_dw" -ForegroundColor DarkGray
Write-Host ""
