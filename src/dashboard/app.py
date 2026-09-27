import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st
import pandas as pd
from config.settings import settings
from config.categories import CATEGORY_REGISTRY
from src.pipelines.db import AsosDatabase
from src.alerts.telegram import TelegramAlerter

st.set_page_config(
    page_title="ASOS Price Intelligence Monitor",
    page_icon="🛍",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS for styling
st.markdown("""
<style>
    .metric-card {
        background-color: #1E232F;
        border: 1px solid #2D3748;
        border-radius: 8px;
        padding: 16px;
        margin-bottom: 12px;
    }
    .deal-badge {
        background-color: #E53E3E;
        color: white;
        padding: 3px 8px;
        border-radius: 4px;
        font-weight: bold;
        font-size: 0.85em;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 12px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 48px;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)


@st.cache_resource
def get_db():
    return AsosDatabase()


db = get_db()

# --- SIDEBAR FILTERS ---
with st.sidebar:
    st.title("🛍 ASOS Monitor")
    st.caption("E-commerce Price & Deal Intelligence")
    st.divider()

    st.subheader("Filter Catalog")

    # Categories filter
    categories_data = db.get_categories()
    category_options = {"All Categories": None}
    for c in categories_data:
        category_options[f"{c['title']} ({c['product_count']})"] = c["id"]

    selected_cat_label = st.selectbox("Category", list(category_options.keys()))
    selected_cat_id = category_options[selected_cat_label]

    # Minimum discount filter
    min_discount = st.slider("Minimum Discount (%)", min_value=0, max_value=90, value=20, step=5)

    # Max price filter
    max_price = st.number_input("Max Price (EUR)", min_value=10, max_value=500, value=250, step=10)

    # Selling fast checkbox
    only_selling_fast = st.checkbox("🔥 Only 'Selling Fast' items", value=False)

    # Search keyword
    search_query = st.text_input("🔍 Search by product name or brand", placeholder="e.g. Nike, hoodie...")

    st.divider()
    if st.button("🔄 Refresh Data", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    # Telegram info badge
    alerter = TelegramAlerter()
    st.caption(f"Telegram Alerts: **{'Active' if alerter.is_configured else 'Mock / Simulation'}**")


# --- DATA RETRIEVAL ---
@st.cache_data(ttl=60)
def load_data(category_id: int | None):
    products = db.get_all_products(category_id=category_id)
    if not products:
        return pd.DataFrame()
    df = pd.DataFrame(products)
    return df


df = load_data(selected_cat_id)

if df.empty:
    st.warning("No products found in the database. Run the scraper first with: `uv run python -m src.main --all-categories`")
    st.stop()

# Apply filters
filtered_df = df.copy()

if min_discount > 0:
    filtered_df = filtered_df[filtered_df["discount_percent"] >= min_discount]

if max_price:
    filtered_df = filtered_df[filtered_df["current_price"] <= max_price]

if only_selling_fast and "is_selling_fast" in filtered_df.columns:
    filtered_df = filtered_df[filtered_df["is_selling_fast"] == 1]

if search_query:
    q = search_query.lower()
    filtered_df = filtered_df[
        filtered_df["name"].str.lower().str.contains(q, na=False) |
        filtered_df["brand"].str.lower().str.contains(q, na=False)
    ]

# Brand filter in sidebar based on current subset
available_brands = sorted(filtered_df["brand"].dropna().unique().tolist())
with st.sidebar:
    selected_brands = st.multiselect("Brand", available_brands)
    if selected_brands:
        filtered_df = filtered_df[filtered_df["brand"].isin(selected_brands)]


# --- TOP METRICS ---
col1, col2, col3, col4 = st.columns(4)

total_items = len(df)
deals_in_view = len(filtered_df)
max_disc = filtered_df["discount_percent"].max() if not filtered_df.empty else 0.0
avg_price = filtered_df["current_price"].mean() if not filtered_df.empty else 0.0

col1.metric("Catalog in DB", f"{total_items:,} items")
col2.metric("Matching Deals in View", f"{deals_in_view:,} items")
col3.metric("Top Discount in View", f"-{max_disc:.1f}%" if max_disc > 0 else "0%")
col4.metric("Avg Filtered Price", f"{avg_price:.2f} EUR" if avg_price > 0 else "0.00 EUR")

st.markdown("---")

# --- TABS ---
tab_deals, tab_analytics, tab_explorer, tab_alerts = st.tabs([
    "🔥 Deal Cards Showcase",
    "📊 Market & Price Analytics",
    "📋 Data Explorer & Export",
    "🤖 Telegram Alerting Simulation",
])


# --- TAB 1: DEAL CARDS ---
with tab_deals:
    st.subheader("Highlighted Deals & Price Drops")
    st.caption("Visual grid of discounted items matching active filters")

    if filtered_df.empty:
        st.info("No items match your active filters. Try decreasing the minimum discount or clearing the brand filter.")
    else:
        # Display top 48 cards
        deals_to_display = filtered_df.sort_values(by="discount_percent", ascending=False).head(48)
        
        cards_per_row = 4
        rows = [deals_to_display.iloc[i:i + cards_per_row] for i in range(0, len(deals_to_display), cards_per_row)]

        for row in rows:
            cols = st.columns(cards_per_row)
            for i, (_, item) in enumerate(row.iterrows()):
                with cols[i]:
                    with st.container(border=True):
                        img_url = item.get("image_url")
                        if img_url and str(img_url).startswith("http"):
                            st.image(img_url, use_container_width=True)
                        else:
                            st.markdown("📷 *No Image Available*")

                        st.markdown(f"**{item.get('brand', 'ASOS')}**")
                        st.caption(f"{item.get('name', '')[:50]}...")

                        disc = item.get("discount_percent", 0.0)
                        curr = item.get("current_price", 0.0)
                        prev = item.get("previous_price")

                        if disc > 0:
                            st.markdown(
                                f"<span class='deal-badge'>-{disc:.1f}%</span> &nbsp; "
                                f"<b style='color:#48BB78; font-size:1.15em;'>{curr:.2f} EUR</b> "
                                f"<s style='color:#E2E8F0; font-size:0.85em;'>{prev:.2f} EUR</s>",
                                unsafe_allow_html=True
                            )
                        else:
                            st.markdown(f"<b style='font-size:1.1em;'>{curr:.2f} EUR</b>", unsafe_allow_html=True)

                        url = item.get("url", "https://www.asos.com")
                        st.link_button("View on ASOS ↗", url, use_container_width=True)


# --- TAB 2: ANALYTICS ---
with tab_analytics:
    st.subheader("Market & Price Analytics")
    
    col_chart1, col_chart2 = st.columns(2)
    
    with col_chart1:
        st.markdown("##### 🏆 Top Discounted Brands")
        brand_stats = df[df["discount_percent"] > 0].groupby("brand")["discount_percent"].agg(["count", "mean", "max"]).reset_index()
        brand_stats = brand_stats[brand_stats["count"] >= 3].sort_values(by="mean", ascending=False).head(10)
        
        if not brand_stats.empty:
            brand_stats.columns = ["Brand", "Deals Count", "Avg Discount (%)", "Max Discount (%)"]
            st.dataframe(brand_stats, use_container_width=True)
        else:
            st.info("Not enough deal data for brand statistics.")

    with col_chart2:
        st.markdown("##### 🏷 Categories by Total Products")
        cat_df = pd.DataFrame(categories_data)
        if not cat_df.empty and "title" in cat_df.columns:
            st.bar_chart(cat_df.set_index("title")["product_count"])
        else:
            st.info("No category data available.")


# --- TAB 3: DATA EXPLORER ---
with tab_explorer:
    st.subheader("Raw Catalog Data Explorer")
    st.caption("Search, inspect, and export cleaned dataset")

    st.dataframe(
        filtered_df[[
            "id", "product_code", "brand", "name", "current_price",
            "previous_price", "discount_percent", "currency", "url"
        ]],
        use_container_width=True,
        hide_index=True
    )

    col_dl1, col_dl2 = st.columns(2)
    with col_dl1:
        csv_data = filtered_df.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="📥 Download Filtered Results (CSV)",
            data=csv_data,
            file_name="asos_filtered_deals.csv",
            mime="text/csv",
            use_container_width=True
        )
    with col_dl2:
        json_data = filtered_df.to_json(orient="records", indent=2).encode("utf-8")
        st.download_button(
            label="📥 Download Filtered Results (JSON)",
            data=json_data,
            file_name="asos_filtered_deals.json",
            mime="application/json",
            use_container_width=True
        )


# --- TAB 4: TELEGRAM ALERTS ---
with tab_alerts:
    st.subheader("Telegram Deal Alerting Pipeline")
    st.markdown("""
    The alerting pipeline continuously evaluates freshly scraped products against discount thresholds
    and dispatches formatted alert notifications to your Telegram channel or chat.
    """)

    col_al1, col_al2 = st.columns(2)

    with col_al1:
        st.markdown("##### ⚙️ Integration Status")
        if alerter.is_configured:
            st.success("✅ Telegram Bot Token and Chat ID are configured.")
        else:
            st.warning("⚠️ **Mock / Simulation Mode Active**")
            st.caption(
                "To enable real notifications, add your `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` "
                "to the `.env` file. Currently, notifications are safely logged to console/logs."
            )

        threshold_input = st.slider("Alert Trigger Threshold (% discount)", 30, 85, int(alerter.min_discount), 5)

        if st.button("🚀 Trigger Test Alert for Top Deal", use_container_width=True):
            top_deals = db.get_top_deals(limit=1)
            if top_deals:
                deal = top_deals[0]
                success = alerter.send_alert(deal)
                if success:
                    st.success(f"Dispatched notification for: **{deal['name']}** (-{deal['discount_percent']}%)!")
            else:
                st.warning("No marked-down deals currently found in database.")

    with col_al2:
        st.markdown("##### 📱 Message Preview")
        top_deal = db.get_top_deals(limit=1)
        if top_deal:
            formatted_msg = alerter.format_deal_message(top_deal[0])
            st.code(formatted_msg, language="html")
        else:
            st.caption("No sample deal available to preview.")
