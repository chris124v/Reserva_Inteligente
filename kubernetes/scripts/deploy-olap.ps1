# deploy-olap.ps1 - Despliega HDFS + Hive + Spark e inicializa el esquema estrella

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  Reserva Inteligente - OLAP + Spark Deploy  " -ForegroundColor Cyan
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

$scriptPath    = Split-Path -Parent $MyInvocation.MyCommand.Path
$kubernetesPath = Split-Path -Parent $scriptPath
$projectRoot   = Split-Path -Parent $kubernetesPath
Set-Location $kubernetesPath

# ── HDFS ─────────────────────────────────────────────────────────────────────

Write-Host "[1/6] Desplegando HDFS NameNode..." -ForegroundColor Yellow
kubectl apply -f olap/hdfs/namenode-statefulset.yaml
kubectl apply -f olap/hdfs/namenode-service.yaml
Write-Host "  Esperando que NameNode este listo..." -ForegroundColor Cyan
kubectl wait --for=condition=ready pod -l app=hdfs-namenode -n reservainteligente --timeout=180s
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: NameNode no levanto en tiempo. Revisa los logs:" -ForegroundColor Red
    Write-Host "  kubectl logs -l app=hdfs-namenode -n reservainteligente" -ForegroundColor Yellow
    exit 1
}
Write-Host "OK NameNode listo (RPC en puerto 8020)" -ForegroundColor Green
Write-Host ""

Write-Host "[2/6] Desplegando HDFS DataNode..." -ForegroundColor Yellow
kubectl apply -f olap/hdfs/datanode-statefulset.yaml
kubectl apply -f olap/hdfs/datanode-service.yaml
Write-Host "  Esperando que DataNode este listo..." -ForegroundColor Cyan
kubectl wait --for=condition=ready pod -l app=hdfs-datanode -n reservainteligente --timeout=180s
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: DataNode no levanto en tiempo. Revisa los logs:" -ForegroundColor Red
    Write-Host "  kubectl logs -l app=hdfs-datanode -n reservainteligente" -ForegroundColor Yellow
    exit 1
}
Write-Host "OK DataNode listo y registrado con NameNode" -ForegroundColor Green
Write-Host ""

# ── Hive ──────────────────────────────────────────────────────────────────────

Write-Host "[3/6] Desplegando Hive (ConfigMap + Metastore DB + Metastore + HiveServer2)..." -ForegroundColor Yellow

Write-Host "  ConfigMap de Hive (core-site + hive-site)..." -ForegroundColor Cyan
kubectl apply -f olap/hive/hive-configmap.yaml

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

Write-Host "  Hive Metastore (incluye init schema, primera vez tarda ~2 min)..." -ForegroundColor Cyan
kubectl apply -f olap/hive/metastore-deployment.yaml
kubectl apply -f olap/hive/metastore-service.yaml
kubectl wait --for=condition=ready pod -l app=hive-metastore -n reservainteligente --timeout=300s
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Hive Metastore no levanto. Revisa:" -ForegroundColor Red
    Write-Host "  kubectl logs -l app=hive-metastore -n reservainteligente -c init-schema" -ForegroundColor Yellow
    Write-Host "  kubectl logs -l app=hive-metastore -n reservainteligente -c hive-metastore" -ForegroundColor Yellow
    exit 1
}
Write-Host "  OK Hive Metastore listo en puerto 9083" -ForegroundColor Green

Write-Host "  HiveServer2..." -ForegroundColor Cyan
kubectl apply -f olap/hive/hiveserver2-deployment.yaml
kubectl apply -f olap/hive/hiveserver2-service.yaml
kubectl wait --for=condition=ready pod -l app=hiveserver2 -n reservainteligente --timeout=300s
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: HiveServer2 no levanto. Revisa:" -ForegroundColor Red
    Write-Host "  kubectl logs -l app=hiveserver2 -n reservainteligente" -ForegroundColor Yellow
    exit 1
}
Write-Host "  OK HiveServer2 listo en puerto 10000" -ForegroundColor Green
Write-Host ""

# ── Spark ─────────────────────────────────────────────────────────────────────

Write-Host "[4/6] Desplegando Apache Spark (Master + Worker)..." -ForegroundColor Yellow
kubectl apply -f olap/spark/spark-services.yaml
kubectl apply -f olap/spark/spark-master-deployment.yaml
kubectl apply -f olap/spark/spark-worker-deployment.yaml

Write-Host "  Esperando que Spark Master este listo..." -ForegroundColor Cyan
kubectl wait --for=condition=ready pod -l app=spark-master -n reservainteligente --timeout=120s
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Spark Master no levanto. Revisa:" -ForegroundColor Red
    Write-Host "  kubectl logs -l app=spark-master -n reservainteligente" -ForegroundColor Yellow
    exit 1
}
Write-Host "  OK Spark Master listo en puerto 7077" -ForegroundColor Green

Write-Host "  Esperando que Spark Worker este listo..." -ForegroundColor Cyan
kubectl wait --for=condition=ready pod -l app=spark-worker -n reservainteligente --timeout=120s
if ($LASTEXITCODE -ne 0) {
    Write-Host "ADVERTENCIA: Spark Worker no levanto en tiempo (no bloquea el deploy)" -ForegroundColor Yellow
    Write-Host "  kubectl logs -l app=spark-worker -n reservainteligente" -ForegroundColor Yellow
} else {
    Write-Host "  OK Spark Worker listo y registrado con el Master" -ForegroundColor Green
}
Write-Host ""

# ── Esquema estrella ──────────────────────────────────────────────────────────

Write-Host "[5/6] Inicializando esquema estrella en Hive..." -ForegroundColor Yellow

