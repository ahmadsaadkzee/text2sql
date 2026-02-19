import chromadb
from chromadb.utils import embedding_functions
import os

class ChromaManager:
    def __init__(self, persist_dir="chroma_db"):
        self.persist_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), persist_dir)
        self.client = chromadb.PersistentClient(path=self.persist_dir)
        
        # Use a standard, free embedding model (all-MiniLM-L6-v2)
        # We use the built-in Chroma sentence transformer embedding function
        self.embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")
        
        self.collection_name = "sql_schema_context"
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            embedding_function=self.embedding_fn
        )

    def initialize_collection(self):
        """
        Embeds generic SQL logic and examples. 
        Specific schema context is now handled dynamically or via populate_schema().
        """
        # Check if already populated with generic logic
        results = self.collection.get(where={"type": "logic"})
        if len(results['ids']) > 0:
            return

        documents = [
            # Common Queries / Logic (DB Agnostic)
            "To calculate total, use SUM(column).",
            "To count items, use COUNT(column).",
            "To filter results, use WHERE column = 'value'.",
            "To sort results, use ORDER BY column DESC/ASC.",
            "To group data, use GROUP BY column.",
            "To limit results, use LIMIT N.",
            "For 'top N per category', use window function: RANK() OVER (PARTITION BY category ORDER BY val DESC).",
            "For recursive hierarchies (e.g. org chart), use WITH RECURSIVE cte AS (...).",
            "For moving averages, use AVG(val) OVER (ORDER BY date ROWS BETWEEN 6 PRECEDING AND CURRENT ROW).",
            "For year-over-year growth, use LAG(val) OVER (ORDER BY date)."
        ]
        
        metadatas = [{"type": "logic", "topic": "generic_sql"} for _ in documents]
        ids = [f"logic_{i}" for i in range(len(documents))]

        print("Populating ChromaDB with generic logic...")
        self.collection.add(
            documents=documents,
            metadatas=metadatas,
            ids=ids
        )
        print("ChromaDB generic logic populated.")

    def index_schema(self, schema_text):
        """
        Dynamically indexes the provided schema text.
        Previous schema entries are removed to avoid hallucinations.
        """
        # 1. Delete old schema entries
        try:
            self.collection.delete(where={"type": "schema"})
        except:
            pass # Collection might be empty or filter not found

        # 2. Chunk schema (simple split by table for now)
        # Assuming schema_text is formatted with "Table: name"
        chunks = schema_text.split("Table: ")
        documents = []
        metadatas = []
        ids = []
        
        for i, chunk in enumerate(chunks):
            if not chunk.strip():
                continue
            table_name = chunk.split("\n")[0].strip()
            full_chunk = f"Table: {chunk}"
            documents.append(full_chunk)
            metadatas.append({"type": "schema", "table": table_name})
            ids.append(f"schema_{table_name}_{i}")
            
        if documents:
            self.collection.add(documents=documents, metadatas=metadatas, ids=ids)
            print(f"Indexed {len(documents)} schema chunks.")

    def get_relevant_context(self, query, n_results=3):
        """
        Retrieves top relevant schema/logic snippets for a given NL query.
        """
        results = self.collection.query(
            query_texts=[query],
            n_results=n_results
        )
        
        # Flatten results list
        if results and results['documents']:
            return results['documents'][0]
        return []

if __name__ == "__main__":
    # Test/Initialize
    cm = ChromaManager()
    cm.initialize_collection()
    print("Test Search 'revenue':", cm.get_relevant_context("What is the total revenue?"))
