# status.ps1 - Verifica el estado del ambiente de Reserva Inteligente en Kubernetes

Write-Host "=====================================" -ForegroundColor Cyan
Write-Host "  Reserva Inteligente - Status Check  " -ForegroundColor Cyan
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host ""

if (-not (Get-Command kubectl -ErrorAction SilentlyContinue)) {
    Write-Host "ERROR: kubectl no instalado" -ForegroundColor Red
    exit 1
}

Write-Host "[1/8] Estado del cluster..." -ForegroundColor Yellow
kubectl cluster-info --request-timeout=5s 2>&1 | Out-Null
if ($LASTEXITCODE -eq 0) {
    Write-Host "  OK Kubernetes corriendo" -ForegroundColor Green
} else {
    Write-Host "  X Kubernetes NO corriendo" -ForegroundColor Red
    exit 1
}
Write-Host ""

Write-Host "[2/8] Namespace..." -ForegroundColor Yellow
$ns = kubectl get namespace reservainteligente --ignore-not-found=true 2>$null
if ($ns) {
    Write-Host "  OK reservainteligente existe" -ForegroundColor Green
} else {
    Write-Host "  X reservainteligente no existe" -ForegroundColor Red
}
Write-Host ""

# Helper: comprueba si un deployment/statefulset tiene al menos 1 pod Ready
function Get-WorkloadStatus {
    param([string]$Kind, [string]$Name)
    $ready = kubectl get $Kind $Name -n reservainteligente --ignore-not-found=true -o jsonpath="{.status.readyReplicas}" 2>$null
    if ([string]::IsNullOrWhiteSpace($ready) -or $ready -eq "0") { return "X" }
    return "OK"
}

Write-Host "[3/8] Stack operacional..." -ForegroundColor Yellow
$checks = @(
    @{kind="deployment"; name="main-api";       label="API"},
    @{kind="deployment"; name="search-service"; label="Search Service"},
    @{kind="deployment"; name="nginx-balancer"; label="Nginx"},
    @{kind="statefulset"; name="postgres";       label="PostgreSQL"},
    @{kind="deployment"; name="redis";           label="Redis"},
    @{kind="statefulset"; name="elasticsearch";  label="Elasticsearch"},
    @{kind="statefulset"; name="mongo-configsvr";label="MongoDB Config"},
    @{kind="statefulset"; name="mongors1";        label="MongoDB Shard"},
    @{kind="deployment"; name="mongos";          label="MongoDB Mongos"}
)
foreach ($c in $checks) {
    $status = Get-WorkloadStatus -Kind $c.kind -Name $c.name
    if ($status -eq "OK") {
        Write-Host "  OK $($c.label)" -ForegroundColor Green
    } else {
        Write-Host "  X  $($c.label)" -ForegroundColor Red
    }
}
Write-Host ""

Write-Host "[4/8] HDFS..." -ForegroundColor Yellow
$nnStatus = Get-WorkloadStatus -Kind statefulset -Name hdfs-namenode
$dnStatus = Get-WorkloadStatus -Kind statefulset -Name hdfs-datanode
if ($nnStatus -eq "OK") { Write-Host "  OK NameNode (RPC :8020, UI :9870)" -ForegroundColor Green } else { Write-Host "  X  NameNode" -ForegroundColor Red }
if ($dnStatus -eq "OK") { Write-Host "  OK DataNode" -ForegroundColor Green } else { Write-Host "  X  DataNode" -ForegroundColor Red }
Write-Host ""

Write-Host "[5/8] Hive..." -ForegroundColor Yellow
$msdbStatus = Get-WorkloadStatus -Kind statefulset -Name hive-metastore-db
$msStatus   = Get-WorkloadStatus -Kind deployment  -Name hive-metastore
$hs2Status  = Get-WorkloadStatus -Kind deployment  -Name hiveserver2
if ($msdbStatus -eq "OK") { Write-Host "  OK Metastore DB (PostgreSQL)" -ForegroundColor Green } else { Write-Host "  X  Metastore DB" -ForegroundColor Red }
if ($msStatus   -eq "OK") { Write-Host "  OK Hive Metastore (:9083)" -ForegroundColor Green }   else { Write-Host "  X  Hive Metastore" -ForegroundColor Red }
if ($hs2Status  -eq "OK") { Write-Host "  OK HiveServer2 (:10000 JDBC, :10002 UI)" -ForegroundColor Green } else { Write-Host "  X  HiveServer2" -ForegroundColor Red }

