"""
neo4j/rutas_entrega.py
──────────────────────
Módulo de simulación de rutas de entrega para el proyecto Reserva Inteligente.

Lee los pedidos pendientes a domicilio desde Neo4J y calcula el orden óptimo
de entrega para cada repartidor usando el algoritmo de vecino más cercano:
  - Parte desde la zona del restaurante
  - En cada paso va al cliente más cercano que aún no fue visitado
  - Repite hasta entregar todos los pedidos asignados

Uso:
  # Con port-forward activo:
  # kubectl port-forward svc/neo4j-service 7474:7474 7687:7687 -n reservainteligente
  pip install -r neo4j/requirements.txt
  python neo4j/rutas_entrega.py

Salida:
  Imprime la ruta optimizada por repartidor con distancia total estimada.
  También exporta el resultado a neo4j/rutas_resultado.json
"""

import os
import sys
import json
from neo4j import GraphDatabase

# La consola de Windows usa cp1252 y no puede imprimir los caracteres de caja/emoji
# del resumen. Forzamos UTF-8 en stdout para evitar UnicodeEncodeError.
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

# ── Configuracion ─────────────────────────────────────────────────────────────
# Credenciales por variable de entorno (no hardcodeadas). Para correr manual,
# setear NEO4J_PASSWORD en el entorno. Host localhost porque se accede via
# port-forward de Kubernetes.
NEO4J_URI      = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER     = os.environ.get("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.environ.get("NEO4J_PASSWORD", "neo4j")

# Numero de repartidores disponibles
NUM_REPARTIDORES = 2

# Matriz de distancias entre zonas. Se llena en runtime desde el grafo de Neo4J
# (cargar_matriz_distancias) usando shortestPath sobre las relaciones DISTANCIA_A,
# asi se obtiene la distancia minima real entre CUALQUIER par de zonas (incluso
# las que no tienen arista directa, via caminos multi-salto) y no se duplica la
# data hardcodeada de seed_neo4j.py. Cumple el Req 6 ("consultas en Neo4J para
# encontrar caminos optimos").
DISTANCIAS = {}

def cargar_matriz_distancias(session):
    """
    Calcula la distancia minima en km entre todos los pares de zonas usando
    shortestPath sobre las relaciones DISTANCIA_A del grafo, y la guarda en el
    diccionario global DISTANCIAS.
    """
    result = session.run("""
        MATCH (a:Zona), (b:Zona)
        WHERE a.nombre < b.nombre
        MATCH p = shortestPath((a)-[:DISTANCIA_A*]-(b))
        RETURN a.nombre AS za, b.nombre AS zb,
               reduce(s = 0, r IN relationships(p) | s + r.km) AS km
    """)
    for row in result:
        DISTANCIAS[(row["za"], row["zb"])] = row["km"]
    print(f"  Matriz de distancias cargada del grafo: {len(DISTANCIAS)} pares de zonas")

def distancia(zona_a, zona_b):
    """Distancia minima en km entre dos zonas (de la matriz cargada del grafo)."""
    if zona_a == zona_b:
        return 0
    return DISTANCIAS.get((zona_a, zona_b),
           DISTANCIAS.get((zona_b, zona_a), 999))

# ── Algoritmo de vecino mas cercano ──────────────────────────────────────────

def vecino_mas_cercano(zona_inicio, pedidos):
    """
    Dado un punto de inicio y una lista de pedidos con zona_entrega,
    devuelve el orden optimo de entrega usando vecino mas cercano.

    Parametros:
      zona_inicio: str — zona del restaurante (punto de partida)
      pedidos: list[dict] — cada dict tiene {pedido_id, cliente, zona_entrega, total}

    Retorna:
      list[dict] — pedidos en orden optimo de entrega
      int — distancia total recorrida en km
    """
    pendientes  = pedidos.copy()
    ruta        = []
    zona_actual = zona_inicio
    km_total    = 0

    while pendientes:
        # Buscar el pedido cuya zona de entrega este mas cerca de la zona actual
        mas_cercano = min(
            pendientes,
            key=lambda p: distancia(zona_actual, p["zona_entrega"] or zona_inicio)
        )
        km = distancia(zona_actual, mas_cercano["zona_entrega"] or zona_inicio)
        km_total   += km
        zona_actual = mas_cercano["zona_entrega"] or zona_inicio

        ruta.append({**mas_cercano, "km_desde_anterior": km})
        pendientes.remove(mas_cercano)

    return ruta, km_total

# ── Consulta de pedidos pendientes desde Neo4J ───────────────────────────────

def obtener_pedidos_pendientes(session):
    """
    Lee los pedidos a domicilio PENDIENTES de entrega desde Neo4J.

    Solo estados aun no finalizados (pendiente, confirmado, en_preparacion, listo);
    se excluyen 'entregado' y 'cancelado' — no tiene sentido rutear un pedido ya
    entregado o cancelado. Se usa toUpper() para ser robusto al case del estado.
    """
    result = session.run("""
        MATCH (u:Usuario)-[:REALIZO]->(o:Pedido)-[:EN]->(r:Restaurante)
        WHERE toUpper(o.tipo_entrega) = 'DOMICILIO'
          AND toUpper(o.estado) IN ['PENDIENTE', 'CONFIRMADO', 'EN_PREPARACION', 'LISTO']
        RETURN o.id          AS pedido_id,
               u.nombre      AS cliente,
               o.zona_entrega AS zona_entrega,
               r.nombre      AS restaurante,
               r.zona        AS zona_restaurante,
               o.total       AS total
        ORDER BY o.fecha ASC
    """)
    return [dict(r) for r in result]

# ── Asignacion de pedidos a repartidores ─────────────────────────────────────

def asignar_pedidos(pedidos, num_repartidores):
    """
    Distribuye los pedidos entre los repartidores de forma balanceada
    (round-robin por restaurante de origen).
    """
    # Agrupar pedidos por restaurante
    por_restaurante = {}
    for p in pedidos:
        rest = p["restaurante"]
        if rest not in por_restaurante:
            por_restaurante[rest] = {
                "zona_restaurante": p["zona_restaurante"],
                "pedidos": []
            }
        por_restaurante[rest]["pedidos"].append(p)

    # Distribuir restaurantes entre repartidores
    asignaciones = {f"Repartidor {i+1}": [] for i in range(num_repartidores)}
    repartidores = list(asignaciones.keys())

    for i, (restaurante, datos) in enumerate(por_restaurante.items()):
        repartidor = repartidores[i % num_repartidores]
        asignaciones[repartidor].append({
            "restaurante":       restaurante,
            "zona_restaurante":  datos["zona_restaurante"],
            "pedidos":           datos["pedidos"]
        })

    return asignaciones

# ── Imprimir resultado ────────────────────────────────────────────────────────

def imprimir_rutas(rutas_por_repartidor):
    print("\n" + "═" * 60)
    print("  RUTAS DE ENTREGA OPTIMIZADAS")
    print("  Algoritmo: Vecino Más Cercano")
    print("═" * 60)

    for repartidor, paradas in rutas_por_repartidor.items():
        print(f"\n📦 {repartidor}")
        print("─" * 40)

        if not paradas:
            print("  Sin pedidos asignados")
            continue

        km_total_repartidor = 0
        for parada in paradas:
            print(f"\n  🍽️  {parada['restaurante']} ({parada['zona_restaurante']})")
            print(f"  {'Pedido':<10} {'Cliente':<20} {'Zona Entrega':<20} {'Km':<5} {'Total CRC'}")
            print(f"  {'-'*75}")
            for entrega in parada["ruta"]:
                zona = entrega["zona_entrega"] or "N/A"
                km   = entrega["km_desde_anterior"]
                print(f"  #{entrega['pedido_id']:<9} {entrega['cliente']:<20} {zona:<20} {km:<5} ₡{entrega['total']:.0f}")
            print(f"  Subtotal restaurante: {parada['km_restaurante']} km")
            km_total_repartidor += parada["km_restaurante"]

        print(f"\n  ✅ Total recorrido: {km_total_repartidor} km")

    print("\n" + "═" * 60)

# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print("Conectando a Neo4J...")
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

    with driver.session() as session:
        print("Cargando matriz de distancias del grafo...")
        cargar_matriz_distancias(session)
        print("Obteniendo pedidos pendientes...")
        pedidos = obtener_pedidos_pendientes(session)

    driver.close()

    if not pedidos:
        print("No hay pedidos pendientes a domicilio.")
        return

    print(f"  {len(pedidos)} pedidos pendientes encontrados")

    # Asignar pedidos a repartidores
    asignaciones = asignar_pedidos(pedidos, NUM_REPARTIDORES)

    # Calcular ruta optima para cada repartidor
    rutas_por_repartidor = {}
    for repartidor, grupos in asignaciones.items():
        paradas = []
        for grupo in grupos:
            ruta, km = vecino_mas_cercano(grupo["zona_restaurante"], grupo["pedidos"])
            paradas.append({
                "restaurante":      grupo["restaurante"],
                "zona_restaurante": grupo["zona_restaurante"],
                "ruta":             ruta,
                "km_restaurante":   km,
            })
        rutas_por_repartidor[repartidor] = paradas

    # Imprimir resultado
    imprimir_rutas(rutas_por_repartidor)

    # Exportar a JSON (junto al script, sin depender del directorio actual)
    output_path = os.path.join(os.path.dirname(__file__), "rutas_resultado.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(rutas_por_repartidor, f, ensure_ascii=False, indent=2)
    print(f"\n📄 Resultado exportado a {output_path}")

if __name__ == "__main__":
    main()