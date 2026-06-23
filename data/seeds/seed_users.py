#!/usr/bin/env python3
"""
Seed users in AWS Cognito only (PostgreSQL users are created by postgres_seed.sql).
Run from project root: python data/seeds/seed_users.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from dotenv import load_dotenv
load_dotenv()

from app.auth.cognito import CognitoClient

# ── User definitions ─────────────────────────────────────────────────────────

def _seed_demo_users():
    """Usuarios sinteticos compartidos por Postgres y Mongo.

    Usan los MISMOS emails que generan postgres_seed.sql y mongo_seed.js
    (admin{N}.seed@demo.com / cliente{N}.seed@demo.com), de modo que un solo
    usuario de Cognito sirve a ambos backends operacionales. Son datos para
    poblar dashboards/analitica; el password cumple la politica del pool.
    Para borrarlos: data/seeds/cognito_cleanup.py (borra solo *.seed@demo.com).
    """
    users = []
    for g in range(1, 5):       # 4 admins  -> total 6 con los base
        users.append({"email": f"admin{g}.seed@demo.com", "password": "SeedDemo2026!",
                      "nombre": f"Admin Demo {g}", "rol": "admin"})
    for g in range(1, 31):      # 30 clientes -> total 33 con los base
        users.append({"email": f"cliente{g}.seed@demo.com", "password": "SeedDemo2026!",
                      "nombre": f"Cliente Demo {g}", "rol": "cliente"})
    return users

ALL_COGNITO_USERS = [
    {"email": "adminpostgres@gmail.com",   "password": "messiGo7te!d", "nombre": "Admin Postgres",    "rol": "admin"},
    {"email": "clientepostgres@gmail.com", "password": "t0puriA!$",    "nombre": "Cliente Postgres",  "rol": "cliente"},
    {"email": "admin2.postgres@gmail.com", "password": "CR7secure!",   "nombre": "Cristiano Ronaldo", "rol": "admin"},
    {"email": "lionel.postgres@gmail.com", "password": "t0puriA!$",    "nombre": "Lionel Messi",      "rol": "cliente"},
    {"email": "iniesta.postgres@gmail.com","password": "t0puriA!$",    "nombre": "Andres Iniesta",    "rol": "cliente"},
    {"email": "adminmongo@gmail.com",      "password": "messiGo7te!d", "nombre": "Admin Mongo",       "rol": "admin"},
    {"email": "clientemongo@gmail.com",    "password": "t0puriA!$",    "nombre": "Cliente Mongo",     "rol": "cliente"},
    {"email": "admin2.mongo@example.com",  "password": "IbraSecure8!", "nombre": "Zlatan Ibrahimovic","rol": "admin"},
    {"email": "lionel.mongo@example.com",  "password": "t0puriA!$",    "nombre": "Lionel Messi",      "rol": "cliente"},
    {"email": "iniesta.mongo@example.com", "password": "t0puriA!$",    "nombre": "Andres Iniesta",    "rol": "cliente"},
] + _seed_demo_users()

# ── Steps ────────────────────────────────────────────────────────────────────

def seed_cognito(cognito: CognitoClient):
    print("\n── Creando usuarios en AWS Cognito ──────────────────────────────")
    ok = skipped = failed = 0
    for u in ALL_COGNITO_USERS:
        result = cognito.register_user(
            email=u["email"],
            password=u["password"],
            nombre=u["nombre"],
            rol=u["rol"],
        )
        if result["success"]:
            print(f"  ✓ {u['email']}")
            ok += 1
        elif "UsernameExistsException" in str(result.get("error", "")):
            print(f"  ~ {u['email']} (ya existe, omitido)")
            skipped += 1
        else:
            print(f"  ✗ {u['email']} — {result.get('error')}")
            failed += 1
    print(f"\n  Cognito: {ok} creados, {skipped} omitidos, {failed} errores")


def main():
    print("=== Seed de Usuarios en Cognito ===")
    cognito = CognitoClient()
    seed_cognito(cognito)
    print("\n=== Completado ===")
    print("Siguiente paso: ejecuta cleanup y seed de Postgres/Mongo via kubectl.")
    print("  Ver: data/seeds/instrucciones_seed.md")


if __name__ == "__main__":
    main()
