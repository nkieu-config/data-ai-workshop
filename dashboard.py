import os
import streamlit as st
import duckdb
import pandas as pd
import google.generativeai as genai
import numpy as np

# Page Config
st.set_page_config(
    page_title="TU Student Analytics Dashboard",
    page_icon="🎓",
    layout="wide"
)

st.title("🎓 Thammasat Student Analytics & Pipeline Audit Dashboard")

with st.sidebar:
    st.header("⚙️ Settings")
    gemini_api_key = st.text_input("Gemini API Key", type="password", help="Enter your Google Gemini API key to enable real LLM RAG Q&A.")
    if gemini_api_key:
        st.success("API Key provided.")
    else:
        st.warning("Provide API Key for full RAG feature.")

st.markdown("This dashboard displays insights from the **Trusted Layer** inside our DuckDB database, populated by our idempotent batch pipeline.")

db_path = "data/trusted_database.db"

# Check if DB exists
if not os.path.exists(db_path):
    st.error("❌ Database file not found. Please run the pipeline script first to ingest data.")
    st.info("Run command: `python3 pipeline.py --business-date 2026-06-28 --run-id FIRST_RUN`")
else:
    con = duckdb.connect(db_path, read_only=True)

@st.cache_data(show_spinner="Embedding student database for Semantic Search...")
def get_cached_embeddings(api_key, _con):
    genai.configure(api_key=api_key)
    # Fetch all records
    df = _con.execute("SELECT source_row_no, student_no, rag_document_title, rag_document_text, source_url FROM trusted_student_snapshot").df()
    texts = df['rag_document_text'].tolist()
    # Call Gemini embedding API
    response = genai.embed_content(model="models/text-embedding-004", content=texts)
    embeddings = np.array(response['embedding'])
    return df, embeddings
    
    # ----------------------------------------------------
    # Metrics
    # ----------------------------------------------------
    metrics = con.execute("""
        SELECT 
            COUNT(*), 
            AVG(gpa), 
            AVG(expected_salary_thb), 
            AVG(credit_earned) 
        FROM trusted_student_snapshot
    """).fetchone()
    
    total_students, avg_gpa, avg_salary, avg_credits = metrics
    
    # Create Tabs
    tab1, tab2, tab3, tab4 = st.tabs(["📊 Analytics Dashboard", "📋 Audit Logs", "🤖 RAG Q&A", "💾 SQL Explorer"])
    
    with tab1:
        # ----------------------------------------------------
        # Metrics
        # ----------------------------------------------------
        metrics = con.execute("""
            SELECT 
                COUNT(*), 
                AVG(gpa), 
                AVG(expected_salary_thb), 
                AVG(credit_earned) 
            FROM trusted_student_snapshot
        """).fetchone()
        
        total_students, avg_gpa, avg_salary, avg_credits = metrics
        
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Students", f"{total_students} rows")
        col2.metric("Average GPA", f"{avg_gpa:.2f}")
        col3.metric("Average Expected Salary", f"{avg_salary:,.0f} THB")
        col4.metric("Average Credits Earned", f"{avg_credits:.1f}")
        
        st.markdown("---")
        
        # ----------------------------------------------------
        # Charts Layout
        # ----------------------------------------------------
        left_col, right_col = st.columns(2)
        
        with left_col:
            st.subheader("💼 Career Interests Distribution")
            career_df = con.execute("""
                SELECT career_interest, COUNT(*) as count 
                FROM trusted_student_snapshot 
                GROUP BY career_interest
                ORDER BY count DESC
            """).df()
            st.bar_chart(data=career_df.set_index('career_interest'))
            
            st.subheader("🏫 Campus Breakdown")
            campus_df = con.execute("""
                SELECT campus, COUNT(*) as count 
                FROM trusted_student_snapshot 
                GROUP BY campus
            """).df()
            st.dataframe(campus_df, use_container_width=True)
    
        with right_col:
            st.subheader("📈 GPA Distribution (Undergrad vs Postgrad)")
            gpa_df = con.execute("""
                SELECT level, gpa 
                FROM trusted_student_snapshot
            """).df()
            
            # Simple pivot or grouping for display
            st.scatter_chart(data=gpa_df, x='gpa', y='level', color='level')
            
            st.subheader("🎓 Level of Study Breakdown")
            level_df = con.execute("""
                SELECT level, COUNT(*) as count 
                FROM trusted_student_snapshot 
                GROUP BY level
            """).df()
            st.dataframe(level_df, use_container_width=True)

    with tab2:
        # ----------------------------------------------------
        # Audit Logs Section
        # ----------------------------------------------------
        st.subheader("📋 Pipeline Run History (Audit Logs)")
        st.markdown("Real-time logging history from the `batch_audit` table.")
        
        audit_df = con.execute("""
            SELECT 
                run_id, 
                business_date, 
                start_time, 
                end_time, 
                status, 
                source_count, 
                loaded_count, 
                rejected_count, 
                error_message 
            FROM batch_audit 
            ORDER BY start_time DESC
        """).df()
        
        st.dataframe(audit_df, use_container_width=True)

    with tab3:
        # ----------------------------------------------------
        # RAG Q&A Section (LLM Powered)
        # ----------------------------------------------------
        st.subheader("🤖 RAG Question Answering (Powered by Gemini)")
        
        if gemini_api_key:
            st.markdown("This uses **Semantic Search (Vector Search)** by generating text embeddings using `text-embedding-004` and searching via Cosine Similarity.")
        else:
            st.markdown("This uses **Keyword-based Search** as a fallback since no Gemini API Key is configured in the sidebar.")
            
        user_query = st.text_input("Ask a question about the students (e.g., 'What are the top career interests?', 'Who is visual learner?', 'Tell me about SK0005'):", "")
        
        if user_query:
            retrieved_df = pd.DataFrame()
            context_str = ""
            
            if gemini_api_key:
                # Semantic Search Pathway
                try:
                    # 1. Load cached embeddings and DataFrame
                    df_all, embeddings = get_cached_embeddings(gemini_api_key, con)
                    
                    # 2. Embed user query
                    genai.configure(api_key=gemini_api_key)
                    query_resp = genai.embed_content(model="models/text-embedding-004", content=user_query)
                    query_vector = np.array(query_resp['embedding'])
                    
                    # 3. Calculate Cosine Similarity
                    dot_product = np.dot(embeddings, query_vector)
                    norms = np.linalg.norm(embeddings, axis=1) * np.linalg.norm(query_vector)
                    similarities = dot_product / (norms + 1e-10) # avoid division by zero
                    
                    # 4. Filter and select top 5
                    retrieved_df = df_all.copy()
                    retrieved_df['similarity_score'] = similarities
                    retrieved_df = retrieved_df.sort_values(by='similarity_score', ascending=False).head(5)
                    
                    st.success(f"✅ Semantic Search completed. Found {len(retrieved_df)} top matches.")
                    context_str = "\n".join([
                        f"Source Row {row['source_row_no']} ({row['student_no']}) [Similarity: {row['similarity_score']:.3f}]: {row['rag_document_text']}" 
                        for idx, row in retrieved_df.iterrows()
                    ])
                    
                except Exception as e:
                    st.error(f"Error calculating embeddings or similarities: {e}")
                    st.info("Falling back to keyword search...")
                    retrieved_df = pd.DataFrame()
            
            # If not gemini_api_key OR semantic search failed
            if not gemini_api_key or retrieved_df.empty:
                # Improved keyword matching: split query into words > 3 chars
                import re
                words = [w for w in re.split(r'\W+', user_query) if len(w) > 3]
                if not words:
                    words = [user_query]
                
                conditions = []
                params = []
                for w in words[:5]: 
                    search_term = f"%{w}%"
                    conditions.append("(LOWER(rag_keywords) LIKE LOWER(?) OR LOWER(rag_document_text) LIKE LOWER(?) OR LOWER(student_no) LIKE LOWER(?))")
                    params.extend([search_term, search_term, search_term])
                    
                where_clause = " OR ".join(conditions)
                
                retrieved_df = con.execute(f"""
                    SELECT 
                        source_row_no,
                        student_no,
                        rag_document_title,
                        rag_document_text,
                        source_url
                    FROM trusted_student_snapshot
                    WHERE {where_clause}
                    LIMIT 5
                """, params).df()
                
                if retrieved_df.empty:
                    st.warning("⚠️ No relevant documents found in the workbook for this query.")
                    context_str = ""
                else:
                    st.success(f"✅ Keyword Search found {len(retrieved_df)} relevant chunk(s).")
                    context_str = "\n".join([f"Source Row {row['source_row_no']} ({row['student_no']}): {row['rag_document_text']}" for idx, row in retrieved_df.iterrows()])

            # Now generate answer using LLM
            if gemini_api_key:
                with st.spinner("Generating answer using Gemini..."):
                    try:
                        genai.configure(api_key=gemini_api_key)
                        system_instruction = """You are a helpful assistant for the Thammasat Data & AI Workshop.
Answer the user's question ONLY using the provided retrieved context from the Excel workbook.
If the answer is not in the context, say "I cannot find the answer in the provided workbook."
When answering, ALWAYS cite your sources using the 'Source Row' number."""
                        
                        prompt = f"""
{system_instruction}

Retrieved Context:
{context_str}

User Question:
{user_query}
"""
                        
                        # Fallback mechanism for different model string availabilities
                        model_names = ['gemini-2.5-flash', 'gemini-1.5-flash', 'gemini-1.5-flash-latest', 'gemini-pro']
                        response = None
                        last_err = None
                        
                        for m_name in model_names:
                            try:
                                model = genai.GenerativeModel(m_name)
                                response = model.generate_content(prompt)
                                break
                            except Exception as e:
                                last_err = e
                                continue
                                
                        if response is None:
                            raise last_err
                        
                        st.markdown(f"### ✨ AI Answer (via {model.model_name}):")
                        st.info(response.text)
                    
                    except Exception as e:
                        st.error(f"Error communicating with Gemini API: {e}")
            else:
                st.warning("⚠️ Gemini API Key is missing. Please enter it in the sidebar to generate an AI answer.")
                st.markdown("### 📝 LLM Prompt Builder (Fallback mode)")
                st.markdown("If an API Key was provided, the following context would be sent:")
                st.code(context_str, language="text")

            st.markdown("### 🧩 Retrieved Context Details:")
            st.dataframe(retrieved_df, use_container_width=True)

    with tab4:
        st.subheader("💾 SQL Explorer (DuckDB)")
        st.markdown("Run custom SQL queries directly against the DuckDB Trusted Layer. The database is in **Read-Only** mode for safety.")
        
        default_query = "SELECT * FROM trusted_student_snapshot LIMIT 100;"
        user_sql = st.text_area("SQL Query:", value=default_query, height=150)
        
        if st.button("▶️ Run Query"):
            with st.spinner("Executing query..."):
                try:
                    result_df = con.execute(user_sql).df()
                    st.success(f"✅ Query executed successfully. Returned {len(result_df)} rows.")
                    st.dataframe(result_df, use_container_width=True)
                except Exception as e:
                    st.error(f"❌ Error executing query: {e}")
    
    con.close()
