"""
olap/validate_spark.py
───────────────────────
Script de validación de los análisis Spark.

Verifica que los 3 análisis de Spark generaron datos correctamente
consultando las tablas analytics_* en PostgreSQL y exportando
los resultados como reportes exportables.

Verifica:
  1. analytics_tendencias_consumo — tendencias de consumo por mes/categoria
  2. analytics_horarios_pico      — horarios pico de actividad
  3. analytics_crecimiento_mensual — crecimiento mensual con MoM

Uso:
  # Con port-forward activo:
  # kubectl port-forward svc/postgres-service 5432:5432 -n reservainteligente
  pip install psycopg2-binary
  python olap/validate_spark.py

Salida:
  Reporte en consola y exportado a olap/validate_spark_report.json
"""

import os
import sys
import json
import psycopg2
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

OK   = "[OK]"
FAIL = "[FAIL]"
INFO = "[INFO]"

resultados  = []
reportes    = {}

def check(nombre, condicion, detalle=""):
    estado = OK if condicion else FAIL
    linea  = f"  {estado}  {nombre}"
    if detalle:
        linea += f" — {detalle}"
    print(linea)
    resultados.append({"test": nombre, "estado": estado, "detalle": detalle})
    return condicion

# ── Validaciones ──────────────────────────────────────────────────────────────

def validar_tendencias_consumo(cur):
    print("\n── 1. Tendencias de Consumo (Spark Analysis) ────────────────")
    try:
        cur.execute("SELECT COUNT(*) FROM analytics_tendencias_consumo")
        total = cur.fetchone()[0]
        check("Tabla analytics_tendencias_consumo tiene datos", total > 0, f"{total} filas")

        cur.execute("""
            SELECT anio, mes, categoria, num_pedidos, unidades_vendidas, ingresos
            FROM analytics_tendencias_consumo
            ORDER BY ingresos DESC
            LIMIT 5
        """)
        rows = cur.fetchall()
        cols = [d[0] for d in cur.description]

        print(f"\n  Top 5 categorias por ingresos:")
        print(f"  {'Año':<6} {'Mes':<5} {'Categoria':<20} {'Pedidos':<10} {'Unidades':<10} {'Ingresos'}")
        print(f"  {'-'*70}")
        for r in rows:
            print(f"  {r[0]:<6} {r[1]:<5} {str(r[2]):<20} {r[3]:<10} {r[4]:<10} ₡{r[5]:,.2f}")

        check("Top categorias calculadas", len(rows) > 0, f"{len(rows)} categorias")

        cur.execute("""
            SELECT COUNT(DISTINCT categoria) FROM analytics_tendencias_consumo
        """)
        cats = cur.fetchone()[0]
        check("Multiples categorias analizadas", cats > 1, f"{cats} categorias distintas")

        reportes["tendencias_consumo"] = [dict(zip(cols, r)) for r in rows]

    except Exception as e:
        check("analytics_tendencias_consumo", False, str(e))


def validar_horarios_pico(cur):
    print("\n── 2. Horarios Pico (Spark Analysis) ────────────────────────")
    try:
        cur.execute("SELECT COUNT(*) FROM analytics_horarios_pico")
        total = cur.fetchone()[0]
        check("Tabla analytics_horarios_pico tiene datos", total > 0, f"{total} filas")

        cur.execute("""
            SELECT hora, dia_semana_nombre, total_reservas, total_pedidos, ingresos_pedidos
            FROM analytics_horarios_pico
            ORDER BY total_pedidos + total_reservas DESC
            LIMIT 5
        """)
        rows = cur.fetchall()
        cols = [d[0] for d in cur.description]

        print(f"\n  Top 5 horarios con mas actividad:")
        print(f"  {'Hora':<6} {'Dia':<12} {'Reservas':<10} {'Pedidos':<10} {'Ingresos'}")
        print(f"  {'-'*60}")
        for r in rows:
            print(f"  {r[0]:<6} {str(r[1]):<12} {r[2]:<10} {r[3]:<10} ₡{r[4]:,.2f}")

        check("Horarios pico identificados", len(rows) > 0, f"{len(rows)} horarios")

        cur.execute("""
            SELECT COUNT(DISTINCT hora) FROM analytics_horarios_pico
        """)
        horas = cur.fetchone()[0]
        check("Multiples horas analizadas", horas > 1, f"{horas} horas distintas")

        reportes["horarios_pico"] = [dict(zip(cols, r)) for r in rows]

    except Exception as e:
        check("analytics_horarios_pico", False, str(e))


def validar_crecimiento_mensual(cur):
    print("\n── 3. Crecimiento Mensual (Spark Analysis) ──────────────────")
    try:
        cur.execute("SELECT COUNT(*) FROM analytics_crecimiento_mensual")
        total = cur.fetchone()[0]
        check("Tabla analytics_crecimiento_mensual tiene datos", total > 0, f"{total} filas")

        cur.execute("""
            SELECT anio, mes, pedidos_mes, clientes_activos, ingresos_mes,
                   crecimiento_ingresos_pct, crecimiento_pedidos_pct
            FROM analytics_crecimiento_mensual
            ORDER BY anio, mes
        """)
        rows = cur.fetchall()
        cols = [d[0] for d in cur.description]

        print(f"\n  Crecimiento mensual:")
        print(f"  {'Año':<6} {'Mes':<5} {'Pedidos':<10} {'Clientes':<10} {'Ingresos':<15} {'Crec.%'}")
        print(f"  {'-'*65}")
        for r in rows:
            crec = f"{r[6]}%" if r[6] is not None else "N/A"
            print(f"  {r[0]:<6} {r[1]:<5} {r[2]:<10} {r[3]:<10} ₡{r[4]:>12,.2f}  {crec}")

        check("Series temporales calculadas", len(rows) > 0, f"{len(rows)} meses")
        check("Window functions LAG() aplicadas",
              any(r[6] is not None for r in rows),
              "crecimiento MoM calculado")

        reportes["crecimiento_mensual"] = [dict(zip(cols, r)) for r in rows]

    except Exception as e:
        check("analytics_crecimiento_mensual", False, str(e))


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("  VALIDACION SPARK — Reserva Inteligente")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    print(f"\nConectando a PostgreSQL {PG_HOST}:{PG_PORT}/{PG_DBNAME}...")
    try:
        conn = psycopg2.connect(
            host=PG_HOST, port=PG_PORT, dbname=PG_DBNAME,
            user=PG_USER, password=PG_PASSWORD
        )
        print("  Conexion exitosa")
    except Exception as e:
        print(f"  ERROR: {e}")
        print("  Verificar: kubectl port-forward svc/postgres-service 5432:5432 -n reservainteligente")
        sys.exit(1)

    cur = conn.cursor()
    validar_tendencias_consumo(cur)
    validar_horarios_pico(cur)
    validar_crecimiento_mensual(cur)
    cur.close()
    conn.close()

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
        "datos":      reportes,
    }
    output = os.path.join(os.path.dirname(__file__), "validate_spark_report.json")
    with open(output, "w", encoding="utf-8") as f:
        json.dump(reporte, f, ensure_ascii=False, indent=2, default=str)
    print(f"\n  Reporte exportado a {output}")

    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
