import streamlit as st
import pandas as pd
import sqlite3
import os
import time
from sqlalchemy import create_engine
from langchain_core.prompts import PromptTemplate
from db.init_db import init_db

# Import local modules
from langchain_groq_llm import get_llm
from sql_validator import validate_sql
from chroma_manager import ChromaManager
from schema_utils import get_database_schema
from value_utils import enrich_schema_with_values, get_distinct_values
import tempfile

# Page Config
st.set_page_config(page_title="NL to SQL Generator", layout="wide")

# --- Session State ---
if "logs" not in st.session_state:
    st.session_state.logs = []

if "generated_sql" not in st.session_state:
    st.session_state.generated_sql = ""

if "indexed_db_path" not in st.session_state:
    st.session_state.indexed_db_path = None
    
if "db_path" not in st.session_state:
    st.session_state.db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "db", "demo.sqlite")

# --- Helper Functions ---
def get_db_path():
    return st.session_state.db_path

def get_engine():
    db_path = get_db_path()
    return create_engine(f"sqlite:///{db_path}")

def run_query(query):
    """Executes query securely and returns DataFrame."""
    # 1. Validate
    is_valid, msg = validate_sql(query)
    if not is_valid:
        return None, f"Validation Error: {msg}"
    
    # 2. Execute
    try:
        start_time = time.time()
        engine = get_engine()
        # Use pandas read_sql for convenience
        with engine.connect() as conn:
            df = pd.read_sql(query, conn)
        
        duration = time.time() - start_time
        
        # Log success
        st.session_state.logs.insert(0, {
            "query": query, "status": "Success", "time": f"{duration:.4f}s"
        })
        
        return df, None
        
    except Exception as e:
        # Log failure
        st.session_state.logs.insert(0, {
            "query": query, "status": "Error", "error": str(e)
        })
        return None, f"Execution Error: {str(e)}"

# --- Load Resources ---
@st.cache_resource
def get_chroma_manager():
    cm = ChromaManager()
    cm.initialize_collection()
    return cm

# --- UI Sidebar ---
with st.sidebar:
    st.title("Settings")
    
    # DB Selection
    st.subheader("Database Selection")
    uploaded_db = st.file_uploader("Upload SQLite Database (.db, .sqlite)", type=["db", "sqlite"])
    
    if uploaded_db:
        # Save uploaded file to temp
        with tempfile.NamedTemporaryFile(delete=False, suffix=".sqlite") as tmp_file:
            tmp_file.write(uploaded_db.getvalue())
            st.session_state.db_path = tmp_file.name
        st.success(f"Using uploaded database: {uploaded_db.name}")
    else:
        # Default to demo.sqlite logic
        demo_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "db", "demo.sqlite")
        st.session_state.db_path = demo_path
        
        st.info("Using Demo Database")
        with st.expander("ℹ️ About Demo Data", expanded=True):
            st.markdown("""
            **Synthetic E-Commerce Data**
            - **Customers**: 50 records (Name, City, Join Date)
            - **Orders**: 200 records (Amount, Status, Date)
            - **Relationships**: Orders linked to Customers via ID
            
            *Ideal for testing aggregation (SUM/COUNT) and joins.*
            """)

    # Model Selector
    model_name = st.selectbox("LLM Model", ["llama-3.3-70b-versatile", "meta-llama/llama-4-maverick-17b-128e-instruct", "meta-llama/llama-4-scout-17b-16e-instruct"], index=0)
    
    # Read-Only Mode Toggle (Visual only, engine enforcement is via validator)
    read_only = st.checkbox("Read-Only Mode", value=True, disabled=True, help="Enforced by Validator")
    
    if st.button("Re-initialize Database"):
        try:
            init_db()
            st.success("Database reset!")
        except Exception as e:
            st.error(f"Error: {e}")

    st.markdown("---")
    st.markdown("### Schema Info")
    if st.button("Show Schema"):
        engine = get_engine()
        inspector = sqlite3.connect(get_db_path())
        cursor = inspector.cursor()
        
        st.markdown("**Tables:**")
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        for t in tables:
            st.markdown(f"- `{t[0]}`")
            cursor.execute(f"PRAGMA table_info({t[0]})")
            cols = cursor.fetchall()
            for c in cols:
                st.caption(f"  - {c[1]} ({c[2]})")
        inspector.close()

# --- Main App ---
st.title("Natural Language to SQL")

# Tabs
tab1, tab2, tab3, tab4 = st.tabs(["Query Builder", "Manual SQL", "DB Browser", "Logs"])

