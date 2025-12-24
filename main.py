# main.py
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
# 한글 폰트 깨짐 방지 (Streamlit + Plotly)
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
# 경로 설정
# ===============================
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"

# ===============================
# 유틸: NFC/NFD 안전 파일 찾기
# ===============================
def normalize_str(s: str, form: str):
    return unicodedata.normalize(form, s)

def find_file_by_name(directory: Path, target_name: str) -> Path | None:
    target_nfc = normalize_str(target_name, "NFC")
    target_nfd = normalize_str(target_name, "NFD")

    for f in directory.iterdir():
        name_nfc = normalize_str(f.name, "NFC")
        name_nfd = normalize_str(f.name, "NFD")
        if name_nfc == target_nfc or name_nfd == target_nfd:
            return f
    return None

# ===============================
# 학교 및 EC 정보
# ===============================
SCHOOL_INFO = {
    "송도고": {"ec": 1.0, "color": "#1f77b4"},
    "하늘고": {"ec": 2.0, "color": "#2ca02c"},  # 최적
    "아라고": {"ec": 4.0, "color": "#ff7f0e"},
    "동산고": {"ec": 8.0, "color": "#d62728"},
}

ENV_FILES = {
    "송도고": "송도고_환경데이터.csv",
    "하늘고": "하늘고_환경데이터.csv",
    "아라고": "아라고_환경데이터.csv",
    "동산고": "동산고_환경데이터.csv",
}

GROWTH_FILE_NAME = "4개교_생육결과데이터.xlsx"

# ===============================
# 데이터 로딩 함수 (캐시)
# ===============================
@st.cache_data(show_spinner=False)
def load_environment_data():
    env_data = {}

    for school, fname in ENV_FILES.items():
        file_path = find_file_by_name(DATA_DIR, fname)
        if file_path is None:
            continue

        df = pd.read_csv(file_path)
        df["time"] = pd.to_datetime(df["time"], errors="coerce")
        env_data[school] = df

    return env_data

@st.cache_data(show_spinner=False)
def load_growth_data():
    file_path = find_file_by_name(DATA_DIR, GROWTH_FILE_NAME)
    if file_path is None:
        return None

    xls = pd.ExcelFile(file_path)
    data = {}

    for sheet in xls.sheet_names:
        df = pd.read_excel(xls, sheet_name=sheet)
        data[sheet] = df

    return data

# ===============================
# 데이터 로딩
# ===============================
with st.spinner("데이터 로딩 중..."):
    env_data = load_environment_data()
    growth_data = load_growth_data()

if not env_data or growth_data is None:
    st.error("❌ 데이터 파일을 찾을 수 없습니다. data 폴더 및 파일명을 확인하세요.")
    st.stop()

# ===============================
# 사이드바
# ===============================
st.sidebar.title("🏫 학교 선택")
school_option = st.sidebar.selectbox(
    "학교",
    ["전체"] + list(SCHOOL_INFO.keys())
)

# ===============================
# 제목
# ===============================
st.title("🌱 극지식물 최적 EC 농도 연구")

# ===============================
# 탭 구성
# ===============================
tab1, tab2, tab3 = st.tabs(["📖 실험 개요", "🌡️ 환경 데이터", "📊 생육 결과"])

# ======================================================
# 📖 Tab 1: 실험 개요
# ======================================================
with tab1:
    st.subheader("연구 배경 및 목적")
    st.write("""
    극지 환경에서 생존 가능한 식물의 생육 조건을 탐구하기 위해  
    **EC(전기전도도) 농도 차이**가 생육에 미치는 영향을 분석하였다.
    """)

    info_rows = []
    total_plants = 0

    for school, info in SCHOOL_INFO.items():
        count = len(growth_data.get(school, []))
        total_plants += count
        info_rows.append({
            "학교명": school,
            "EC 목표": info["ec"],
            "개체수": count,
            "색상": info["color"]
        })

    info_df = pd.DataFrame(info_rows)
    st.dataframe(info_df, use_container_width=True)

    avg_temp = pd.concat(env_data.values())["temperature"].mean()
    avg_hum = pd.concat(env_data.values())["humidity"].mean()

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("총 개체수", f"{total_plants} 개")
    col2.metric("평균 온도", f"{avg_temp:.1f} ℃")
    col3.metric("평균 습도", f"{avg_hum:.1f} %")
    col4.metric("최적 EC", "2.0 (하늘고) ⭐")

