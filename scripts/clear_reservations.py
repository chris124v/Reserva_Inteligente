"""Utility script to delete all reservations from the database.

This is intentionally not run automatically.

Usage:
  python scripts/clear_reservations.py --yes

It will delete rows from the 'reservations' table.
"""

from __future__ import annotations

import argparse

from sqlalchemy import text

from app.database.connection import engine


def main() -> None:
    parser = argparse.ArgumentParser(description="Delete all reservations from the database")
    parser.add_argument("--yes", action="store_true", help="Confirm deletion")
    args = parser.parse_args()

    if not args.yes:
        raise SystemExit("Refusing to run without --yes")

    with engine.begin() as conn:
        conn.execute(text("DELETE FROM reservations"))

    print("All reservations deleted.")


if __name__ == "__main__":
    main()