# --- Tab 1: NL Query Builder ---
with tab1:
    st.markdown("### Ask a question in plain English")
    
    with st.form("nl_query_form"):
        user_question = st.text_area("Question", placeholder="e.g. Show all customers in Lahore", height=100)
        submitted = st.form_submit_button("Generate SQL")
        
    if submitted and user_question:
        try:
            # 1. Retrieve Context
            progress_text = "Retrieving context..."
            my_bar = st.progress(0, text=progress_text)
            
            cm = get_chroma_manager()
            context_docs = cm.get_relevant_context(user_question)
            context_str = "\n".join(context_docs) if isinstance(context_docs, list) else str(context_docs)
            
            my_bar.progress(30, text="Constructing prompt...")
            
            # 2. Build Prompt
            prompt_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "prompts", "nl_to_sql_prompt.txt")
            with open(prompt_path, "r") as f:
                template = f.read()
                
            # Dynamic Schema Context
            # 1. Get raw schema
            raw_schema = get_database_schema(get_db_path())
            
            # 2. Enrich with distinct values (for better filtering context)
            full_schema_context = enrich_schema_with_values(raw_schema, get_engine())
            
            # Index Schema if changed
            if st.session_state.indexed_db_path != get_db_path():
                cm = get_chroma_manager()
                cm.index_schema(full_schema_context)
                st.session_state.indexed_db_path = get_db_path()
            
            filled_prompt = template.format(
                schema_context=full_schema_context,
                retrieved_context=context_str,
                user_question=user_question
            )
            
            my_bar.progress(60, text="Querying LLM...")
            
            # 3. Call LLM
            llm = get_llm(model_name)
            response = llm.invoke(filled_prompt)
            generated_sql = response.content.strip()
            
            # Clean generated SQL
            # 1. Remove Markdown code blocks
            if generated_sql.startswith("```"):
                generated_sql = generated_sql.split("```")[1].strip()
            if generated_sql.lower().startswith("sql"):
                generated_sql = generated_sql[3:].strip()
            
            # Clean generated SQL - Robust Strategy
            reasoning = ""
            
            # 1. Separator Logic (Best Case)
            if "### SQL START ###" in generated_sql:
                parts = generated_sql.split("### SQL START ###")
                reasoning = parts[0].strip()
                generated_sql = parts[1].strip()
            
            # 2. Fallback: Extract logic starting from SELECT if separator missing
            elif "SELECT" in generated_sql.upper():
                # Heuristic: Find last occurrence of SELECT if multiple? Or first?
                # Usually logic is before code.
                idx = generated_sql.upper().find("SELECT")
                # Check if there is text before SELECT that looks like comments/reasoning
                pre_text = generated_sql[:idx].strip()
                if len(pre_text) > 5: # If significant text before SELECT
                   reasoning = pre_text
                generated_sql = generated_sql[idx:]
            
            # 3. Clean remaining non-sql lines from the SQL part
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
                
            # Display Reasoning if present
            if reasoning:
                with st.expander("Show Logic / Reasoning"):
                    st.write(reasoning.replace("/*", "").replace("*/", "").strip())
                
            st.session_state.generated_sql = generated_sql
            my_bar.progress(100, text="Done!")
            time.sleep(0.5)
            my_bar.empty()
            
        except Exception as e:
            st.error(f"Error generating SQL: {e}")

    # Display Generated SQL and Run Button (Outside form to allow interactivity)
    if st.session_state.generated_sql:
        st.markdown("#### Generated SQL")
        st.code(st.session_state.generated_sql, language="sql")
        
        if st.session_state.generated_sql == "CANNOT_ANSWER":
            st.warning("The model determined it cannot answer this question with the available schema.")
        else:
            col1, col2 = st.columns([1, 5])
            with col1:
                if st.button("Run Query", key="run_gen"):
                    df, error = run_query(st.session_state.generated_sql)
                    if error:
                        st.error(error)
                    else:
                        st.success(f"Query executed in {st.session_state.logs[0]['time']}")
                        st.dataframe(df, use_container_width=True, hide_index=True)

# --- Tab 2: Manual SQL ---
with tab2:
    st.markdown("### Execute Custom SQL")
    manual_sql = st.text_area("SQL Query", value="SELECT * FROM customers LIMIT 5;", height=150)
    
    if st.button("Run Manual Query"):
        df, error = run_query(manual_sql)
        if error:
            st.error(error)
        else:
            st.success("Query executed successfully")
            st.dataframe(df, use_container_width=True, hide_index=True)

# --- Tab 3: DB Browser ---
with tab3:
    st.markdown("### Database Browser")
    
    # Table List
    try:
        engine = get_engine()
        conn = engine.connect()
        # Use inspection for robust table listing
        from sqlalchemy import inspect
        inspector = inspect(engine)
        table_names = inspector.get_table_names()
        
        selected_table = st.selectbox("Select Table", table_names)
        
        if selected_table:
            st.write(f"Previewing table: **{selected_table}**")
            # Show columns
            columns = [col['name'] for col in inspector.get_columns(selected_table)]
            st.caption(f"Columns: {', '.join(columns)}")
            
            # Show data
            df = pd.read_sql(f"SELECT * FROM {selected_table} LIMIT 10", conn)
            st.dataframe(df, use_container_width=True, hide_index=True)
            
        conn.close()
    except Exception as e:
        st.error(f"Error browsing database: {e}")

# --- Tab 4: Logs ---
with tab4:
    st.markdown("### Execution Logs")
    if st.session_state.logs:
        for i, log in enumerate(st.session_state.logs):
            with st.expander(f"{log['status']}: {log['query'][:50]}...", expanded=(i==0)):
                st.write(f"**Query:**")
                st.code(log['query'], language="sql")
                if 'time' in log:
                    st.write(f"**Duration:** {log['time']}")
                if 'error' in log:
                    st.error(f"**Error:** {log['error']}")
    else:
        st.info("No queries executed yet.")
