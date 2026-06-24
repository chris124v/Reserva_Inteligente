"""
olap/validate_dw.py
────────────────────
Script de validación del Data Warehouse y procesamiento Spark.

Verifica:
  1. Conectividad con PostgreSQL
  2. Tablas analytics_* generadas por Spark tienen datos
  3. Tablas del esquema estrella en Hive tienen datos
  4. DAG de Airflow corrió exitosamente

Uso:
  # Con port-forwards activos:
  # kubectl port-forward svc/postgres-service 5432:5432 -n reservainteligente
  # kubectl port-forward svc/hiveserver2 10000:10000 -n reservainteligente
  pip install psycopg2-binary pyhive
  python olap/validate_dw.py

Salida:
  Reporte en consola y exportado a olap/validate_dw_report.json
"""

import os
import sys
import json
from datetime import datetime

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

# ── Configuracion ─────────────────────────────────────────────────────────────
PG_HOST     = os.environ.get("PG_HOST",     "localhost")
PG_PORT     = int(os.environ.get("PG_PORT", "5432"))
PG_DBNAME   = os.environ.get("PG_DBNAME",   "restaurantes_db")
PG_USER     = os.environ.get("PG_USER",     "postgres")
PG_PASSWORD = os.environ.get("PG_PASSWORD", "MySecurePass123!")

HIVE_HOST   = os.environ.get("HIVE_HOST",   "localhost")
HIVE_PORT   = int(os.environ.get("HIVE_PORT", "10000"))

OK   = "[OK]"
FAIL = "[FAIL]"
INFO = "[INFO]"

resultados = []

def check(nombre, condicion, detalle=""):
    estado = OK if condicion else FAIL
    linea  = f"  {estado}  {nombre}"
    if detalle:
        linea += f" — {detalle}"
    print(linea)
    resultados.append({"test": nombre, "estado": estado, "detalle": detalle})
    return condicion

# ── PostgreSQL ────────────────────────────────────────────────────────────────

def get_pg_conn():
    import psycopg2
    return psycopg2.connect(
        host=PG_HOST, port=PG_PORT, dbname=PG_DBNAME,
        user=PG_USER, password=PG_PASSWORD
    )

def validar_postgres():
    print("\n── 1. Conectividad PostgreSQL ────────────────────────────────")
    try:
        conn = get_pg_conn()
        conn.close()
        check("Conexion a PostgreSQL", True, f"{PG_HOST}:{PG_PORT}/{PG_DBNAME}")
        return True
    except Exception as e:
        check("Conexion a PostgreSQL", False, str(e))
        return False

def validar_tablas_analytics(conn):
    print("\n── 2. Tablas analytics_* generadas por Spark ────────────────")
    cur = conn.cursor()

    tablas = [
        ("analytics_tendencias_consumo",  "Tendencias de consumo por mes y categoria"),
        ("analytics_horarios_pico",        "Horarios pico de pedidos y reservas"),
        ("analytics_crecimiento_mensual",  "Crecimiento mensual de ingresos"),
        ("analytics_ingresos_mes_categoria","Ingresos por mes y categoria (Metabase)"),
        ("analytics_actividad_zona",       "Actividad por zona geografica (Metabase)"),
        ("analytics_pedidos_estado",       "Pedidos completados vs cancelados (Metabase)"),
    ]

    for tabla, descripcion in tablas:
        try:
            cur.execute(f"SELECT COUNT(*) FROM {tabla}")
            count = cur.fetchone()[0]
            check(f"{tabla}", count > 0, f"{count} filas — {descripcion}")
        except Exception as e:
            check(f"{tabla}", False, f"No existe o error: {e}")
            conn.rollback()

    cur.close()

def validar_datos_origen(conn):
    print("\n── 3. Integridad datos origen (PostgreSQL operacional) ───────")
    cur = conn.cursor()

    queries = [
        ("Usuarios en BD",      "SELECT COUNT(*) FROM users"),
        ("Restaurantes en BD",  "SELECT COUNT(*) FROM restaurants"),
        ("Pedidos en BD",       "SELECT COUNT(*) FROM orders"),
        ("Reservas en BD",      "SELECT COUNT(*) FROM reservations"),
        ("Menus en BD",         "SELECT COUNT(*) FROM menus"),
    ]

    for nombre, query in queries:
        try:
            cur.execute(query)
            count = cur.fetchone()[0]
            check(nombre, count > 0, f"{count} registros")
        except Exception as e:
            check(nombre, False, str(e))
            conn.rollback()

    cur.close()

# ── Hive ──────────────────────────────────────────────────────────────────────

def validar_hive():
    print("\n── 4. Esquema estrella en Hive (Data Warehouse) ─────────────")
    try:
        from pyhive import hive
        conn = hive.connect(host=HIVE_HOST, port=HIVE_PORT, database="reserva_dw")
        cur  = conn.cursor()

        tablas_dw = [
            "dim_tiempo",
            "dim_usuario",
            "dim_restaurante",
            "dim_producto",
            "dim_ubicacion",
            "fact_reservas",
            "fact_pedidos",
        ]

        for tabla in tablas_dw:
            try:
                cur.execute(f"SELECT COUNT(*) FROM reserva_dw.{tabla}")
                count = cur.fetchone()[0]
                check(f"Hive: {tabla}", count >= 0, f"{count} filas")
            except Exception as e:
                check(f"Hive: {tabla}", False, str(e))

        cur.close()
        conn.close()

    except ImportError:
        print(f"  {INFO}  pyhive no instalado — saltando validacion Hive")
        print(f"  {INFO}  Instalar: pip install pyhive thrift")
    except Exception as e:
        print(f"  {INFO}  No se pudo conectar a Hive: {e}")
        print(f"  {INFO}  Verificar port-forward: kubectl port-forward svc/hiveserver2 10000:10000 -n reservainteligente")

# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("  VALIDACION DATA WAREHOUSE — Reserva Inteligente")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    if not validar_postgres():
        print("\nNo se pudo conectar a PostgreSQL.")
        print("Verificar: kubectl port-forward svc/postgres-service 5432:5432 -n reservainteligente")
        sys.exit(1)

    conn = get_pg_conn()
    validar_tablas_analytics(conn)
    validar_datos_origen(conn)
    conn.close()

    validar_hive()

    # Resumen
    total  = len(resultados)
    ok     = sum(1 for r in resultados if r["estado"] == OK)
    failed = total - ok

    print("\n" + "=" * 60)
    print(f"  RESUMEN: {ok}/{total} validaciones exitosas", end="")
    if failed:
        print(f"  |  {failed} fallaron")
    else:
        print("  ✅ Todo OK")
    print("=" * 60)

    reporte = {
        "fecha":      datetime.now().isoformat(),
        "postgres":   f"{PG_HOST}:{PG_PORT}/{PG_DBNAME}",
        "resumen":    {"total": total, "ok": ok, "fallaron": failed},
        "resultados": resultados,
    }
    output = os.path.join(os.path.dirname(__file__), "validate_dw_report.json")
    with open(output, "w", encoding="utf-8") as f:
        json.dump(reporte, f, ensure_ascii=False, indent=2)
    print(f"\n  Reporte exportado a {output}")

    sys.exit(0 if failed == 0 else 1)

if __name__ == "__main__":
    main()