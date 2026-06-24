# clean_up_ram.ps1 - Escala a 0 los componentes que NO usa el pipeline de
# Proyecto 2 (OLAP/Spark/Airflow/Neo4J/Metabase), para liberar RAM del nodo.
# No borra PVC/PV ni toca namespace/config; todo se puede volver a levantar
# escalando a 1 (o con deploy-all.ps1).
#
# Que se apaga y por que:
#   - spark-master / spark-worker: el cluster standalone de Spark nunca se usa.
#     Todos los spark-submit (manuales y del DAG de Airflow) corren con
#     --master local[*]; el DAG ejecuta Spark dentro del propio contenedor de
#     airflow-scheduler (que ya trae pyspark instalado). Nada se conecta a
#     spark://spark-master:7077.
#   - MongoDB (mongo-configsvr, mongors1, mongos): el ETL de Airflow lee
#     exclusivamente PostgreSQL (spark.read.jdbc en etl_dimensiones_hechos.py).
#     Ningun componente de OLAP/Spark/Neo4J/Airflow/Metabase toca Mongo.
#
# Que NO se toca (a proposito):
#   - redis: se mantiene siempre arriba (decision explicita del usuario).
#   - main-api, nginx-balancer, search-service, elasticsearch, postgres,
#     hdfs, hive, airflow, metabase, neo4j: son necesarios para el stack
#     operacional o para el pipeline de Proyecto 2 (Req 1, 3, 4, 5, 6).

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  Reserva Inteligente - Clean Up RAM        " -ForegroundColor Cyan
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
        Write-Host "  Omitiendo $Kind/$Name (no existe)" -ForegroundColor DarkGray
    }
}

Write-Host "[1/2] Apagando Spark standalone (master + worker, no usado por el pipeline)..." -ForegroundColor Yellow
Stop-Workload -Kind deployment -Name spark-master
Stop-Workload -Kind deployment -Name spark-worker
Write-Host ""

Write-Host "[2/2] Apagando MongoDB (configsvr + shard + mongos, no usado por el ETL)..." -ForegroundColor Yellow
Stop-Workload -Kind deployment  -Name mongos
Stop-Workload -Kind statefulset -Name mongo-configsvr
Stop-Workload -Kind statefulset -Name mongors1
Write-Host ""

Write-Host "============================================" -ForegroundColor Green
Write-Host "  RAM liberada!                              " -ForegroundColor Green
Write-Host "============================================" -ForegroundColor Green
Write-Host ""
Write-Host "Redis se mantiene activo a proposito (no se toca)." -ForegroundColor Cyan
Write-Host ""
Write-Host "Para volver a levantar estos componentes:" -ForegroundColor Cyan
Write-Host "  kubectl scale deployment/spark-master deployment/spark-worker --replicas=1 -n reservainteligente" -ForegroundColor DarkGray
Write-Host "  kubectl scale statefulset/mongo-configsvr statefulset/mongors1 --replicas=1 -n reservainteligente" -ForegroundColor DarkGray
Write-Host "  kubectl scale deployment/mongos --replicas=1 -n reservainteligente" -ForegroundColor DarkGray
Write-Host "  (o corre .\deploy-all.ps1 para restaurar todo el stack operacional)" -ForegroundColor DarkGray
Write-Host ""
