from dotenv import load_dotenv
import streamlit as st
import os
from groq import Groq

# Load environment variables (local development)
load_dotenv()  

# Fetch API key (priority: .env > Streamlit secrets)
GROQ_API_KEY = os.getenv("GROQ_API_KEY") or st.secrets.get("GROQ_API_KEY")

# Initialize client only if the key exists (prevent crashes)
try:
    client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None
except Exception as e:
    st.error(f"❌ Failed to initialize Groq client: {e}")
    client = None  # Graceful fallback

SQL_SYSTEM = """
You are a SQLite SQL expert. If the user's question is ambiguous, ask exactly one clarifying question instead of SQL. Otherwise, think step by step, and respond ONLY with a syntactically correct SQL SELECT query.
Use only the tables and columns in the schema. Use consistent aliases. Do NOT include explanations.
Example:
Schema:
Table sales(id INT, amount FLOAT, region TEXT)
Question: What is the total sales amount?
SQL: SELECT SUM(amount) AS total_sales FROM sales;
"""

CHART_SYSTEM = """
You are a Python chart assistant. Think step by step, then generate valid Python code to create an interactive chart using plotly.express (imported as px). The user gives a pandas DataFrame named df.
Rules:
- Assign the figure to variable 'fig'.
- Reference columns as df['column_name'].
- No matplotlib or plt.show().
- No markdown, comments, or explanations.
- Include titles and axis labels.

Rules: - Always assign the created figure to a variable named 'fig'. 
- Use only DataFrame columns referenced as df['column_name'], never df.index.
 - Avoid quoting numeric values. For example, use nlargest(5, 'Total') not nlargest('5', 'Total').
 - Make sure all strings have matching quotes and all parentheses are properly closed. 
- Avoid errors like: Chart code raised an error: unterminated string literal (detected at line 4) (<string>, line 4) 
- Do NOT include plt.show() or any matplotlib code. 
- Do NOT include markdown, code blocks, comments, or explanations — only valid Python code. 
- Use appropriate plotly.express functions such as px.bar, px.line, px.scatter, etc. - Include meaningful titles, axis labels, and legends where relevant.
 - Ensure the generated code runs without syntax errors.
"""


def ask_question(question: str, schema: str, temperature: float = 0.2) -> str:
    messages = [
        {"role": "system", "content": SQL_SYSTEM},
        {"role": "user", "content": f"{schema}\n\nQuestion: {question}"}
    ]
    res = client.chat.completions.create(
        model="llama3-70b-8192",
        messages=messages,
        temperature=temperature
    )
    return res.choices[0].message.content.strip()


def ask_for_chart(df, question: str, temperature: float = 0.2) -> str:
    sample = df.head().to_markdown(index=False)
    messages = [
        {"role": "system", "content": CHART_SYSTEM},
        {"role": "user", "content": f"df.head():\n{sample}\n\nQuestion: {question}"}
    ]
    res = client.chat.completions.create(
        model="llama3-70b-8192",
        messages=messages,
        temperature=temperature
    )
    return res.choices[0].message.content.strip()


def generate_suggested_questions(schema: str, num_questions: int = 5) -> list:
    prompt = f"""You are a helpful assistant that generates concise questions based on the database schema. Ignore SQL details.\nSchema:\n{schema}\nProvide {num_questions} natural language questions a user might ask. Output only the questions."""
    messages = [{"role": "user", "content": prompt}]
    res = client.chat.completions.create(
        model="llama3-70b-8192",
        messages=messages
    )
    lines = [l.strip() for l in res.choices[0].message.content.splitlines() if l.strip()]
    questions = []
    for line in lines:
        if line[0].isdigit() and "." in line:
            questions.append(line.split(".", 1)[1].strip())
        elif "?" in line:
            questions.append(line)
    return questions


def ask_nlp_fallback(user_question: str, df_sample_md: str) -> str:
    prompt = f"""
You are a data analyst assistant. Use the following snapshot of data:\n{df_sample_md}\nAnswer the question concisely. If unclear, say so.\nQuestion: {user_question}
"""
    messages = [{"role": "user", "content": prompt}]
    res = client.chat.completions.create(
        model="llama3-70b-8192",
        messages=messages
    )
    return res.choices[0].message.content.strip()