
import sys
import os
import sqlite3
from typing import List

# Add parent dir to path to import app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from langchain_groq_llm import get_llm
from chroma_manager import ChromaManager
from schema_utils import get_database_schema
from value_utils import enrich_schema_with_values
from sqlalchemy import create_engine

# Configuration
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "db", "demo.sqlite")
MODEL_NAME = "llama-3.3-70b-versatile"

TEST_QUERIES = [
    # Medium Complexity (Joins, Aggregations, Filtering)
    "1. Get the total revenue from all orders.",
    "2. List all customers who live in 'New York'.",
    "3. Count the number of orders for each status.",
    "4. Find the customer name with the highest total order amount.",
    "5. List all orders placed in 2023.",
    "6. Calculate the average order amount.",
    "7. Find customers who have placed more than 1 order.",
    "8. List all 'Pending' orders along with the customer name.",
    "9. What is the total revenue per city?",
    "10. Find the customer who placed the earliest order.",

    # High Complexity (Window Functions, CTEs, Recursive, Complex Filtering)
    "11. Rank customers by their total spending (highest first).",
    "12. Calculate the running total of revenue ordered by date.",
    "13. Find the top 2 customers in each city by revenue.",
    "14. Identify customers who have NOT placed any orders.",
    "15. Calculate the month-over-month revenue growth.",
    "16. detailed list of all orders with customer name and formatted date (YYYY-MM-DD).",
    "17. Who are the customers with orders above the average order amount?",
    "18. List distinct statuses used in orders.",
    "19. Count how many customers joined in each month of 2023.",
    "20. Find orders where the amount is greater than the average amount for that specific customer."
]

def run_tests():
    print(f"Running tests on DB: {DB_PATH}")
    
    # Setup Context
    engine = create_engine(f"sqlite:///{DB_PATH}")
    raw_schema = get_database_schema(DB_PATH)
    full_schema_context = enrich_schema_with_values(raw_schema, engine)
    
    cm = ChromaManager()
    
    llm = get_llm(MODEL_NAME)
    
    # Load Prompt Template
    prompt_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "prompts", "nl_to_sql_prompt.txt")
    with open(prompt_path, "r") as f:
        template = f.read()

    passed = 0
    failed = 0
    results = []

    for i, question in enumerate(TEST_QUERIES):
        print(f"\nScanning Q{i+1}: {question}")
        
        try:
            # 1. Retrieval
            context = cm.get_relevant_context(question)
            context_str = "\n".join(context)
            
            # 2. Prompting
            filled_prompt = template.format(
                schema_context=full_schema_context,
                retrieved_context=context_str,
                user_question=question
            )
            
            # 3. Generation
            response = llm.invoke(filled_prompt)
            generated_sql = response.content.strip()
            
            # Clean generated SQL - Robust Strategy
            
            # 1. Separator Logic (Best Case)
            if "### SQL START ###" in generated_sql:
                parts = generated_sql.split("### SQL START ###")
                generated_sql = parts[1].strip()
            
            # 2. Extract logic starting from SELECT
            elif "SELECT" in generated_sql.upper():
                idx = generated_sql.upper().find("SELECT")
                generated_sql = generated_sql[idx:]
            
            # 3. Clean remaining non-sql lines (trailing explanations)
            lines = generated_sql.split('\n')
            cleaned_lines = []
            for line in lines:
                if line.strip().startswith("Note:") or line.strip().startswith("Explanation:"):
                    break
                if not line.strip().startswith("--") and not line.strip().startswith("/*"):
                    cleaned_lines.append(line)
            generated_sql = "\n".join(cleaned_lines).strip()
            
            # 4. Final semicolon fix
            if ";" in generated_sql:
                generated_sql = generated_sql.split(";")[0] + ";"

            print(f"Generated SQL: {generated_sql}")
            
            # 4. Execution (Validation)
            with sqlite3.connect(DB_PATH) as conn:
                cursor = conn.cursor()
                cursor.execute(generated_sql)
                rows = cursor.fetchall()
                print(f"Result: {len(rows)} rows returned.")
                passed += 1
                results.append({"q": question, "status": "PASS", "sql": generated_sql})
                
        except Exception as e:
            print(f"FAILED: {str(e)}")
            failed += 1
            results.append({"q": question, "status": "FAIL", "error": str(e)})

    print("\n" + "="*30)
    print(f"Final Report: {passed}/{len(TEST_QUERIES)} Passed")
    print("="*30)
    
    # Save detailed report
    with open("tests/test_results.txt", "w") as f:
        for res in results:
            f.write(f"Q: {res['q']}\nStatus: {res['status']}\n")
            if "sql" in res:
                f.write(f"SQL: {res['sql']}\n")
            if "error" in res:
                f.write(f"Error: {res['error']}\n")
            f.write("-" * 20 + "\n")

if __name__ == "__main__":
    run_tests()