if ($hs2Status -eq "OK") {
    $hivePod = kubectl get pods -n reservainteligente -l app=hiveserver2 --field-selector=status.phase=Running -o jsonpath="{.items[0].metadata.name}" 2>$null
    if (-not [string]::IsNullOrWhiteSpace($hivePod)) {
        $tables = kubectl exec -n reservainteligente $hivePod -- /opt/hive/bin/hive -e "USE reserva_dw; SHOW TABLES;" 2>$null
        $tableCount = ($tables -split "`n" | Where-Object { $_ -match "^\w" }).Count
        if ($tableCount -gt 0) {
            Write-Host "  OK reserva_dw: $tableCount tablas/vistas" -ForegroundColor Green
        } else {
            Write-Host "  X  reserva_dw vacia (corre deploy-olap.ps1 para inicializar)" -ForegroundColor Yellow
        }
    }
}
Write-Host ""

Write-Host "[6/8] Spark..." -ForegroundColor Yellow
$smStatus = Get-WorkloadStatus -Kind deployment -Name spark-master
$swStatus = Get-WorkloadStatus -Kind deployment -Name spark-worker
if ($smStatus -eq "OK") { Write-Host "  OK Spark Master (:7077 cluster, :8080 UI)" -ForegroundColor Green } else { Write-Host "  X  Spark Master" -ForegroundColor Red }
if ($swStatus -eq "OK") { Write-Host "  OK Spark Worker" -ForegroundColor Green }                          else { Write-Host "  X  Spark Worker" -ForegroundColor Red }

if ($smStatus -eq "OK") {
    $pgPod = kubectl get pods -n reservainteligente -l app=postgres --field-selector=status.phase=Running -o jsonpath="{.items[0].metadata.name}" 2>$null
    if (-not [string]::IsNullOrWhiteSpace($pgPod)) {
        $analytics = kubectl exec -n reservainteligente $pgPod -- psql -U postgres -d restaurantes_db -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_name LIKE 'analytics_%';" 2>$null
        $analyticsCount = ($analytics -replace '\s','')
        if ($analyticsCount -gt 0) {
            Write-Host "  OK $analyticsCount tablas analytics en PostgreSQL" -ForegroundColor Green
        } else {
            Write-Host "  - Tablas analytics no encontradas (ejecuta los scripts Spark)" -ForegroundColor DarkGray
        }
    }
}
Write-Host ""

Write-Host "[7/8] Airflow..." -ForegroundColor Yellow
$apgStatus = Get-WorkloadStatus -Kind statefulset -Name airflow-postgres
$aschStatus = Get-WorkloadStatus -Kind deployment  -Name airflow-scheduler
$awebStatus = Get-WorkloadStatus -Kind deployment  -Name airflow-webserver
if ($apgStatus  -eq "OK") { Write-Host "  OK Metadata DB (PostgreSQL)" -ForegroundColor Green } else { Write-Host "  X  Metadata DB" -ForegroundColor Red }
if ($aschStatus -eq "OK") { Write-Host "  OK Scheduler (LocalExecutor)" -ForegroundColor Green } else { Write-Host "  X  Scheduler" -ForegroundColor Red }
if ($awebStatus -eq "OK") { Write-Host "  OK Webserver (:8080)" -ForegroundColor Green }          else { Write-Host "  X  Webserver" -ForegroundColor Red }

$initJobStatus = kubectl get job airflow-init -n reservainteligente --ignore-not-found=true -o jsonpath="{.status.succeeded}" 2>$null
if ($initJobStatus -eq "1") {
    Write-Host "  OK airflow-init completado (db migrate + usuario admin)" -ForegroundColor Green
} else {
    Write-Host "  - airflow-init no completado todavia" -ForegroundColor DarkGray
}
Write-Host ""

Write-Host "[8/8] Persistencia (PVC)..." -ForegroundColor Yellow
kubectl get pvc -n reservainteligente
Write-Host ""

Write-Host "=====================================" -ForegroundColor Cyan
Write-Host "  Port-forwards disponibles:         " -ForegroundColor Cyan
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host "  API:            kubectl port-forward svc/api-service 8000:80 -n reservainteligente" -ForegroundColor White
Write-Host "  Search:         kubectl port-forward svc/search-service 8001:80 -n reservainteligente" -ForegroundColor White
Write-Host "  Nginx:          kubectl port-forward svc/nginx-service 8080:80 -n reservainteligente" -ForegroundColor White
Write-Host "  Elasticsearch:  kubectl port-forward svc/elasticsearch 9200:9200 -n reservainteligente" -ForegroundColor White
Write-Host "  HDFS UI:        kubectl port-forward svc/hdfs-namenode 9870:9870 -n reservainteligente" -ForegroundColor White
Write-Host "  HiveServer2 UI: kubectl port-forward svc/hiveserver2 10002:10002 -n reservainteligente" -ForegroundColor White
Write-Host "  Spark Master UI:kubectl port-forward svc/spark-master 8080:8080 -n reservainteligente" -ForegroundColor White
Write-Host "  Airflow UI:     kubectl port-forward svc/airflow-webserver 8080:8080 -n reservainteligente" -ForegroundColor White
Write-Host ""
Write-Host "Listo!" -ForegroundColor Green
Write-Host ""
