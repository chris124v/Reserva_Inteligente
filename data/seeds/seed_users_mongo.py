#!/usr/bin/env python3
"""
Seed users in AWS Cognito only (MongoDB users are created by mongo_seed.js).
Run from project root: python data/seeds/seed_users_mongo.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from dotenv import load_dotenv
load_dotenv()

from app.auth.cognito import CognitoClient

# ── User definitions ─────────────────────────────────────────────────────────

ALL_COGNITO_USERS = [
    {"email": "adminmongo@gmail.com",      "password": "messiGo7te!d", "nombre": "Admin Mongo",        "rol": "admin"},
    {"email": "clientemongo@gmail.com",    "password": "t0puriA!$",    "nombre": "Cliente Mongo",      "rol": "cliente"},
    {"email": "admin2.mongo@example.com",  "password": "IbraSecure8!", "nombre": "Zlatan Ibrahimovic", "rol": "admin"},
    {"email": "lionel.mongo@example.com",  "password": "t0puriA!$",    "nombre": "Lionel Messi",       "rol": "cliente"},
    {"email": "iniesta.mongo@example.com", "password": "t0puriA!$",    "nombre": "Andres Iniesta",     "rol": "cliente"},
    {"email": "adminpostgres@gmail.com",   "password": "messiGo7te!d", "nombre": "Admin Postgres",     "rol": "admin"},
    {"email": "clientepostgres@gmail.com", "password": "t0puriA!$",    "nombre": "Cliente Postgres",   "rol": "cliente"},
    {"email": "admin2.postgres@gmail.com", "password": "CR7secure!",   "nombre": "Cristiano Ronaldo",  "rol": "admin"},
    {"email": "lionel.postgres@gmail.com", "password": "t0puriA!$",    "nombre": "Lionel Messi",       "rol": "cliente"},
    {"email": "iniesta.postgres@gmail.com","password": "t0puriA!$",    "nombre": "Andres Iniesta",     "rol": "cliente"},
]

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
    print("Siguiente paso: ejecuta cleanup y seed de Mongo/Postgres via kubectl.")
    print("  Ver: data/seeds/instrucciones_seed.md")


if __name__ == "__main__":
    main()
