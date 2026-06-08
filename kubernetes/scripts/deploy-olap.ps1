# deploy-olap.ps1 - Despliega la infraestructura OLAP (HDFS + Hive) en Kubernetes

Write-Host "=====================================" -ForegroundColor Cyan
Write-Host "  Reserva Inteligente - OLAP Deploy  " -ForegroundColor Cyan
Write-Host "=====================================" -ForegroundColor Cyan
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

$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
$kubernetesPath = Split-Path -Parent $scriptPath
Set-Location $kubernetesPath

# ── HDFS ─────────────────────────────────────────────────────────────────────

Write-Host "[1/4] Desplegando HDFS NameNode..." -ForegroundColor Yellow
kubectl apply -f olap/hdfs/namenode-statefulset.yaml
kubectl apply -f olap/hdfs/namenode-service.yaml
Write-Host "  Esperando que NameNode este listo..." -ForegroundColor Cyan
kubectl wait --for=condition=ready pod -l app=hdfs-namenode -n reservainteligente --timeout=180s
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: NameNode no levanto en tiempo. Revisa los logs:" -ForegroundColor Red
    Write-Host "  kubectl logs -l app=hdfs-namenode -n reservainteligente" -ForegroundColor Yellow
    exit 1
}
Write-Host "OK NameNode listo" -ForegroundColor Green
Write-Host ""

Write-Host "[2/4] Desplegando HDFS DataNode..." -ForegroundColor Yellow
kubectl apply -f olap/hdfs/datanode-statefulset.yaml
kubectl apply -f olap/hdfs/datanode-service.yaml
Write-Host "  Esperando que DataNode este listo..." -ForegroundColor Cyan
kubectl wait --for=condition=ready pod -l app=hdfs-datanode -n reservainteligente --timeout=180s
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: DataNode no levanto en tiempo. Revisa los logs:" -ForegroundColor Red
    Write-Host "  kubectl logs -l app=hdfs-datanode -n reservainteligente" -ForegroundColor Yellow
    exit 1
}
Write-Host "OK DataNode listo" -ForegroundColor Green
Write-Host ""

# ── Hive Metastore DB ─────────────────────────────────────────────────────────

Write-Host "[3/4] Desplegando Hive Metastore (PostgreSQL + Metastore + HiveServer2)..." -ForegroundColor Yellow

Write-Host "  PostgreSQL del Metastore..." -ForegroundColor Cyan
kubectl apply -f olap/hive/metastore-postgres-statefulset.yaml
kubectl apply -f olap/hive/metastore-postgres-service.yaml
kubectl wait --for=condition=ready pod -l app=hive-metastore-db -n reservainteligente --timeout=120s
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: PostgreSQL del Metastore no levanto. Revisa:" -ForegroundColor Red
    Write-Host "  kubectl logs -l app=hive-metastore-db -n reservainteligente" -ForegroundColor Yellow
    exit 1
}
Write-Host "  OK PostgreSQL del Metastore listo" -ForegroundColor Green

Write-Host "  Hive Metastore (incluye init schema)..." -ForegroundColor Cyan
kubectl apply -f olap/hive/metastore-deployment.yaml
kubectl apply -f olap/hive/metastore-service.yaml
Write-Host "  Esperando init del schema (puede tardar ~2 min la primera vez)..." -ForegroundColor Cyan
kubectl wait --for=condition=ready pod -l app=hive-metastore -n reservainteligente --timeout=300s
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Hive Metastore no levanto. Revisa:" -ForegroundColor Red
    Write-Host "  kubectl logs -l app=hive-metastore -n reservainteligente -c init-schema" -ForegroundColor Yellow
    Write-Host "  kubectl logs -l app=hive-metastore -n reservainteligente -c hive-metastore" -ForegroundColor Yellow
    exit 1
}
Write-Host "  OK Hive Metastore listo" -ForegroundColor Green

# ── HiveServer2 ───────────────────────────────────────────────────────────────

Write-Host "[4/4] Desplegando HiveServer2..." -ForegroundColor Yellow
kubectl apply -f olap/hive/hiveserver2-deployment.yaml
kubectl apply -f olap/hive/hiveserver2-service.yaml
kubectl wait --for=condition=ready pod -l app=hiveserver2 -n reservainteligente --timeout=300s
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: HiveServer2 no levanto. Revisa:" -ForegroundColor Red
    Write-Host "  kubectl logs -l app=hiveserver2 -n reservainteligente" -ForegroundColor Yellow
    exit 1
}
Write-Host "OK HiveServer2 listo" -ForegroundColor Green
Write-Host ""

Write-Host "=====================================" -ForegroundColor Green
Write-Host "  OLAP Stack desplegado correctamente  " -ForegroundColor Green
Write-Host "=====================================" -ForegroundColor Green
Write-Host ""
Write-Host "Conexiones disponibles (con port-forward):" -ForegroundColor Cyan
Write-Host "  HDFS NameNode Web UI:  http://localhost:9870" -ForegroundColor White
Write-Host "    kubectl port-forward -n reservainteligente svc/hdfs-namenode 9870:9870" -ForegroundColor DarkGray
Write-Host "  HiveServer2 JDBC:      jdbc:hive2://localhost:10000" -ForegroundColor White
Write-Host "    kubectl port-forward -n reservainteligente svc/hiveserver2 10000:10000" -ForegroundColor DarkGray
Write-Host "  HiveServer2 Web UI:    http://localhost:10002" -ForegroundColor White
Write-Host "    kubectl port-forward -n reservainteligente svc/hiveserver2 10002:10002" -ForegroundColor DarkGray
Write-Host ""
Write-Host "Verificar estado de todos los pods OLAP:" -ForegroundColor Cyan
Write-Host "  kubectl get pods -n reservainteligente -l 'app in (hdfs-namenode,hdfs-datanode,hive-metastore-db,hive-metastore,hiveserver2)'" -ForegroundColor DarkGray
Write-Host ""
