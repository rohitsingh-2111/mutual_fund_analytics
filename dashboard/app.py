from pathlib import Path
import sqlite3
import pandas as pd
import plotly.express as px
import streamlit as st

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR.parent / "data" / "db" / "bluestock_mf.db"

st.set_page_config(page_title="Bluestock Mutual Fund Analytics", layout="wide", initial_sidebar_state="expanded")
st.title("📊 Bluestock Mutual Fund Performance Analytics Portal")

def get_db_path() -> Path | None:
    if DB_PATH.exists() and DB_PATH.stat().st_size > 0:
        return DB_PATH
    return None


db_path = get_db_path()

if not db_path:
    st.error("⚠️ Database 'bluestock_mf.db' could not be found. Please run the ETL pipeline and place the database in data/db.")
else:
    def run_query(query, params=None):
        with sqlite3.connect(db_path) as conn:
            return pd.read_sql_query(query, conn, params=params)

    try:
        fund_data = run_query("SELECT DISTINCT fund_name, category, risk_level FROM dim_fund ORDER BY category, fund_name")
        all_funds = fund_data['fund_name'].tolist()
        all_categories = fund_data['category'].dropna().unique().tolist()
        all_risk_levels = fund_data['risk_level'].dropna().unique().tolist()

        st.sidebar.header("🔍 Filters")
        selected_categories = st.sidebar.multiselect("Select categories", options=all_categories, default=all_categories)
        selected_risk_levels = st.sidebar.multiselect("Select risk levels", options=all_risk_levels, default=all_risk_levels)
        selected_funds = st.sidebar.multiselect("Select funds", options=all_funds, default=all_funds[:5])

        if not selected_categories or not selected_risk_levels or not selected_funds:
            st.warning("Select at least one category, one risk level, and one fund to view the chart.")
        else:
            placeholders = {
                'categories': ','.join(['?'] * len(selected_categories)),
                'risk_levels': ','.join(['?'] * len(selected_risk_levels)),
                'funds': ','.join(['?'] * len(selected_funds)),
            }
            query = f"""
                SELECT d.fund_name, d.category, f.date, f.nav
                FROM fact_nav f
                JOIN dim_fund d ON f.amfi_code = d.amfi_code
                WHERE d.category IN ({placeholders['categories']})
                  AND d.risk_level IN ({placeholders['risk_levels']})
                  AND d.fund_name IN ({placeholders['funds']})
                ORDER BY d.fund_name, f.date ASC;
            """
            params = selected_categories + selected_risk_levels + selected_funds
            df_trends = run_query(query, params=params)
            df_trends['date'] = pd.to_datetime(df_trends['date'], errors='coerce')
            df_trends = df_trends.dropna(subset=['date', 'nav'])

            if df_trends.empty:
                st.warning("No NAV history was found for the selected filters.")
            else:
                fig_line = px.line(
                    df_trends,
                    x='date',
                    y='nav',
                    color='fund_name',
                    title='NAV History for Selected Funds',
                    labels={'nav': 'NAV', 'date': 'Date', 'fund_name': 'Fund'},
                    template='plotly_white',
                )
                st.plotly_chart(fig_line, use_container_width=True)

                st.subheader("📋 Selected Fund Summary")
                summary = (
                    df_trends.groupby('fund_name')['nav']
                    .agg(min_nav='min', max_nav='max', mean_nav='mean', std_nav='std')
                    .reset_index()
                )
                st.dataframe(summary.style.format({'min_nav': '{:.2f}', 'max_nav': '{:.2f}', 'mean_nav': '{:.2f}', 'std_nav': '{:.2f}'}), use_container_width=True)
    except Exception as e:
        st.error(f"Data loading mismatch: {e}")