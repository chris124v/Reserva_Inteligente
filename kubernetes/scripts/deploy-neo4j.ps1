# deploy-neo4j.ps1
# Despliega Neo4J en Kubernetes con los manifiestos YAML y carga el grafo desde PostgreSQL.
#
# Modela el grafo de usuarios/productos/pedidos + zonas para los Req 5 y 6
# (analisis de grafos, co-compras, recomendaciones y rutas de entrega).
#
# Prerequisitos:
#   - deploy-all.ps1 ya ejecutado (PostgreSQL operacional con datos)
#   - pip install -r Neo4j\neo4j-requirements.txt  (neo4j, psycopg2-binary)
#   - databases/Neo4j/secret.yaml creado a partir de secret.example.yaml

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  Reserva Inteligente - Neo4J Deploy       " -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# ── Verificaciones previas ────────────────────────────────────────────────────

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
$projectRoot    = Split-Path -Parent $kubernetesPath
$neo4jManifests = Join-Path $kubernetesPath "databases\Neo4j"

# ── 1. Desplegar Neo4J (manifiestos YAML) ─────────────────────────────────────

Write-Host "[1/4] Desplegando Neo4J (Secret + ConfigMap + StatefulSet + Service)..." -ForegroundColor Yellow

$secretFile = Join-Path $neo4jManifests "secret.yaml"
if (-not (Test-Path $secretFile)) {
    Write-Host "ERROR: no existe $secretFile" -ForegroundColor Red
    Write-Host "  Copialo desde la plantilla y rellena el password:" -ForegroundColor Yellow
    Write-Host "  copy databases\Neo4j\secret.example.yaml databases\Neo4j\secret.yaml" -ForegroundColor DarkGray
    exit 1
}

kubectl apply -f "$secretFile"
kubectl apply -f (Join-Path $neo4jManifests "configmap.yaml")
kubectl apply -f (Join-Path $neo4jManifests "statefulset.yaml")
kubectl apply -f (Join-Path $neo4jManifests "service.yaml")
Write-Host "OK Manifiestos aplicados" -ForegroundColor Green
Write-Host ""

# ── 2. Esperar que Neo4J este listo ───────────────────────────────────────────

Write-Host "[2/4] Esperando que Neo4J este listo (~1 min, instala APOC)..." -ForegroundColor Yellow
kubectl rollout status statefulset/neo4j -n reservainteligente --timeout=300s
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Neo4J no levanto en tiempo. Revisa los logs:" -ForegroundColor Red
    Write-Host "  kubectl logs neo4j-0 -n reservainteligente -c neo4j" -ForegroundColor Yellow
    exit 1
}
Write-Host "OK Neo4J listo (Bolt :7687, Browser :7474)" -ForegroundColor Green
Write-Host ""

# ── 3. Extraer credenciales de los Secrets ───────────────────────────────────

Write-Host "[3/4] Leyendo credenciales de los Secrets..." -ForegroundColor Yellow

function Get-SecretValue($secretName, $key) {
    $b64 = kubectl get secret $secretName -n reservainteligente -o "jsonpath={.data.$key}" 2>$null
    if ([string]::IsNullOrWhiteSpace($b64)) { return $null }
    return [System.Text.Encoding]::UTF8.GetString([System.Convert]::FromBase64String($b64))
}

# NEO4J_AUTH tiene formato usuario/password
$neo4jAuth = Get-SecretValue "neo4j-secret" "NEO4J_AUTH"
$pgPassword = Get-SecretValue "app-secret" "DATABASE_PASSWORD"

if ([string]::IsNullOrWhiteSpace($neo4jAuth) -or [string]::IsNullOrWhiteSpace($pgPassword)) {
    Write-Host "ERROR: no se pudieron leer las credenciales de los Secrets" -ForegroundColor Red
    exit 1
}

$neo4jParts    = $neo4jAuth -split '/', 2
$env:NEO4J_USER     = $neo4jParts[0]
$env:NEO4J_PASSWORD = $neo4jParts[1]
$env:PG_PASSWORD    = $pgPassword
Write-Host "OK Credenciales cargadas en el entorno" -ForegroundColor Green
Write-Host ""

# ── 4. Cargar grafo desde PostgreSQL ─────────────────────────────────────────

Write-Host "[4/4] Cargando grafo desde PostgreSQL..." -ForegroundColor Yellow

$reqFile = Join-Path $projectRoot "Neo4j\neo4j-requirements.txt"
if (Test-Path $reqFile) {
    Write-Host "  Instalando dependencias Python..." -ForegroundColor Cyan
    pip install -r $reqFile -q
}

$seedFile = Join-Path $projectRoot "Neo4j\seed_neo4j.py"
if (-not (Test-Path $seedFile)) {
    Write-Host "  ADVERTENCIA: no se encuentra $seedFile, omitiendo seed" -ForegroundColor Yellow
} else {
    Write-Host "  Abriendo port-forwards temporales (neo4j-service 7687, postgres-service 5432)..." -ForegroundColor Cyan
    $pfNeo4j = Start-Job { kubectl port-forward svc/neo4j-service 7687:7687 -n reservainteligente }
    $pfPg    = Start-Job { kubectl port-forward svc/postgres-service 5432:5432 -n reservainteligente }
    Start-Sleep -Seconds 6

    python $seedFile

    Stop-Job $pfNeo4j; Remove-Job $pfNeo4j
    Stop-Job $pfPg;    Remove-Job $pfPg

    if ($LASTEXITCODE -ne 0) {
        Write-Host "  ADVERTENCIA: el seed pudo haber fallado. Verifica manualmente." -ForegroundColor Yellow
    } else {
        Write-Host "  OK Grafo cargado en Neo4J" -ForegroundColor Green
    }
}
Write-Host ""

# ── Resumen ───────────────────────────────────────────────────────────────────

Write-Host "============================================" -ForegroundColor Green
Write-Host "  Neo4J desplegado correctamente!          " -ForegroundColor Green
Write-Host "============================================" -ForegroundColor Green
Write-Host ""
Write-Host "Neo4J Browser (con port-forward):" -ForegroundColor Cyan
Write-Host "  kubectl port-forward svc/neo4j-service 7474:7474 7687:7687 -n reservainteligente" -ForegroundColor DarkGray
Write-Host "  http://localhost:7474  (usuario: neo4j)" -ForegroundColor White
Write-Host ""
Write-Host "Consultas Cypher (co-compras, recomendaciones, rutas): Neo4j\queries.cypher" -ForegroundColor Cyan
Write-Host "Simular rutas de entrega:" -ForegroundColor Cyan
Write-Host "  `$env:NEO4J_PASSWORD='...'; python Neo4j\rutas_entrega.py" -ForegroundColor DarkGray
Write-Host ""
