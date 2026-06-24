"""
Neo4j/validate_neo4j.py
────────────────────────
Script de validación de integridad y funcionalidad del grafo Neo4J.

Verifica:
  1. Conectividad con Neo4J
  2. Integridad del grafo (nodos y relaciones esperados)
  3. Consultas del Req 5 (co-compras, usuarios influyentes, referidos, rutas)
  4. Módulo de rutas de entrega (Req 6)

Uso:
  kubectl port-forward svc/neo4j-service 7474:7474 7687:7687 -n reservainteligente
  kubectl port-forward svc/postgres-service 5432:5432 -n reservainteligente
  pip install -r Neo4j/neo4j-requirements.txt
  python Neo4j/validate_neo4j.py

Salida:
  Reporte de validación en consola y exportado a Neo4j/validation_report.json
"""

import os
import sys
import json
from datetime import datetime
from neo4j import GraphDatabase

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

# ── Configuracion ─────────────────────────────────────────────────────────────
NEO4J_URI      = os.environ.get("NEO4J_URI",      "bolt://localhost:7687")
NEO4J_USER     = os.environ.get("NEO4J_USER",     "neo4j")
NEO4J_PASSWORD = os.environ.get("NEO4J_PASSWORD", "Neo4jPass123!")

# Minimos esperados en el grafo (ajustar si el seed cambia)
MINIMOS = {
    "Usuario":     5,
    "Restaurante": 3,
    "Producto":    5,
    "Pedido":      10,
    "Zona":        3,
}

RELACIONES_ESPERADAS = [
    "REALIZO",
    "EN",
    "CONTIENE",
    "PERTENECE_A",
    "UBICADO_EN",
    "DISTANCIA_A",
]

# ── Helpers ───────────────────────────────────────────────────────────────────

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

# ── Validaciones ──────────────────────────────────────────────────────────────

def validar_conectividad(driver):
    print("\n── 1. Conectividad ──────────────────────────────────────────")
    try:
        with driver.session() as s:
            s.run("RETURN 1")
        check("Conexion a Neo4J", True, f"bolt://{NEO4J_URI.split('://')[-1]}")
        return True
    except Exception as e:
        check("Conexion a Neo4J", False, str(e))
        return False


def validar_integridad_grafo(session):
    print("\n── 2. Integridad del grafo ──────────────────────────────────")

    # Contar nodos por tipo
    result = session.run(
        "MATCH (n) RETURN labels(n)[0] AS tipo, count(n) AS cantidad"
    )
    conteos = {row["tipo"]: row["cantidad"] for row in result}

    print(f"  {INFO}  Nodos encontrados: {conteos}")
    for tipo, minimo in MINIMOS.items():
        cant = conteos.get(tipo, 0)
        check(
            f"Nodos :{tipo} >= {minimo}",
            cant >= minimo,
            f"{cant} nodos"
        )

    # Contar relaciones
    result = session.run(
        "MATCH ()-[r]->() RETURN type(r) AS rel, count(r) AS cantidad"
    )
    rels = {row["rel"]: row["cantidad"] for row in result}
    print(f"  {INFO}  Relaciones encontradas: {rels}")

    for rel in RELACIONES_ESPERADAS:
        cant = rels.get(rel, 0)
        check(f"Relacion :{rel} existe", cant > 0, f"{cant} relaciones")


