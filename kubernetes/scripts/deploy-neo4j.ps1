# deploy-neo4j.ps1
# Despliega Neo4J en Kubernetes usando Helm y carga el grafo desde PostgreSQL
#
# Prerequisitos:
#   - deploy-all.ps1 ya ejecutado (PostgreSQL con datos)
#   - helm instalado (winget install Helm.Helm)
#   - pip install neo4j psycopg2-binary

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  Reserva Inteligente - Neo4J Deploy       " -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# ── Verificaciones previas ────────────────────────────────────────────────────

if (-not (Get-Command kubectl -ErrorAction SilentlyContinue)) {
    Write-Host "ERROR: kubectl no instalado" -ForegroundColor Red
    exit 1
}

if (-not (Get-Command helm -ErrorAction SilentlyContinue)) {
    Write-Host "ERROR: helm no instalado. Instalar con: winget install Helm.Helm" -ForegroundColor Red
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

# ── 1. Repositorio de Helm ────────────────────────────────────────────────────

Write-Host "[1/3] Configurando repositorio Helm de Neo4J..." -ForegroundColor Yellow
helm repo add neo4j https://helm.neo4j.com/neo4j 2>&1 | Out-Null
helm repo update 2>&1 | Out-Null
Write-Host "OK Repositorio neo4j configurado" -ForegroundColor Green
Write-Host ""

# ── 2. Desplegar Neo4J ────────────────────────────────────────────────────────

Write-Host "[2/3] Desplegando Neo4J con Helm..." -ForegroundColor Yellow

# Verificar si ya esta instalado
$existingRelease = helm list -n reservainteligente --filter "^neo4j$" -q 2>$null
if ($existingRelease -eq "neo4j") {
    Write-Host "  Neo4J ya esta instalado, omitiendo instalacion" -ForegroundColor DarkGray
} else {
    helm install neo4j neo4j/neo4j `
        --namespace reservainteligente `
        --set neo4j.name=neo4j `
        --set neo4j.password="Neo4jPass123!" `
        --set volumes.data.mode=defaultStorageClass `
        --set env.NEO4J_PLUGINS='["apoc"]'

    if ($LASTEXITCODE -ne 0) {
        Write-Host "ERROR: fallo la instalacion de Neo4J con Helm" -ForegroundColor Red
        exit 1
    }
}

Write-Host "  Esperando que Neo4J este listo (puede tardar ~2 minutos)..." -ForegroundColor Cyan
kubectl rollout status --watch --timeout=300s statefulset/neo4j -n reservainteligente

if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Neo4J no levanto en tiempo. Revisa los logs:" -ForegroundColor Red
    Write-Host "  kubectl logs -l app=neo4j -n reservainteligente" -ForegroundColor Yellow
    exit 1
}

Write-Host "OK Neo4J listo" -ForegroundColor Green
Write-Host ""

# ── 3. Cargar grafo desde PostgreSQL ─────────────────────────────────────────

Write-Host "[3/3] Cargando grafo desde PostgreSQL..." -ForegroundColor Yellow

# Instalar dependencias Python necesarias para el seed
$reqFile = Join-Path $projectRoot "neo4j\requirements.txt"
if (Test-Path $reqFile) {
    Write-Host "  Instalando dependencias Python..." -ForegroundColor Cyan
    pip install -r $reqFile -q
}

$seedFile = Join-Path $projectRoot "neo4j\seed_neo4j.py"
if (-not (Test-Path $seedFile)) {
    Write-Host "  ADVERTENCIA: no se encuentra $seedFile" -ForegroundColor Yellow
    Write-Host "  Ejecuta el seed manualmente:" -ForegroundColor DarkGray
    Write-Host "  kubectl port-forward svc/neo4j 7474:7474 7687:7687 -n reservainteligente" -ForegroundColor DarkGray
    Write-Host "  kubectl port-forward svc/postgres-service 5432:5432 -n reservainteligente" -ForegroundColor DarkGray
    Write-Host "  python neo4j\seed_neo4j.py" -ForegroundColor DarkGray
} else {
    Write-Host "  Abriendo port-forwards temporales..." -ForegroundColor Cyan

    $pfNeo4j = Start-Job { kubectl port-forward svc/neo4j 7687:7687 -n reservainteligente }
    $pfPg    = Start-Job { kubectl port-forward svc/postgres-service 5432:5432 -n reservainteligente }
    Start-Sleep -Seconds 5

    python $seedFile

    Stop-Job $pfNeo4j; Remove-Job $pfNeo4j
    Stop-Job $pfPg;    Remove-Job $pfPg

    if ($LASTEXITCODE -ne 0) {
        Write-Host "  ADVERTENCIA: el seed pudo haber fallado parcialmente" -ForegroundColor Yellow
        Write-Host "  Verifica con: kubectl port-forward svc/neo4j 7474:7474 7687:7687 -n reservainteligente" -ForegroundColor DarkGray
        Write-Host "  Luego abre http://localhost:7474 y ejecuta: MATCH (n) RETURN labels(n), count(n)" -ForegroundColor DarkGray
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
Write-Host "Endpoints disponibles (con port-forward):" -ForegroundColor Cyan
Write-Host "  Neo4J Browser: http://localhost:7474" -ForegroundColor White
Write-Host "    kubectl port-forward svc/neo4j 7474:7474 7687:7687 -n reservainteligente" -ForegroundColor DarkGray
Write-Host "  Usuario: neo4j  |  Password: Neo4jPass123!" -ForegroundColor White
Write-Host ""
Write-Host "Verificar estado del pod:" -ForegroundColor Cyan
Write-Host "  kubectl get pods -l app=neo4j -n reservainteligente" -ForegroundColor DarkGray
Write-Host ""
Write-Host "Verificar grafo (en Neo4J Browser):" -ForegroundColor Cyan
Write-Host "  MATCH (n) RETURN labels(n), count(n)" -ForegroundColor DarkGray
Write-Host ""