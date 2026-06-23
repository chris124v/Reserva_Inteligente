#!/usr/bin/env python3
"""
Borra de AWS Cognito UNICAMENTE los usuarios sinteticos del seed extendido
(emails admin{N}.seed@demo.com / cliente{N}.seed@demo.com).

NO toca las cuentas base del demo (adminpostgres@, clientemongo@, etc.): esas
se mantienen siempre. Es el equivalente en Cognito de postgres_cleanup.sql /
mongo_cleanup.js, pero acotado a los usuarios sinteticos por seguridad.

Uso desde la raiz del proyecto:
    python data/seeds/cognito_cleanup.py            # borra los *.seed@demo.com
    python data/seeds/cognito_cleanup.py --dry-run  # solo lista, no borra
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from dotenv import load_dotenv
load_dotenv()

from app.config import settings
from app.auth.cognito import CognitoClient


def seed_emails():
    """Mismos emails que generan los seeds de Postgres/Mongo y _seed_demo_users()."""
    emails = [f"admin{g}.seed@demo.com" for g in range(1, 5)]
    emails += [f"cliente{g}.seed@demo.com" for g in range(1, 31)]
    return emails


def main():
    dry_run = "--dry-run" in sys.argv
    cognito = CognitoClient()
    client = cognito.client
    pool_id = settings.COGNITO_USER_POOL_ID

    print("=== Cleanup de usuarios sinteticos en Cognito ===")
    if dry_run:
        print("(modo dry-run: no se borra nada)\n")

    deleted = skipped = failed = 0
    for email in seed_emails():
        try:
            # Resolver el Username real por si el pool usa sub/alias en vez del email
            try:
                username = cognito._find_username_by_email(email)
            except ValueError:
                print(f"  ~ {email} (no existe, omitido)")
                skipped += 1
                continue

            if dry_run:
                print(f"  - {email} (se borraria)")
                continue

            client.admin_delete_user(UserPoolId=pool_id, Username=username)
            print(f"  x {email} borrado")
            deleted += 1
        except Exception as e:  # noqa: BLE001
            print(f"  ! {email} - error: {e}")
            failed += 1

    print(f"\n  Cognito: {deleted} borrados, {skipped} omitidos, {failed} errores")
    print("=== Completado ===")


if __name__ == "__main__":
    main()
