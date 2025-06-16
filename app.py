import streamlit as st
import pandas as pd
import sqlite3
import tempfile
import textwrap
import plotly.express as px

from groq_layer import ask_question, ask_for_chart, ask_nlp_fallback, generate_suggested_questions

st.set_page_config(page_title="Talk to Your Data", layout="wide")
st.title("🧠 Talk to Your Data")

# Initialize session state keys
target_keys = ["chart_history", "suggested_questions", "user_question"]
for key in target_keys:
    if key not in st.session_state:
        if key in ("chart_history", "suggested_questions"):
            st.session_state[key] = []
        else:
            st.session_state[key] = ""

# Main tabs for Query and History
tabs = st.tabs(["📝 Query", "📊 Chart History"])

# Utility to run and save chart
def _run_and_save_chart(code, df, question):
    namespace = {"df": df, "px": px}
    exec(textwrap.dedent(code), namespace)
    fig = namespace.get("fig")
    if fig:
        st.session_state.chart_history.append({"question": question, "code": code, "fig": fig})
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("No figure named 'fig' returned by the code.")

with tabs[0]:
    uploaded_file = st.file_uploader("Upload a .db, .csv, or .xlsx file", type=["db", "csv", "xlsx"])
    conn = None
    dfs = {}
    schema_text = ""
    table_names = []

    if uploaded_file:
        file_type = uploaded_file.name.split('.')[-1].lower()
        tmp_file = tempfile.NamedTemporaryFile(delete=False, suffix=f".{file_type}")
        tmp_file.write(uploaded_file.getvalue())
        tmp_file.close()

        with st.spinner("Processing file..."):
            if file_type == "db":
                conn = sqlite3.connect(tmp_file.name)
                def get_sqlite_schema(conn):
                    schema = ""
                    cursor = conn.cursor()
                    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
                    tables = cursor.fetchall()
                    for (table_name,) in tables:
                        sample = pd.read_sql_query(f"SELECT * FROM {table_name} LIMIT 5", conn)
                        dfs[table_name] = pd.read_sql_query(f"SELECT * FROM {table_name}", conn)
                        schema += f"Table {table_name} (sample and types):\n"
                        schema += sample.to_markdown(index=False) + "\n"
                        schema += ", ".join(f"{col} ({dfs[table_name][col].dtype})" for col in dfs[table_name].columns) + "\n\n"
                    return schema, list(dfs.keys())
                schema_text, table_names = get_sqlite_schema(conn)

            elif file_type == "csv":
                df = pd.read_csv(tmp_file.name)
                dfs["csv_data"] = df
                schema_text = "Table csv_data (sample and types):\n" + df.head().to_markdown(index=False) + "\n"
                schema_text += ", ".join(f"{col} ({df[col].dtype})" for col in df.columns) + "\n\n"
                table_names = ["csv_data"]

            elif file_type == "xlsx":
                xls = pd.ExcelFile(tmp_file.name)
                for sheet in xls.sheet_names:
                    df = xls.parse(sheet)
                    dfs[sheet] = df
                    schema_text += f"Table {sheet} (sample and types):\n" + df.head().to_markdown(index=False) + "\n"
                    schema_text += ", ".join(f"{col} ({df[col].dtype})" for col in df.columns) + "\n\n"
                table_names = list(dfs.keys())
        st.success("File uploaded and processed successfully!")

        # Table preview & mode selection
        col1, col2 = st.columns([3,1])
        with col1:
            selected_table = st.selectbox("Choose a table to preview", table_names)
            st.dataframe(dfs[selected_table])
        with col2:
            mode = st.radio("Choose query mode:", ["SQL Query Mode", "AI Data Analysis Mode"], key="mode_select")

        # Suggested questions as buttons
        with st.expander("💡 Suggested questions"):
            if not st.session_state.suggested_questions:
                with st.spinner("Generating suggested questions..."):
                    st.session_state.suggested_questions = generate_suggested_questions(schema_text)
            for i, q in enumerate(st.session_state.suggested_questions):
                if st.button(q, key=f"suggest_{i}"):
                    st.session_state.user_question = q

        # Stateful user input
        user_question = st.text_input(
            "Ask a question about the uploaded data:",
            value=st.session_state.user_question,
            key="user_question"
        )

        if user_question:
            if mode == "SQL Query Mode":
                df_result = None
                # Generate and show SQL result
                try:
                    sql_query = ask_question(user_question, schema_text)
                    with st.spinner("Running SQL query..."):
                        if conn:
                            df_result = pd.read_sql_query(sql_query, conn)
                        else:
                            import pandasql
                            df_result = pandasql.sqldf(sql_query, dfs)
                    st.subheader("AI Answer")
                    st.dataframe(df_result)
                except Exception:
                    st.subheader("AI Answer")
                    nlp_answer = ask_nlp_fallback(user_question, schema_text)
                    st.markdown(nlp_answer)

                # Always offer chart generation if there's data
                if df_result is not None and not df_result.empty:
                    if st.checkbox("Generate chart from result?", key="sql_chart"):
                        chart_code = ask_for_chart(df_result, user_question)
                        st.subheader("Generated Chart")
                        st.code(chart_code, language="python")
                        _run_and_save_chart(chart_code, df_result, user_question)

            else:
                # AI Data Analysis Mode
                st.subheader("AI Answer (Direct Data Analysis)")
                sample_md = dfs[selected_table].head(20).to_markdown(index=False)
                nlp_response = ask_nlp_fallback(user_question, sample_md)
                st.markdown(nlp_response)
                if st.checkbox("Generate chart from data analysis?", key="ai_chart"):
                    chart_code = ask_for_chart(dfs[selected_table], user_question)
                    st.subheader("Generated Chart")
                    st.code(chart_code, language="python")
                    _run_and_save_chart(chart_code, dfs[selected_table], user_question)

with tabs[1]:
    st.header("📊 Your Chart History")
    if st.session_state.chart_history:
        for idx, entry in enumerate(reversed(st.session_state.chart_history)):
            st.markdown(f"**Q#{len(st.session_state.chart_history)-idx}:** {entry['question']}")
            with st.expander("View Chart"):
                st.code(entry["code"], language="python")
                st.plotly_chart(entry["fig"], use_container_width=True)
    else:
        st.info("No charts have been generated this session.")