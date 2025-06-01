import streamlit as st
import pandas as pd
import sqlite3
import tempfile
import textwrap
import plotly.express as px

from groq_layer import ask_question, ask_for_chart, ask_nlp_fallback, generate_suggested_questions

st.set_page_config(page_title="Talk to Your Data", layout="wide")
st.title("🧠 Talk to Your Data")

# Page selection
page = st.sidebar.radio("Go to", ["Home", "Chart History"])

# Initialize chart history and suggested questions
if "chart_history" not in st.session_state:
    st.session_state["chart_history"] = []
if "suggested_questions" not in st.session_state:
    st.session_state["suggested_questions"] = []


def maybe_generate_chart(df, question):
    if st.checkbox("Generate chart from result?"):
        chart_code = ask_for_chart(df, question)

        st.subheader("Generated Chart")
        st.code(chart_code, language="python")

        try:
            namespace = {"df": df, "px": px}
            exec(textwrap.dedent(chart_code), namespace)
            fig = namespace.get("fig")
            if fig:
                st.session_state["chart_history"].append({
                    "question": question,
                    "code": chart_code,
                    "fig": fig
                })
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.warning("No figure named 'fig' was returned by the code.")
        except Exception as e:
            st.error(f"Chart code raised an error:\n\n{e}")


if page == "Home":
    uploaded_file = st.file_uploader("Upload a .db, .csv, or .xlsx file", type=["db", "csv", "xlsx"])

    conn = None
    dfs = {}
    schema_text = ""

    if uploaded_file:
        file_type = uploaded_file.name.split(".")[-1].lower()
        tmp_file = tempfile.NamedTemporaryFile(delete=False, suffix="." + file_type)
        tmp_file.write(uploaded_file.getvalue())
        tmp_file.close()

        if file_type == "db":
            conn = sqlite3.connect(tmp_file.name)

            def get_sqlite_schema(conn):
                schema = ""
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
                tables = cursor.fetchall()
                for (table_name,) in tables:
                    df = pd.read_sql_query(f"SELECT * FROM {table_name} LIMIT 100", conn)
                    dfs[table_name] = df
                    schema += f"Table {table_name}:\n"
                    schema += ", ".join(f"{col} ({df[col].dtype})" for col in df.columns)
                    schema += "\n\n"
                return schema, list(dfs.keys())

            schema_text, table_names = get_sqlite_schema(conn)

        elif file_type == "csv":
            df = pd.read_csv(tmp_file.name)
            dfs["csv_data"] = df
            schema_text = "Table csv_data:\n" + ", ".join(f"{col} ({df[col].dtype})" for col in df.columns)
            table_names = ["csv_data"]

        elif file_type == "xlsx":
            xls = pd.ExcelFile(tmp_file.name)
            for sheet in xls.sheet_names:
                dfs[sheet] = xls.parse(sheet)
            schema_text = ""
            for sheet, df in dfs.items():
                schema_text += f"Table {sheet}:\n" + ", ".join(f"{col} ({df[col].dtype})" for col in df.columns) + "\n\n"
            table_names = list(dfs.keys())

        st.success("File uploaded and processed successfully!")

        selected_table = st.selectbox("Choose a table to preview", table_names)
        st.dataframe(dfs[selected_table])

        if not st.session_state["suggested_questions"]:
            with st.spinner("Generating smart questions..."):
                st.session_state["suggested_questions"] = generate_suggested_questions(schema_text)

        selected_question = st.selectbox("💡 Suggested questions", [""] + st.session_state["suggested_questions"])
        default_text = selected_question if selected_question else ""
        user_question = st.text_input("Ask a question about the uploaded data:", value=default_text)

        mode = st.radio(
            "Choose query mode:",
            ("Smart Query Mode", "AI Insights Mode")
        )

        if user_question:
            if mode == "Smart Query Mode":
                try:
                    sql_query = ask_question(user_question, schema_text)

                    if conn:
                        df = pd.read_sql_query(sql_query, conn)
                    else:
                        import pandasql
                        df = pandasql.sqldf(sql_query, {name: dfs[name] for name in dfs})

                    if df is not None and not df.empty:
                        st.subheader("AI Answer")
                        st.dataframe(df)
                        maybe_generate_chart(df, user_question)
                    else:
                        st.subheader("AI Answer")
                        nlp_answer = ask_nlp_fallback(user_question, schema_text)
                        st.markdown(nlp_answer)

                except Exception as e:
                    st.subheader("AI Answer")
                    nlp_answer = ask_nlp_fallback(user_question, schema_text)
                    st.markdown(nlp_answer)

            else:  # AI Insights Mode
                st.subheader("AI Answer (Direct Data Analysis)")
                sample_md = dfs[selected_table].head(20).to_markdown()
                nlp_response = ask_nlp_fallback(user_question, sample_md)
                st.markdown(nlp_response)
                maybe_generate_chart(dfs[selected_table], user_question)

# --- CHART HISTORY PAGE ---
elif page == "Chart History":
    st.header("📊 Your Chart History")

    if st.session_state["chart_history"]:
        for idx, entry in enumerate(reversed(st.session_state["chart_history"])):
            st.markdown(f"**Q#{len(st.session_state['chart_history']) - idx}:** {entry['question']}")
            with st.expander("View Chart"):
                st.code(entry["code"], language="python")
                st.plotly_chart(entry["fig"], use_container_width=True)
    else:
        st.info("No charts have been generated yet in this session.")
