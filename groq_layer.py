from dotenv import load_dotenv
load_dotenv()

from groq import Groq
import ast
import os

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

SQL_SYSTEM = """You are a SQLite SQL expert. The user will give a database schema and a natural language question.
Respond ONLY with a syntactically correct SQL SELECT query.
Rules:
- Use only the tables and columns in the schema.
- Use consistent and declared table aliases (e.g. album AS a).
- Do not include explanations or code block markers.
"""

CHART_SYSTEM = """
You are a Python chart assistant. The user gives you a pandas DataFrame named `df`.
Generate valid Python code to create an interactive chart using plotly.express (imported as px).

Rules:
- Always assign the created figure to a variable named 'fig'.
- Use only DataFrame columns referenced as df['column_name'], never df.index.
- Avoid quoting numeric values. For example, use nlargest(5, 'Total') not nlargest('5', 'Total').
- Make sure all strings have matching quotes and all parentheses are properly closed.
- Avoid errors like: Chart code raised an error:
  unterminated string literal (detected at line 4) (<string>, line 4)
- Do NOT include plt.show() or any matplotlib code.
- Do NOT include markdown, code blocks, comments, or explanations — only valid Python code.
- Use appropriate plotly.express functions such as px.bar, px.line, px.scatter, etc.
- Include meaningful titles, axis labels, and legends where relevant.
- Ensure the generated code runs without syntax errors.
"""



def ask_question(question: str, schema: str) -> str:
    messages = [
        {"role": "system", "content": SQL_SYSTEM},
        {"role": "user", "content": f"{schema}\n\nQuestion: {question}"}
    ]
    res = client.chat.completions.create(model="llama3-70b-8192", messages=messages)
    return res.choices[0].message.content.strip()

def ask_for_chart(df, question: str) -> str:
    user_msg = f"df.head():\n{df.head().to_markdown()}\n\nQuestion: {question}"
    messages = [
        {"role": "system", "content": CHART_SYSTEM},
        {"role": "user", "content": user_msg}
    ]
    res = client.chat.completions.create(model="llama3-70b-8192", messages=messages)
    return res.choices[0].message.content.strip()

def generate_suggested_questions(schema: str, num_questions: int = 5) -> list:
    prompt = f"""You are a helpful assistant that generates user-friendly, concise questions based only on the database schema provided.
Ignore any SQL details or explanations.

Given this schema:

{schema}

Please provide a numbered list of {num_questions} clear, natural language questions a user might ask about this data.
Only output the questions themselves, without any explanations or additional text. Make sure that the questions are relevant 
to the schema and can be answered by querying the data.
"""
    messages = [{"role": "user", "content": prompt}]
    res = client.chat.completions.create(model="llama3-70b-8192", messages=messages)
    response = res.choices[0].message.content.strip()

    questions = []
    for line in response.splitlines():
        line = line.strip()
        if not line:
            continue
        if line[0].isdigit() and "." in line:
            parts = line.split(".", 1)
            question_text = parts[1].strip()
            if question_text:
                questions.append(question_text)

    if not questions:
        lines = [l.strip() for l in response.splitlines() if l.strip()]
        questions = [l for l in lines if "?" in l]

    if not questions:
        questions = [response]

    return questions

def ask_nlp_fallback(user_question: str, df_sample_md: str) -> str:
    prompt = f"""
You are a data analyst assistant. You are given the following snapshot of data in markdown table format:

{df_sample_md}

Based on this data, answer the question below directly by analyzing the data.

Rules:
- Do NOT generate or mention any SQL queries.
- Use the data given above to reason and answer naturally.
- Provide clear reasoning and a concise answer.
- If you cannot answer definitively from the data shown, say so.

Question: {user_question}
"""
    messages = [{"role": "user", "content": prompt}]
    res = client.chat.completions.create(model="llama3-70b-8192", messages=messages)
    return res.choices[0].message.content.strip()