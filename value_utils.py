from sqlalchemy import create_engine, inspect, text
import pandas as pd

def get_distinct_values(engine, table_name, column_name, limit=5):
    """
    Fetches the top N most frequent distinct values from a column.
    Useful for giving the LLM context about what values actually exist.
    """
    try:
        query = text(f"SELECT DISTINCT {column_name} FROM {table_name} LIMIT {limit}")
        # Using pandas for safe execution and easy formatting
        df = pd.read_sql(query, engine)
        values = df[column_name].tolist()
        return values
    except Exception as e:
        return []

def enrich_schema_with_values(schema_text, engine):
    """
    Parses the schema text and appends sample values for likely categorical columns
    (Text/String types) to help the LLM understand the data content.
    """
    inspector = inspect(engine)
    enriched_schema = []
    
    # Simple parsing: assume schema_text has "Table: table_name" blocks
    # This is a naive enhancement that re-inspects the DB. 
    # A robust production version would combine this with the initial schema extraction.
    
    try:
        for table_name in inspector.get_table_names():
            columns = inspector.get_columns(table_name)
            
            # Reconstruct table header
            table_desc = [f"Table: {table_name}"]
            
            for col in columns:
                col_name = col['name']
                col_type = str(col['type']).upper()
                col_str = f"- {col_name} ({col_type})"
                
                # Heuristic: Add values for TEXT/VARCHAR columns, skip IDs/Dates
                if "TEXT" in col_type or "CHAR" in col_type:
                    values = get_distinct_values(engine, table_name, col_name)
                    if values:
                        col_str += f" (Sample Values: {', '.join(map(str, values))})"
                
                table_desc.append(col_str)
                
            # Add Foreign Keys
            fks = inspector.get_foreign_keys(table_name)
            for fk in fks:
                col = fk['constrained_columns'][0]
                ref_table = fk['referred_table']
                ref_col = fk['referred_columns'][0]
                table_desc.append(f"- Foreign Key: {col} -> {ref_table}.{ref_col}")
            
            enriched_schema.append("\n".join(table_desc))
            
        return "\n\n".join(enriched_schema)
        
    except Exception as e:
        return f"Error enriching schema: {str(e)}\n\n{schema_text}"
