import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(layout="wide")
st.title("📦 법인팀 구매 데이터 인포그래픽 대시보드")

@st.cache_data
def load_data():
    df = pd.read_excel("법인팀구매원장.xlsx", sheet_name="Sheet1")
    df["수량"] = pd.to_numeric(df["수량"], errors="coerce")
    df["구매가액"] = pd.to_numeric(df["구매가액"], errors="coerce")
    df["판매가액"] = pd.to_numeric(df["판매가액"], errors="coerce")
    df["구매단가"] = pd.to_numeric(df["구매단가"], errors="coerce")
    df["판매가"] = pd.to_numeric(df["판매가"], errors="coerce")
    df["이익"] = df["판매가액"] - df["구매가액"]
    df["이익률"] = df["이익"] / df["구매가액"]
    df["날짜"] = pd.to_datetime(df["날짜"], errors="coerce")
    return df

df = load_data()

with st.sidebar:
    st.header("🔍 필터")
    min_date = df["날짜"].min()
    max_date = df["날짜"].max()
    start_date, end_date = st.date_input("날짜 범위", [min_date, max_date], min_value=min_date, max_value=max_date)

    filters = {
        "품종": "품종",
        "품목": "품목",
        "원산지": "원산지/추정",
        "구매처": "구매처",
        "납품처": "납품처/사용처",
        "담당자": "담당자"
    }

    selected = {}
    for label, column in filters.items():
        if column not in df.columns:
            continue
        st.markdown(f"**{label}**")
        real_options = sorted(df[column].dropna().unique().tolist())
        full_options = ["전체"] + real_options
        default_vals = st.multiselect(f"{label} 선택", options=full_options, default=real_options, key=f"select_{column}")
        if "전체" in default_vals or not default_vals:
            selected[column] = real_options
        else:
            selected[column] = default_vals

    exclude_items = st.multiselect("❌ 제외할 품목", sorted(df["품목"].dropna().unique()))
    exclude_types = st.multiselect("❌ 제외할 품종", sorted(df["품종"].dropna().unique()))
    exclude_origins = st.multiselect("❌ 제외할 원산지", sorted(df["원산지/추정"].dropna().unique()))
    exclude_buyers = st.multiselect("❌ 제외할 구매처", sorted(df["구매처"].dropna().unique()))

filtered_df = df[(df["날짜"] >= pd.to_datetime(start_date)) & (df["날짜"] <= pd.to_datetime(end_date))].copy()
for col, vals in selected.items():
    if vals:
        filtered_df = filtered_df[filtered_df[col].isin(vals)]

if exclude_items:
    filtered_df = filtered_df[~filtered_df["품목"].isin(exclude_items)]
if exclude_types:
    filtered_df = filtered_df[~filtered_df["품종"].isin(exclude_types)]
if exclude_origins:
    filtered_df = filtered_df[~filtered_df["원산지/추정"].isin(exclude_origins)]
if exclude_buyers:
    filtered_df = filtered_df[~filtered_df["구매처"].isin(exclude_buyers)]

layout_config = dict(height=700, margin=dict(l=15, r=15, t=70, b=70))

tab1, tab2, tab3, tab4 = st.tabs([
    "📦 납품처별 품목 순위", 
    "💰 구매처별 총 구매가액", 
    "📈 납품처별 평균 이익률", 
    "📌 품목별 평균 구매단가"
])

with tab1:
    st.subheader("📦 납품처별 품목 순위")
    top_items = filtered_df.groupby("품목")["수량"].sum().sort_values(ascending=False).reset_index()
    if not top_items.empty:
        max_page = (len(top_items) - 1) // 10 + 1
        page = st.number_input("페이지", min_value=1, max_value=max_page, value=1, step=1, key="tab1page")
        display = top_items.iloc[(page-1)*10:page*10]
        fig = px.bar(display, x="품목", y="수량")
        fig.update_layout(**layout_config)
        st.plotly_chart(fig, use_container_width=True, key="tab1chart")
    else:
        st.info("조건에 맞는 품목 데이터가 없습니다.")

with tab2:
    st.subheader("💰 구매처별 총 구매가액")
    buyer_total = filtered_df.groupby("구매처")["구매가액"].sum().sort_values(ascending=False).reset_index()
    if not buyer_total.empty:
        max_page = (len(buyer_total) - 1) // 10 + 1
        page = st.number_input("페이지", min_value=1, max_value=max_page, value=1, step=1, key="tab2page")
        display = buyer_total.iloc[(page - 1)*10 : page*10]
        display["구매가액(표시)"] = display["구매가액"].apply(lambda x: f"{x/10000:.1f}만")
        fig = px.bar(display, x="구매처", y="구매가액", text="구매가액(표시)")
        fig.update_layout(**layout_config)
        st.plotly_chart(fig, use_container_width=True, key="tab2chart")
    else:
        st.info("조건에 맞는 구매처 데이터가 없습니다.")

with tab3:
    st.subheader("📈 납품처별 평균 이익률 (%)")
    treemap_data = filtered_df.groupby("납품처/사용처").agg({
        "판매가액": "sum",
        "이익": "sum"
    }).reset_index()
    treemap_data = treemap_data[treemap_data["판매가액"] > 0]
    treemap_data["이익률"] = treemap_data["이익"] / treemap_data["판매가액"]
    treemap_data["스케일값"] = treemap_data["판매가액"].apply(lambda x: x**0.2)
    treemap_data["label_text"] = treemap_data.apply(
        lambda row: f"{row['납품처/사용처']}<br>{row['이익률']*100:.1f}%<br>매출 {int(row['판매가액']):,}원<br>이익 {int(row['이익']):,}원",
        axis=1
    )

    fig = px.treemap(
        treemap_data,
        path=["납품처/사용처"],
        values="스케일값",
        color="이익률",
        color_continuous_scale="RdYlGn"
    )

    fig.update_traces(
        text=treemap_data["label_text"],
        textinfo="text"
    )

    fig.update_layout(
        **layout_config,
        uniformtext=dict(minsize=12, mode='show'),
        font=dict(size=14.5)
    )

    st.plotly_chart(fig, use_container_width=True, key="tab3treemap")

    total_sales = int(treemap_data["판매가액"].sum())
total_purchase = int(treemap_data["판매가액"].sum() - treemap_data["이익"].sum())
total_profit = int(treemap_data["이익"].sum())
profit_rate = total_profit / total_purchase if total_purchase != 0 else 0

st.markdown(f"**총 매출: {total_sales:,}원**")
st.markdown(f"**총 구매액: {total_purchase:,}원**")
st.markdown(f"**총 이익: {total_profit:,}원**")
st.markdown(f"**이익률: {profit_rate * 100:.1f}%**")


with tab4:
    st.subheader("📌 품목별 평균 구매단가")
    avg_unit_price = filtered_df.groupby("품목")["구매단가"].mean().dropna().sort_values(ascending=False).reset_index()
    if not avg_unit_price.empty:
        max_page = (len(avg_unit_price) - 1) // 10 + 1
        page = st.number_input("페이지", min_value=1, max_value=max_page, value=1, step=1, key="tab4page")
        display = avg_unit_price.iloc[(page - 1)*10 : page*10]
        display["구매단가"] = display["구매단가"].round()
        fig = px.bar(display, x="품목", y="구매단가", text="구매단가")
        fig.update_layout(**layout_config)
        st.plotly_chart(fig, use_container_width=True, key="tab4chart")
    else:
        st.info("조건에 맞는 품목 데이터가 없습니다.")
