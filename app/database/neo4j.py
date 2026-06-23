import os
from neo4j import GraphDatabase
from neo4j import Driver

_driver: Driver | None = None

# Retorna el driver de Neo4J, creandolo si no existe.
def get_neo4j_driver() -> Driver:
    global _driver
    if _driver is None:
        uri      = os.getenv("NEO4J_URI",      "bolt://neo4j-service:7687")
        user     = os.getenv("NEO4J_USER",     "neo4j")
        password = os.getenv("NEO4J_PASSWORD", "Neo4jPass123!")
        _driver  = GraphDatabase.driver(uri, auth=(user, password))
    return _driver

# Cierra el driver de Neo4J si esta abierto.
def close_neo4j_driver():
    global _driver
    if _driver is not None:
        _driver.close()
        _driver = None
