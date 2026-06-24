"""
validate_all.py
───────────────
Corre las 4 validaciones del proyecto Reserva Inteligente en orden:

  1. Neo4J      — grafo, consultas Cypher, rutas de entrega
  2. Airflow    — pipeline ETL, DAG, schedule @daily
  3. Spark      — 3 análisis: tendencias, horarios pico, crecimiento mensual
  4. DW         — integridad del Data Warehouse en PostgreSQL y Hive

Requisitos (port-forwards activos):
  kubectl port-forward svc/neo4j-service 7687:7687 -n reservainteligente
  kubectl port-forward svc/airflow-webserver 8080:8080 -n reservainteligente
  kubectl port-forward svc/postgres-service 5432:5432 -n reservainteligente
  kubectl port-forward svc/hiveserver2 10000:10000 -n reservainteligente

Uso:
  pip install neo4j psycopg2-binary requests pyhive thrift
  python validate_all.py

Salida:
  Reporte consolidado en validate_all_report.json
"""

import subprocess
import sys
import json
import os
from datetime import datetime

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

SCRIPTS = [
    ("Neo4J",    "Neo4j/validate_neo4j.py",     "Neo4j/validation_report.json"),
    ("Airflow",  "olap/validate_airflow.py",     "olap/validate_airflow_report.json"),
    ("Spark",    "olap/validate_spark.py",        "olap/validate_spark_report.json"),
    ("DW/Hive",  "olap/validate_dw.py",           "olap/validate_dw_report.json"),
]

def correr_script(nombre, script):
    print(f"\n{'='*60}")
    print(f"  Corriendo: {nombre} ({script})")
    print(f"{'='*60}\n")
    resultado = subprocess.run(
        [sys.executable, script],
        capture_output=False,
    )
    return resultado.returncode == 0

def leer_reporte(path):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None

def main():
    print("=" * 60)
    print("  VALIDACIONES COMPLETAS — Reserva Inteligente")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    resumen_global = []
    exitosos = 0

    for nombre, script, reporte_path in SCRIPTS:
        ok = correr_script(nombre, script)
        reporte = leer_reporte(reporte_path)

        if reporte:
            r = reporte.get("resumen", {})
            detalle = f"{r.get('ok', '?')} OK / {r.get('total', '?')} total"
            if r.get("advertencias"):
                detalle += f" / {r.get('advertencias')} WARN"
            if r.get("fallaron"):
                detalle += f" / {r.get('fallaron')} FAIL"
        else:
            detalle = "reporte no disponible"

        estado = "✅" if ok else "❌"
        if ok:
            exitosos += 1
        resumen_global.append({
            "validacion": nombre,
            "script": script,
            "exitoso": ok,
            "detalle": detalle,
        })
        print(f"\n  {estado} {nombre}: {detalle}")

    print(f"\n{'='*60}")
    print(f"  RESUMEN GLOBAL: {exitosos}/{len(SCRIPTS)} validaciones exitosas")
    if exitosos == len(SCRIPTS):
        print("  ✅ Todas las validaciones pasaron")
    else:
        print(f"  ❌ {len(SCRIPTS) - exitosos} validaciones fallaron")
    print(f"{'='*60}")

    reporte_final = {
        "fecha": datetime.now().isoformat(),
        "resumen": {
            "total": len(SCRIPTS),
            "exitosos": exitosos,
            "fallidos": len(SCRIPTS) - exitosos,
        },
        "validaciones": resumen_global,
    }

    output = os.path.join(os.path.dirname(__file__), "validate_all_report.json")
    with open(output, "w", encoding="utf-8") as f:
        json.dump(reporte_final, f, ensure_ascii=False, indent=2)
    print(f"\n  Reporte consolidado exportado a {output}")

    sys.exit(0 if exitosos == len(SCRIPTS) else 1)

if __name__ == "__main__":
    main()
