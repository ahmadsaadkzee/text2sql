import sqlite3
from sqlalchemy import create_engine, inspect

def get_database_schema(db_path: str) -> str:
    """
    Connects to the SQLite database at db_path and returns a string 
    describing the schema (tables, columns, types).
    """
    try:
        # Create engine
        engine_url = f"sqlite:///{db_path}"
        engine = create_engine(engine_url)
        inspector = inspect(engine)
        
        # Get all table names
        table_names = inspector.get_table_names()
        
        schema_parts = []
        for table_name in table_names:
            # Columns
            columns = inspector.get_columns(table_name)
            col_strings = [f"- {col['name']} ({str(col['type'])})" for col in columns]
            
            # Foreign Keys
            fks = inspector.get_foreign_keys(table_name)
            fk_strings = []
            for fk in fks:
                # Format: fk_col -> referred_table.referred_col
                fk_col = fk['constrained_columns'][0]
                ref_table = fk['referred_table']
                ref_col = fk['referred_columns'][0]
                fk_strings.append(f"- Foreign Key: {fk_col} -> {ref_table}.{ref_col}")
            
            # Combine into table description
            table_desc = f"Table: {table_name}\n" + "\n".join(col_strings + fk_strings)
            schema_parts.append(table_desc)
            
        return "\n\n".join(schema_parts)
        
    except Exception as e:
        return f"Error extracting schema: {str(e)}"

if __name__ == "__main__":
    # Test
    import os
    db_path = os.path.join("db", "demo.sqlite")
    if os.path.exists(db_path):
        print(get_database_schema(db_path))
    else:
        print(f"Database not found at {db_path}")
