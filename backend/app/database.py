import os
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./porra_mundial.db")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
else:
    engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def run_auto_migrations(engine):
    """
    Checks the database schema against the defined SQLAlchemy models,
    and automatically adds any missing columns using ALTER TABLE.
    """
    try:
        from sqlalchemy import inspect, text
        inspector = inspect(engine)
        for table_name, table in Base.metadata.tables.items():
            if table_name not in inspector.get_table_names():
                continue
            existing_cols = {col["name"] for col in inspector.get_columns(table_name)}
            for column in table.columns:
                if column.name not in existing_cols:
                    col_type = str(column.type.compile(engine.dialect))
                    # Handle nullability and defaults
                    null_str = "NULL" if column.nullable else "NOT NULL"
                    default_str = ""
                    if column.default is not None and not callable(column.default.arg):
                        val = column.default.arg
                        if isinstance(val, bool):
                            val = 1 if val else 0
                        if isinstance(val, (int, float)):
                            default_str = f"DEFAULT {val}"
                        else:
                            default_str = f"DEFAULT '{val}'"
                    elif not column.nullable:
                        # SQLite requires a default value for NOT NULL columns added via ALTER TABLE
                        if "INT" in col_type.upper() or "BOOL" in col_type.upper():
                            default_str = "DEFAULT 0"
                        else:
                            default_str = "DEFAULT ''"
                    
                    alter_query = f"ALTER TABLE {table_name} ADD COLUMN {column.name} {col_type} {null_str} {default_str}"
                    print(f"Auto-migration: {alter_query}")
                    with engine.begin() as conn:
                        conn.execute(text(alter_query))
    except Exception as e:
        print(f"Error during auto-migration: {e}")


def get_db():
    """Dependency that yields a DB session per request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
