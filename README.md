#  Talk to Your Data

**Talk to Your Data** is an interactive Streamlit application powered by LLMs that enables users to upload `.db`, `.csv`, or `.xlsx` files and interact with the data using natural language. The app can automatically generate SQL queries, create charts using Plotly, and suggest insightful questions based on your dataset schema.

---

##  Features

- 📂 Upload and preview SQLite, CSV, and Excel files.
- 🧠 Ask natural language questions about your data.
- 📊 Get instant charts generated using Plotly Express.
- 🤖 Toggle between SQL Query mode and AI Data Analysis mode.
- 🧾 View past chart generations in the "Chart History" tab.
- 🔮 Automatically generate smart questions from your data schema.

---

##  Project Structure

- `app.py`: Main Streamlit app file. Handles UI, file uploads, schema parsing, and interaction with the backend logic.
- `groq_layer.py`: Logic layer that uses Groq’s LLM API to:
  - Translate natural language into SQL queries.
  - Generate chart code from a dataframe.
  - Provide fallback NLP analysis when SQL is not possible.
  - Suggest relevant questions based on schema.

---

##  Dependencies

Install the following packages (recommended using a virtual environment):

```bash
pip install streamlit pandas plotly openpyxl sqlite3 pandasql
pip install groq  # Groq's official Python client
