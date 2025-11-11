# create_tables.py
from database import engine, Base
# import models to register tables with Base
import models  # noqa: F401

if __name__ == "__main__":
    print("Creating tables (if not exist)...")
    Base.metadata.create_all(bind=engine)
    print("Done.")
