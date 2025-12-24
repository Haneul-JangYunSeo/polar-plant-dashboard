# ===============================
# main.py
# ===============================

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from pathlib import Path
import unicodedata
from io import BytesIO

# ===============================
# Streamlit 기본 설정
# ===============================
st.set_page_config(
    page_title="🌱 극지식물 최적 EC 농도 연구",
    layout="wide"
)

# ===============================
# 한글 폰트 깨짐 방지
# ===============================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR&display=swap');
html, body, [class*="css"] {
    font-family: 'Noto Sans KR', 'Malgun Gothic', sans-serif;
}
</style>
""", unsafe_allow_html=True)

PLOTLY_FONT = dict(
    family="Malgun Gothic, Apple SD Gothic Neo, Noto Sans KR, sans-serif",
    size=14
)

# ===============================
# 경로 설정 (🔥 중요)
# ===============================
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"

# ===============================
# NFC / NFD 안전 파일 탐색
# ===============================
def _norm(s: str, form: str):
    return unicodedata.normalize(form, s)

def find_file(directory: Path, filename: str) -> Path | None:
    target_nfc = _norm(filename, "NFC")
    target_nfd = _norm(filename, "NFD")

    for f in directory.iterdir():
        name_nfc = _norm(f.name, "NFC")
        name_nfd = _norm(f.name, "NFD")
        if name_nfc == target_nfc or name_nfd == target_nfd:
            return f
    return None

# ===============================
# 학교 정보
# ===============================
SCHOOLS = {
    "송도고": {"ec": 1.0, "color": "#1f77b4"},
    "하늘고": {"ec": 2.0, "color": "#2ca02c"},  # ⭐ 최적
    "아라고": {"ec": 4.0, "color": "#ff7f0e"},
    "동산고": {"ec": 8.0, "color": "#d62728"},
}

ENV_FILES = {
    "송도고": "송도고_환경데이터.csv",
    "하늘고": "하늘고_환경데이터.csv",
    "아라고": "아라고_환경데이터.csv",
    "동산고": "동산고_환경데이터.csv",
}

GROWTH_XLSX = "4개교_생육결과데이터.xlsx"

# ===============================
# 데이터 로딩
# ===============================
@st.cache_data(show_spinner=False)
def load_env_data():
    result = {}
    for school, fname in ENV_FILES.items():
        path = find_file(DATA_DIR, fname)
        if path is None:
            continue
        df = pd.read_csv(path)
        df["time"] = pd.to_datetime(df["time"], errors="coerce")
        result[school] = df
    return result

@st.cache_data(show_spinner=False)
def load_growth_data():
    path = find_file(DATA_DIR, GROWTH_XLSX)
    if path is None:
        return None

    xls = pd.ExcelFile(path)
    data = {}
    for sheet in xls.sheet_names:
        data[sheet] = pd.read_excel(xls, sheet_name=sheet)
    return data

# ===============================
# 데이터 로딩 실행
# ===============================
with st.spinner("📂 데이터 로딩 중..."):
    env_data = load_env_data()
    growth_data = load_growth_data()

if not env_data or growth_data is None:
    st.error("❌ data 폴더 또는 파일명이 올바르지 않습니다.")
    st.stop()

# ===============================
# 사이드바
# ===============================
st.sidebar.title("🏫 학교 선택")
selected_school = st.sidebar.selectbox(
    "학교",
    ["전체"] + list(SCHOOLS.keys())
)

# ===============================
# 제목
# ===============================
st.title("🌱 극지식물 최적 EC 농도 연구")

tab1, tab2, tab3 = st.tabs(["📖 실험 개요", "🌡️ 환경 데이터", "📊 생육 결과"])

# ======================================================
# 📖 실험 개요
# ======================================================
with tab1:
    st.subheader("연구 목적")
    st.write("""
    EC(전기전도도) 농도 차이가 극지식물 생육에 미치는 영향을  
    학교별 실험 결과를 통해 비교·분석하였다.
    """)

    rows = []
    total_cnt = 0
    for s, info in SCHOOLS.items():
        cnt = len(growth_data.get(s, []))
        total_cnt += cnt
        rows.append({
            "학교": s,
            "EC 목표": info["ec"],
            "개체수": cnt
        })

    st.dataframe(pd.DataFrame(rows), use_container_width=True)

    avg_temp = pd.concat(env_data.values())["temperature"].mean()
    avg_hum = pd.concat(env_data.values())["humidity"].mean()

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("총 개체수", total_cnt)
    c2.metric("평균 온도(℃)", f"{avg_temp:.1f}")
    c3.metric("평균 습도(%)", f"{avg_hum:.1f}")
    c4.metric("최적 EC", "2.0 (하늘고) ⭐")

# ======================================================
# 🌡️ 환경 데이터
# ======================================================
with tab2:
    avg_rows = []
    for s, df in env_data.items():
        avg_rows.append({
            "학교": s,
            "온도": df["temperature"].mean(),
            "습도": df["humidity"].mean(),
            "pH": df["ph"].mean(),
            "EC": df["ec"].mean(),
            "목표 EC": SCHOOLS[s]["ec"]
        })

    avg_df = pd.DataFrame(avg_rows)

    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=["평균 온도", "평균 습도", "평균 pH", "목표 EC vs 실측 EC"]
    )

    fig.add_bar(x=avg_df["학교"], y=avg_df["온도"], row=1, col=1)
    fig.add_bar(x=avg_df["학교"], y=avg_df["습도"], row=1, col=2)
    fig.add_bar(x=avg_df["학교"], y=avg_df["pH"], row=2, col=1)
    fig.add_bar(x=avg_df["학교"], y=avg_df["EC"], name="실측", row=2, col=2)
    fig.add_bar(x=avg_df["학교"], y=avg_df["목표 EC"], name="목표", row=2, col=2)

    fig.update_layout(height=700, font=PLOTLY_FONT)
    st.plotly_chart(fig, use_container_width=True)

# ======================================================
# 📊 생육 결과
# ======================================================
with tab3:
    rows = []
    for s, df in growth_data.items():
        rows.append({
            "학교": s,
            "EC": SCHOOLS[s]["ec"],
            "평균 생중량": df["생중량(g)"].mean(),
            "평균 잎 수": df["잎 수(장)"].mean(),
            "평균 지상부 길이": df["지상부 길이(mm)"].mean(),
            "개체수": len(df)
        })

    result_df = pd.DataFrame(rows)
    best = result_df.loc[result_df["평균 생중량"].idxmax()]

    st.metric("🥇 최적 EC", f"{best['EC']} ({best['학교']}) ⭐")

    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=["평균 생중량", "평균 잎 수", "평균 지상부 길이", "개체수"]
    )

    fig.add_bar(x=result_df["학교"], y=result_df["평균 생중량"], row=1, col=1)
    fig.add_bar(x=result_df["학교"], y=result_df["평균 잎 수"], row=1, col=2)
    fig.add_bar(x=result_df["학교"], y=result_df["평균 지상부 길이"], row=2, col=1)
    fig.add_bar(x=result_df["학교"], y=result_df["개체수"], row=2, col=2)

    fig.update_layout(height=700, font=PLOTLY_FONT)
    st.plotly_chart(fig, use_container_width=True)

    merged = pd.concat(
        [df.assign(학교=s) for s, df in growth_data.items()],
        ignore_index=True
    )

    box = px.box(merged, x="학교", y="생중량(g)", points="all")
    box.update_layout(font=PLOTLY_FONT)
    st.plotly_chart(box, use_container_width=True)

    with st.expander("📂 생육 데이터 다운로드"):
        buffer = BytesIO()
        merged.to_excel(buffer, index=False, engine="openpyxl")
        buffer.seek(0)

        st.download_button(
            "XLSX 다운로드",
            data=buffer,
            file_name="생육결과_전체.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
