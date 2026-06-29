import os
import streamlit as st
import duckdb
import pandas as pd

# Page Config
st.set_page_config(
    page_title="TU Student Analytics Dashboard",
    page_icon="🎓",
    layout="wide"
)

st.title("🎓 Thammasat Student Analytics & Pipeline Audit Dashboard")
st.markdown("This dashboard displays insights from the **Trusted Layer** inside our DuckDB database, populated by our idempotent batch pipeline.")

db_path = "data/trusted_database.db"

# Check if DB exists
if not os.path.exists(db_path):
    st.error("❌ Database file not found. Please run the pipeline script first to ingest data.")
    st.info("Run command: `python3 pipeline.py --business-date 2026-06-28 --run-id FIRST_RUN`")
else:
    con = duckdb.connect(db_path)
    
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

    st.markdown("---")
    
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
    
    con.close()