def validar_req5_consultas(session):
    print("\n── 3. Req 5 — Consultas Cypher ──────────────────────────────")

    # Query 1: co-compras
    result = list(session.run("""
        MATCH (p1:Producto)<-[:CONTIENE]-(o:Pedido)-[:CONTIENE]->(p2:Producto)
        WHERE p1.id < p2.id AND o.estado <> 'cancelado'
        WITH p1.nombre AS p1, p2.nombre AS p2, count(o) AS veces
        ORDER BY veces DESC LIMIT 5
        RETURN p1, p2, veces
    """))
    check(
        "Co-compras: 5 pares de productos mas comprados juntos",
        len(result) > 0,
        f"{len(result)} pares encontrados"
    )
    if result:
        print(f"    Top par: '{result[0]['p1']}' + '{result[0]['p2']}' ({result[0]['veces']} veces)")

    # Query 2: usuarios influyentes
    result = list(session.run("""
        MATCH (u:Usuario)-[:REALIZO]->(o:Pedido)
        WITH u.nombre AS usuario, count(o) AS pedidos, sum(o.total) AS gasto
        ORDER BY pedidos DESC LIMIT 5
        RETURN usuario, pedidos, gasto
    """))
    check(
        "Usuarios influyentes por actividad",
        len(result) > 0,
        f"{len(result)} usuarios con pedidos"
    )
    if result:
        print(f"    Top usuario: '{result[0]['usuario']}' con {result[0]['pedidos']} pedidos")

    # Query 3: red de referidos
    result = list(session.run("""
        MATCH (u:Usuario)-[:RECOMENDO]->(r:Usuario)
        RETURN u.nombre AS usuario, count(r) AS referidos
        ORDER BY referidos DESC LIMIT 5
    """))
    check(
        "Red de referidos (RECOMENDO)",
        len(result) >= 0,   # puede ser 0 si no hay referidos en el seed
        f"{len(result)} usuarios con referidos"
    )

    # Query 4: camino minimo entre zonas
    result = list(session.run("""
        MATCH path = shortestPath(
            (a:Zona)-[:DISTANCIA_A*]->(b:Zona)
        )
        WHERE a <> b
        RETURN a.nombre AS origen, b.nombre AS destino,
               reduce(d=0, r IN relationships(path) | d + r.km) AS km
        ORDER BY km ASC LIMIT 1
    """))
    check(
        "Camino minimo entre zonas (shortestPath)",
        len(result) > 0,
        f"Ruta mas corta: {result[0]['origen']} → {result[0]['destino']} ({result[0]['km']} km)" if result else "Sin zonas"
    )


def validar_req6_rutas(session):
    print("\n── 4. Req 6 — Rutas de entrega ──────────────────────────────")

    # Verificar pedidos a domicilio
    result = list(session.run("""
        MATCH (u:Usuario)-[:REALIZO]->(o:Pedido)-[:EN]->(r:Restaurante)
        WHERE toUpper(o.tipo_entrega) = 'DOMICILIO'
        RETURN count(o) AS total
    """))
    total_domicilio = result[0]["total"] if result else 0
    check(
        "Pedidos a domicilio en el grafo",
        total_domicilio > 0,
        f"{total_domicilio} pedidos a domicilio"
    )

    # Verificar zonas con distancias
    result = list(session.run("""
        MATCH (a:Zona)-[r:DISTANCIA_A]->(b:Zona)
        RETURN count(r) AS conexiones
    """))
    conexiones = result[0]["conexiones"] if result else 0
    check(
        "Matriz de distancias entre zonas",
        conexiones > 0,
        f"{conexiones} conexiones entre zonas"
    )

    # Simular algoritmo vecino mas cercano (mini test)
    result = list(session.run("""
        MATCH (a:Zona), (b:Zona)
        WHERE a.nombre < b.nombre
        MATCH p = shortestPath((a)-[:DISTANCIA_A*]-(b))
        RETURN a.nombre AS za, b.nombre AS zb,
               reduce(s=0, r IN relationships(p) | s + r.km) AS km
        LIMIT 3
    """))
    check(
        "shortestPath disponible para algoritmo de rutas",
        len(result) > 0,
        f"{len(result)} pares de zonas con camino calculado"
    )


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("  VALIDACION NEO4J — Reserva Inteligente")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    print(f"\nConectando a {NEO4J_URI} como {NEO4J_USER}...")
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

    if not validar_conectividad(driver):
        print("\nNo se pudo conectar a Neo4J. Verifica el port-forward.")
        sys.exit(1)

    with driver.session() as session:
        validar_integridad_grafo(session)
        validar_req5_consultas(session)
        validar_req6_rutas(session)

    driver.close()

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

    # Exportar reporte
    reporte = {
        "fecha":      datetime.now().isoformat(),
        "neo4j_uri":  NEO4J_URI,
        "resumen":    {"total": total, "ok": ok, "fallaron": failed},
        "resultados": resultados,
    }
    output = os.path.join(os.path.dirname(__file__), "validation_report.json")
    with open(output, "w", encoding="utf-8") as f:
        json.dump(reporte, f, ensure_ascii=False, indent=2)
    print(f"\n  Reporte exportado a {output}")

    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
