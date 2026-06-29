import os
import streamlit as st
import duckdb
import pandas as pd
import google.generativeai as genai
import numpy as np
from sentence_transformers import SentenceTransformer

@st.cache_resource
def load_embedding_model():
    # Cache the local Nomic Embed model in memory so it only loads once
    return SentenceTransformer("nomic-ai/nomic-embed-text-v1.5", trust_remote_code=True)



# Page Config
st.set_page_config(
    page_title="TU Student Analytics Dashboard",
    page_icon="🎓",
    layout="wide"
)

# Premium Aesthetics & Custom Styling
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700&display=swap');
    
    /* Global Font overrides */
    html, body, [class*="css"], .stMarkdown, p, div {
        font-family: 'Outfit', sans-serif !important;
    }
    
    /* Styled Metric Cards */
    div[data-testid="metric-container"] {
        background-color: #ffffff;
        border: 1px solid #e2e8f0;
        padding: 18px 24px;
        border-radius: 14px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03);
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    }
    
    div[data-testid="metric-container"]:hover {
        transform: translateY(-4px);
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.08), 0 4px 6px -2px rgba(0, 0, 0, 0.04);
        border-color: #cbd5e1;
    }
    
    /* Tab formatting */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px;
        padding: 8px 16px;
        background-color: #f1f5f9;
        transition: all 0.2s ease;
    }
    .stTabs [aria-selected="true"] {
        background-color: #3b82f6 !important;
        color: white !important;
    }
</style>
""", unsafe_allow_html=True)

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
            st.dataframe(campus_df, width="stretch")
    
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
            st.dataframe(level_df, width="stretch")

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
        
        st.dataframe(audit_df, width="stretch")

    with tab3:
        # ----------------------------------------------------
        # RAG Q&A Section (LLM Powered)
        # ----------------------------------------------------
        st.subheader("🤖 RAG Question Answering (Powered by Gemini)")
        
        st.markdown("This uses **Semantic Search (Vector Search)** by generating query embeddings via local **Nomic Embed Text v1.5** and calculating Cosine Similarity natively inside DuckDB. No API Key is required for the search phase!")
            
        user_query = st.text_input("Ask a question about the students (e.g., 'What are the top career interests?', 'Who is visual learner?', 'Tell me about SK0005'):", "")
        
        if user_query:
            retrieved_df = pd.DataFrame()
            context_str = ""
            
            # Semantic Search Pathway using pre-calculated database embeddings (Production Best Practice 3: Vector DB)
            try:
                # Install & Load VSS extension natively in DuckDB
                con.execute("INSTALL vss; LOAD vss;")
                
                # 1. We check if the vector_embedding column exists in the schema
                columns_info = con.execute("PRAGMA table_info(trusted_student_snapshot)").df()
                has_vectors = 'vector_embedding' in columns_info['name'].values
                
                if has_vectors:
                    # 2. Embed user query locally (0 API requests!)
                    model = load_embedding_model()
                    query_vector = model.encode(f"search_query: {user_query}").tolist()
                    
                    # 3. Query native Vector Cosine Similarity inside DuckDB SQL
                    retrieved_df = con.execute("""
                        SELECT 
                            source_row_no, 
                            student_no, 
                            rag_document_title, 
                            rag_document_text, 
                            source_url,
                            array_cosine_similarity(vector_embedding::DOUBLE[]::DOUBLE[768], ?::DOUBLE[]::DOUBLE[768]) AS similarity_score
                        FROM trusted_student_snapshot
                        WHERE vector_embedding IS NOT NULL
                        ORDER BY similarity_score DESC
                        LIMIT 5
                    """, (query_vector,)).df()
                    
                    if not retrieved_df.empty:
                        st.success(f"✅ Semantic Search completed inside DuckDB (Local Nomic Embed v1.5). Found {len(retrieved_df)} top matches.")
                        context_str = "\n".join([
                            f"Source Row {row['source_row_no']} ({row['student_no']}) [Similarity: {row['similarity_score']:.3f}]: {row['rag_document_text']}" 
                            for idx, row in retrieved_df.iterrows()
                        ])
                    else:
                        st.warning("⚠️ Database has 'vector_embedding' column, but all entries are NULL. Please run your pipeline to populate vectors.")
                else:
                    st.warning("⚠️ 'vector_embedding' column does not exist in the database table schema. Falling back to keyword search...")
                    
            except Exception as e:
                st.error(f"Error executing database vector search: {e}")
                st.info("Falling back to keyword search...")
                retrieved_df = pd.DataFrame()
            
            # If semantic search failed or returned nothing
            if retrieved_df.empty:
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
                        model_names = [
                            'gemini-2.5-flash', 
                            'gemini-2.5-flash-8b',
                            'gemini-1.5-flash', 
                            'gemini-1.5-pro', 
                            'gemini-1.5-pro-latest',
                            'gemini-2.5-pro',
                            'gemini-1.5-flash-latest', 
                            'gemini-pro'
                        ]
                        response = None
                        errors = []
                        
                        for m_name in model_names:
                            try:
                                model = genai.GenerativeModel(m_name)
                                response = model.generate_content(prompt)
                                break
                            except Exception as e:
                                errors.append(f"- Model '{m_name}' failed: {e}")
                                continue
                                
                        if response is None:
                            error_summary = "\n".join(errors)
                            raise Exception(f"All Generative Models failed.\n{error_summary}")
                        
                        st.markdown(f"### ✨ AI Answer (via {model.model_name}):")
                        st.info(response.text)
                    
                    except Exception as e:
                        st.error(f"Error communicating with Gemini API:\n{e}")
                        st.markdown("### 📝 LLM Prompt Builder (API Limit Fallback)")
                        st.warning("⚠️ API Quota exceeded. Showing the fully constructed grounded prompt that would have been sent to Gemini:")
                        st.code(prompt, language="text")
            else:
                st.warning("⚠️ Gemini API Key is missing. Please enter it in the sidebar to generate an AI answer.")
                st.markdown("### 📝 LLM Prompt Builder (Fallback mode)")
                st.markdown("If an API Key was provided, the following context would be sent:")
                st.code(context_str, language="text")

            st.markdown("### 🧩 Retrieved Context Details:")
            st.dataframe(retrieved_df, width="stretch")

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
                    st.dataframe(result_df, width="stretch")
                except Exception as e:
                    st.error(f"❌ Error executing query: {e}")
    
    con.close()
