# NL to SQL Streamlit App

This is a local Streamlit application that converts natural language questions into secure SQL queries using LangChain, Groq, and SQLite.

## Features

- **Dynamic Database Support**: Upload your own SQLite database or use the demo.
- **Real-time Schema Extraction**: The system understands your specific database structure automatically.
- **NL Query Builder**: Convert natural language to SQL and execute it.
- **Manual SQL**: Write and execute custom SQL queries with safety validation.
- **DB Browser**: Explore the database schema and data.
- **Safety**: strict SELECT-only enforcement, preventing destructive operations.
- **Schema Context**: Optional integration with ChromaDB to improve query generation.
- **Complex Logic Support**: Handles Window Functions, CTEs, and advanced Date Math.
- **Reasoning Display**: Shows the LLM's thought process for transparency.

## Setup Instructions

1.  **Create Virtual Environment**:
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```

2.  **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

3.  **Environment Configuration**:
    - The `.env` file is pre-configured with the provided API key for local development.
    - **Security Note**: Never commit `.env` to version control.

4.  **Launch Application**:
    ```bash
    streamlit run app.py
    ```
    Then use the sidebar to upload your own `.sqlite` or `.db` file.

## Usage

- **NL Query Tab**: Enter a question like "Show all customers in Lahore" or "Total revenue in 2025". Click "Generate SQL" to see the query, then "Run Query" to execute it.
- **Manual SQL Tab**: Write custom SQL. Validation will block non-SELECT statements.
- **DB Browser Tab**: View table structures and data.

## Troubleshooting

- **API Key Errors**: Ensure `GROQ_API_KEY` is set in `.env` or Streamlit secrets.
- **Database Errors**: Run `python db/init_db.py` to reset the database.

## GitHub Setup

1.  Initialize Git:
    ```bash
    git init
    git add .
    git commit -m "Initial commit: NL to SQL App with Complex Query Support"
    ```
2.  Push to GitHub:
    ```bash
    git remote add origin <your-repo-url>
    git branch -M main
    git push -u origin main
    ```
