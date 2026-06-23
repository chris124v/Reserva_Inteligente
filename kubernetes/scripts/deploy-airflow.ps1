# deploy-airflow.ps1 - Despliega Apache Airflow (LocalExecutor) y el DAG etl_reserva_dw

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  Reserva Inteligente - Airflow Deploy       " -ForegroundColor Cyan
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

# ── Configuracion ────────────────────────────────────────────────────────────

Write-Host "[1/5] Aplicando ConfigMap y Secret de Airflow..." -ForegroundColor Yellow
kubectl apply -f olap/airflow/airflow-configmap.yaml
kubectl apply -f olap/airflow/airflow-secret.yaml
Write-Host "OK Configuracion aplicada" -ForegroundColor Green
Write-Host ""

# ── PostgreSQL de metadatos ──────────────────────────────────────────────────

Write-Host "[2/5] Desplegando PostgreSQL de metadatos de Airflow..." -ForegroundColor Yellow
kubectl apply -f olap/airflow/airflow-postgres-statefulset.yaml
kubectl apply -f olap/airflow/airflow-postgres-service.yaml
kubectl wait --for=condition=ready pod -l app=airflow-postgres -n reservainteligente --timeout=120s
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: airflow-postgres no levanto. Revisa:" -ForegroundColor Red
    Write-Host "  kubectl logs -l app=airflow-postgres -n reservainteligente" -ForegroundColor Yellow
    exit 1
}
Write-Host "OK airflow-postgres listo" -ForegroundColor Green
Write-Host ""

# ── Inicializacion (db migrate + usuario admin) ──────────────────────────────

Write-Host "[3/5] Inicializando esquema de metadatos y usuario admin..." -ForegroundColor Yellow
kubectl delete job airflow-init -n reservainteligente --ignore-not-found 2>&1 | Out-Null
kubectl apply -f olap/airflow/airflow-init-job.yaml
kubectl wait --for=condition=complete job/airflow-init -n reservainteligente --timeout=300s
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: airflow-init no completo. Revisa:" -ForegroundColor Red
    Write-Host "  kubectl logs job/airflow-init -n reservainteligente" -ForegroundColor Yellow
    exit 1
}
Write-Host "OK Esquema de metadatos inicializado y usuario admin listo" -ForegroundColor Green
Write-Host ""

# ── Scheduler ─────────────────────────────────────────────────────────────────

Write-Host "[4/5] Desplegando Airflow Scheduler (LocalExecutor)..." -ForegroundColor Yellow
kubectl apply -f olap/airflow/airflow-scheduler-deployment.yaml
kubectl wait --for=condition=available deployment/airflow-scheduler -n reservainteligente --timeout=180s
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: airflow-scheduler no levanto. Revisa:" -ForegroundColor Red
    Write-Host "  kubectl logs -l app=airflow-scheduler -n reservainteligente" -ForegroundColor Yellow
    exit 1
}
Write-Host "OK Scheduler listo (ejecuta el DAG etl_reserva_dw diariamente)" -ForegroundColor Green
Write-Host ""

# ── Webserver ─────────────────────────────────────────────────────────────────

Write-Host "[5/5] Desplegando Airflow Webserver..." -ForegroundColor Yellow
kubectl apply -f olap/airflow/airflow-webserver-deployment.yaml
kubectl apply -f olap/airflow/airflow-webserver-service.yaml
kubectl wait --for=condition=available deployment/airflow-webserver -n reservainteligente --timeout=180s
if ($LASTEXITCODE -ne 0) {
    Write-Host "ADVERTENCIA: airflow-webserver no levanto en tiempo (no bloquea el deploy)" -ForegroundColor Yellow
    Write-Host "  kubectl logs -l app=airflow-webserver -n reservainteligente" -ForegroundColor Yellow
} else {
    Write-Host "OK Webserver listo en puerto 8080" -ForegroundColor Green
}
Write-Host ""

# ── Resumen ───────────────────────────────────────────────────────────────────

Write-Host "============================================" -ForegroundColor Green
Write-Host "  Airflow desplegado correctamente!         " -ForegroundColor Green
Write-Host "============================================" -ForegroundColor Green
Write-Host ""
Write-Host "UI de Airflow (con port-forward):" -ForegroundColor Cyan
Write-Host "  kubectl port-forward -n reservainteligente svc/airflow-webserver 8080:8080" -ForegroundColor DarkGray
Write-Host "  http://localhost:8080  (usuario/clave en airflow-secret.yaml)" -ForegroundColor White
Write-Host ""
Write-Host "Verificar estado de los pods de Airflow:" -ForegroundColor Cyan
Write-Host "  kubectl get pods -n reservainteligente -l 'app in (airflow-postgres,airflow-scheduler,airflow-webserver)'" -ForegroundColor DarkGray
Write-Host ""
Write-Host "Disparar el DAG manualmente sin esperar al schedule diario:" -ForegroundColor Cyan
Write-Host "  kubectl exec -n reservainteligente deploy/airflow-scheduler -- airflow dags trigger etl_reserva_dw" -ForegroundColor DarkGray
Write-Host ""
