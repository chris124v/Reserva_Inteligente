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
  # kubectl port-forward svc/neo4j 7474:7474 7687:7687 -n reservainteligente
  pip install -r neo4j/requirements.txt
  python neo4j/rutas_entrega.py

Salida:
  Imprime la ruta optimizada por repartidor con distancia total estimada.
  También exporta el resultado a neo4j/rutas_resultado.json
"""

import json
from neo4j import GraphDatabase

# ── Configuracion ─────────────────────────────────────────────────────────────
NEO4J_URI      = "bolt://localhost:7687"
NEO4J_USER     = "neo4j"
NEO4J_PASSWORD = "Neo4jPass123!"

# Numero de repartidores disponibles
NUM_REPARTIDORES = 2

# ── Distancias entre zonas (mismas que en seed_neo4j.py) ─────────────────────
DISTANCIAS = {
    ("Calle Roma",    "Av Italia"):      2,
    ("Calle Roma",    "Calle Falsa"):    3,
    ("Calle Roma",    "Muelle"):         8,
    ("Calle Roma",    "Boulevard"):      5,
    ("Calle Roma",    "Av Gol"):         4,
    ("Calle Roma",    "Plaza Central"):  1,
    ("Av Italia",     "Calle Falsa"):    2,
    ("Av Italia",     "Muelle"):         7,
    ("Av Italia",     "Boulevard"):      4,
    ("Calle Falsa",   "Muelle"):         6,
    ("Calle Falsa",   "Av Gol"):         3,
    ("Muelle",        "Boulevard"):      4,
    ("Boulevard",     "Av Gol"):         2,
    ("Av Gol",        "Plaza Central"):  3,
    ("Plaza Central", "Calle Falsa"):    2,
}

def distancia(zona_a, zona_b):
    """Devuelve la distancia en km entre dos zonas. 999 si no hay conexion directa."""
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
    """Lee los pedidos a domicilio pendientes desde Neo4J."""
    result = session.run("""
        MATCH (u:Usuario)-[:REALIZO]->(o:Pedido)-[:EN]->(r:Restaurante)
        WHERE toUpper(o.tipo_entrega) = 'DOMICILIO'
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

    # Exportar a JSON
    output_path = "neo4j/rutas_resultado.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(rutas_por_repartidor, f, ensure_ascii=False, indent=2)
    print(f"\n📄 Resultado exportado a {output_path}")

if __name__ == "__main__":
    main()