# ======================================================
# 🌡️ Tab 2: 환경 데이터
# ======================================================
with tab2:
    st.subheader("학교별 환경 평균 비교")

    avg_rows = []
    for school, df in env_data.items():
        avg_rows.append({
            "학교": school,
            "temperature": df["temperature"].mean(),
            "humidity": df["humidity"].mean(),
            "ph": df["ph"].mean(),
            "ec": df["ec"].mean(),
            "target_ec": SCHOOL_INFO[school]["ec"]
        })

    avg_df = pd.DataFrame(avg_rows)

    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=("평균 온도", "평균 습도", "평균 pH", "목표 EC vs 실측 EC")
    )

    fig.add_bar(x=avg_df["학교"], y=avg_df["temperature"], row=1, col=1)
    fig.add_bar(x=avg_df["학교"], y=avg_df["humidity"], row=1, col=2)
    fig.add_bar(x=avg_df["학교"], y=avg_df["ph"], row=2, col=1)
    fig.add_bar(x=avg_df["학교"], y=avg_df["ec"], name="실측 EC", row=2, col=2)
    fig.add_bar(x=avg_df["학교"], y=avg_df["target_ec"], name="목표 EC", row=2, col=2)

    fig.update_layout(height=700, font=PLOTLY_FONT)
    st.plotly_chart(fig, use_container_width=True)

    if school_option != "전체":
        df = env_data[school_option]

        fig_ts = go.Figure()
        fig_ts.add_scatter(x=df["time"], y=df["temperature"], name="온도")
        fig_ts.add_scatter(x=df["time"], y=df["humidity"], name="습도")
        fig_ts.add_scatter(x=df["time"], y=df["ec"], name="EC")
        fig_ts.add_hline(y=SCHOOL_INFO[school_option]["ec"], line_dash="dash", name="목표 EC")

        fig_ts.update_layout(
            title=f"{school_option} 환경 시계열",
            font=PLOTLY_FONT
        )
        st.plotly_chart(fig_ts, use_container_width=True)

    with st.expander("📂 환경 데이터 원본"):
        all_env = pd.concat(
            [df.assign(학교=school) for school, df in env_data.items()],
            ignore_index=True
        )
        st.dataframe(all_env, use_container_width=True)

        buffer = BytesIO()
        all_env.to_csv(buffer, index=False)
        buffer.seek(0)

        st.download_button(
            "CSV 다운로드",
            data=buffer,
            file_name="환경데이터_전체.csv",
            mime="text/csv"
        )

# ======================================================
# 📊 Tab 3: 생육 결과
# ======================================================
with tab3:
    st.subheader("EC별 생육 결과 분석")

    rows = []
    for school, df in growth_data.items():
        rows.append({
            "학교": school,
            "EC": SCHOOL_INFO[school]["ec"],
            "평균 생중량": df["생중량(g)"].mean(),
            "평균 잎 수": df["잎 수(장)"].mean(),
            "평균 지상부 길이": df["지상부 길이(mm)"].mean(),
            "개체수": len(df)
        })

    result_df = pd.DataFrame(rows)

    best_row = result_df.loc[result_df["평균 생중량"].idxmax()]

    st.metric(
        "🥇 최고 평균 생중량 EC",
        f"EC {best_row['EC']} ({best_row['학교']}) ⭐"
    )

    fig_bar = make_subplots(rows=2, cols=2,
                            subplot_titles=("평균 생중량", "평균 잎 수", "평균 지상부 길이", "개체수"))

    fig_bar.add_bar(x=result_df["학교"], y=result_df["평균 생중량"], row=1, col=1)
    fig_bar.add_bar(x=result_df["학교"], y=result_df["평균 잎 수"], row=1, col=2)
    fig_bar.add_bar(x=result_df["학교"], y=result_df["평균 지상부 길이"], row=2, col=1)
    fig_bar.add_bar(x=result_df["학교"], y=result_df["개체수"], row=2, col=2)

    fig_bar.update_layout(height=700, font=PLOTLY_FONT)
    st.plotly_chart(fig_bar, use_container_width=True)

    merged = []
    for school, df in growth_data.items():
        temp = df.copy()
        temp["학교"] = school
        merged.append(temp)

    merged_df = pd.concat(merged, ignore_index=True)

    fig_box = px.box(
        merged_df,
        x="학교",
        y="생중량(g)",
        points="all"
    )
    fig_box.update_layout(font=PLOTLY_FONT)
    st.plotly_chart(fig_box, use_container_width=True)

    fig_scatter1 = px.scatter(
        merged_df,
        x="잎 수(장)",
        y="생중량(g)",
        color="학교"
    )
    fig_scatter1.update_layout(font=PLOTLY_FONT)

    fig_scatter2 = px.scatter(
        merged_df,
        x="지상부 길이(mm)",
        y="생중량(g)",
        color="학교"
    )
    fig_scatter2.update_layout(font=PLOTLY_FONT)

    col1, col2 = st.columns(2)
    col1.plotly_chart(fig_scatter1, use_container_width=True)
    col2.plotly_chart(fig_scatter2, use_container_width=True)

    with st.expander("📂 생육 데이터 원본"):
        st.dataframe(merged_df, use_container_width=True)

        buffer = BytesIO()
        merged_df.to_excel(buffer, index=False, engine="openpyxl")
        buffer.seek(0)

        st.download_button(
            "XLSX 다운로드",
            data=buffer,
            file_name="생육결과_전체.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