$schemaFile = Join-Path $projectRoot "olap\hive\schema_estrella.hql"
if (-not (Test-Path $schemaFile)) {
    Write-Host "ERROR: no se encuentra $schemaFile" -ForegroundColor Red
    exit 1
}

$hivePod = kubectl get pods -n reservainteligente -l app=hiveserver2 `
    --field-selector=status.phase=Running `
    -o jsonpath='{.items[0].metadata.name}' 2>$null

if ([string]::IsNullOrWhiteSpace($hivePod)) {
    Write-Host "ERROR: no hay pod de hiveserver2 en Running" -ForegroundColor Red
    exit 1
}

Write-Host "  Copiando schema_estrella.hql al pod $hivePod..." -ForegroundColor Cyan
kubectl cp $schemaFile "reservainteligente/${hivePod}:/tmp/schema_estrella.hql"

Write-Host "  Ejecutando DDL (CREATE DATABASE + tablas + vistas)..." -ForegroundColor Cyan
kubectl exec -n reservainteligente $hivePod -- `
    /opt/hive/bin/hive -f /tmp/schema_estrella.hql 2>&1 | Out-Null

if ($LASTEXITCODE -ne 0) {
    Write-Host "ADVERTENCIA: el schema pudo haber fallado parcialmente." -ForegroundColor Yellow
    Write-Host "  Verifica con: kubectl exec -n reservainteligente $hivePod -- /opt/hive/bin/hive -e 'USE reserva_dw; SHOW TABLES;'" -ForegroundColor DarkGray
} else {
    Write-Host "  OK Esquema estrella inicializado (reserva_dw)" -ForegroundColor Green
}
Write-Host ""

# ── Seed PostgreSQL operacional ───────────────────────────────────────────────

Write-Host "[6/6] Aplicando seed a PostgreSQL operacional..." -ForegroundColor Yellow

$seedFile = Join-Path $projectRoot "data\seeds\postgres_seed.sql"
if (-not (Test-Path $seedFile)) {
    Write-Host "  ADVERTENCIA: no se encuentra $seedFile — omitiendo seed" -ForegroundColor Yellow
} else {
    $pgPod = kubectl get pods -n reservainteligente -l app=postgres `
        --field-selector=status.phase=Running `
        -o jsonpath='{.items[0].metadata.name}' 2>$null

    if ([string]::IsNullOrWhiteSpace($pgPod)) {
        Write-Host "  ADVERTENCIA: PostgreSQL no esta corriendo — omitiendo seed" -ForegroundColor Yellow
        Write-Host "  Ejecuta deploy-all.ps1 primero para levantar el stack operacional" -ForegroundColor DarkGray
    } else {
        kubectl cp $seedFile "reservainteligente/${pgPod}:/tmp/postgres_seed.sql"
        kubectl exec -n reservainteligente $pgPod -- `
            psql -U postgres -d restaurantes_db -f /tmp/postgres_seed.sql 2>&1 | Out-Null
        if ($LASTEXITCODE -ne 0) {
            Write-Host "  ADVERTENCIA: seed pudo haber fallado (puede ser normal si ya hay datos)" -ForegroundColor Yellow
        } else {
            Write-Host "  OK Seed aplicado (5 users, 7 restaurants, 28 menus, 9 reservas, 12 orders)" -ForegroundColor Green
        }
    }
}
Write-Host ""

# ── Resumen ───────────────────────────────────────────────────────────────────

Write-Host "============================================" -ForegroundColor Green
Write-Host "  OLAP + Spark desplegados correctamente!  " -ForegroundColor Green
Write-Host "============================================" -ForegroundColor Green
Write-Host ""
Write-Host "Endpoints disponibles (con port-forward):" -ForegroundColor Cyan
Write-Host "  HDFS Web UI:       http://localhost:9870" -ForegroundColor White
Write-Host "    kubectl port-forward -n reservainteligente svc/hdfs-namenode 9870:9870" -ForegroundColor DarkGray
Write-Host "  HiveServer2 JDBC:  jdbc:hive2://localhost:10000" -ForegroundColor White
Write-Host "    kubectl port-forward -n reservainteligente svc/hiveserver2 10000:10000" -ForegroundColor DarkGray
Write-Host "  HiveServer2 UI:    http://localhost:10002" -ForegroundColor White
Write-Host "    kubectl port-forward -n reservainteligente svc/hiveserver2 10002:10002" -ForegroundColor DarkGray
Write-Host "  Spark Master UI:   http://localhost:8080" -ForegroundColor White
Write-Host "    kubectl port-forward -n reservainteligente svc/spark-master 8080:8080" -ForegroundColor DarkGray
Write-Host ""
Write-Host "Verificar estado de todos los pods OLAP + Spark:" -ForegroundColor Cyan
Write-Host "  kubectl get pods -n reservainteligente -l 'app in (hdfs-namenode,hdfs-datanode,hive-metastore-db,hive-metastore,hiveserver2,spark-master,spark-worker)'" -ForegroundColor DarkGray
Write-Host ""
Write-Host "Ejecutar analisis Spark manualmente:" -ForegroundColor Cyan
Write-Host "  `$pod = kubectl get pods -n reservainteligente -l app=spark-master -o jsonpath='{.items[0].metadata.name}'" -ForegroundColor DarkGray
Write-Host "  kubectl cp olap/spark/tendencias_consumo.py reservainteligente/`$pod:/tmp/" -ForegroundColor DarkGray
Write-Host "  kubectl exec -n reservainteligente `$pod -- bash -c 'PYSPARK_PYTHON=python3 PYSPARK_DRIVER_PYTHON=python3 /spark/bin/spark-submit --master local[*] --packages org.postgresql:postgresql:42.7.1 /tmp/tendencias_consumo.py'" -ForegroundColor DarkGray
Write-Host ""
