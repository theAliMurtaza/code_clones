"""
create_tables.py
Run this once to create all database tables.

Usage:
    python create_tables.py
"""

from database import engine, Base
import models   # noqa: F401 — ensures all models are registered

def main():
    print("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    print("Done. Tables created:")
    for table in Base.metadata.sorted_tables:
        print(f"  ✓ {table.name}")

if __name__ == "__main__":
    main()
