import re

def validate_sql(query: str) -> tuple[bool, str]:
    """
    Validates the SQL query to ensure it is a safe SELECT statement.
    Returns (is_valid, error_message).
    """
    if not query:
        return False, "Query is empty."

    # Normalize query
    query = query.strip()
    
    # Check for empty string again after strip
    if not query:
        return False, "Query is empty."

    # 1. Reject multiple statements (semicolon check)
    # Allow a single semicolon at the end, but not in the middle
    if ';' in query[:-1]:
         return False, "Multiple statements are not allowed (semicolon detected in middle of query)."

    # 2. Strict SELECT only
    # Case-insensitive check if it starts with SELECT
    if not re.match(r'^\s*SELECT', query, re.IGNORECASE):
        return False, "Only SELECT queries are allowed."

    # 3. Block Prohibited Keywords (DML/DDL)
    # We use word boundaries \b to avoid matching substrings (e.g., 'UPDATE' in 'UPDATED_AT')
    prohibited_keywords = [
        "INSERT", "UPDATE", "DELETE", "DROP", "ALTER", 
        "ATTACH", "DETACH", "PRAGMA", "TRUNCATE", "REPLACE",
        "CREATE", "GRANT", "REVOKE", "COMMIT", "ROLLBACK", "EXEC", "EXECUTE"
    ]
    
    upper_query = query.upper()
    for keyword in prohibited_keywords:
        if re.search(r'\b' + keyword + r'\b', upper_query):
            return False, f"Prohibited keyword detected: {keyword}"

    # 4. Prevent excessive comments which might hide injection
    if '--' in query or '/*' in query:
        return False, "SQL comments are not allowed."

    return True, "Valid SQL"
