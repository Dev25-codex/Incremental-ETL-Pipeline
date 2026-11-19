from pathlib import Path
from database import engine
from sqlalchemy import text

# SQL schema file location
BASE_DIR = Path(__file__).resolve().parents[2]

SQL_FILE = BASE_DIR / "sql" / "use_case_02_schema.sql"

try:
    # Read SQL file
    with open(SQL_FILE, "r", encoding="utf-8") as file:
        sql_script = file.read()

    # Execute SQL statements
    statements = [
        statement.strip()
        for statement in sql_script.split(";")
        if statement.strip()
    ]

    with engine.begin() as connection:
        for statement in statements:
            connection.execute(text(statement))

    print("Use Case 2 Schema Created Successfully!")

except Exception as e:
    print("Schema Creation Failed:", e)

finally:
    engine.dispose()