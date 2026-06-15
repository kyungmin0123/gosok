import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import warnings
warnings.filterwarnings('ignore')

# ─────────────────────────────────────────
# 페이지 설정
# ─────────────────────────────────────────
st.set_page_config(
    page_title="고속도로 교통사고 사고유형 분석",
    page_icon="⚠️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ─────────────────────────────────────────
# CSS
# ─────────────────────────────────────────
st.markdown("""
<style>
    .main-header {
        font-size: 2.2rem;
        font-weight: 700;
        color: #1a1a2e;
        text-align: center;
        padding: 20px 0 10px 0;
    }
    .sub-header {
        font-size: 1rem;
        color: #666;
        text-align: center;
        margin-bottom: 30px;
    }
    .section-title {
        font-size: 1.25rem;
        font-weight: 700;
        color: #2c3e50;
        border-left: 5px solid #e74c3c;
        padding-left: 12px;
        margin: 30px 0 15px 0;
    }
    .kpi-box {
        border-radius: 14px;
        padding: 18px 10px;
        color: white;
        text-align: center;
        box-shadow: 0 4px 14px rgba(0,0,0,0.12);
    }
    .kpi-val  { font-size: 1.9rem; font-weight: 700; }
    .kpi-label{ font-size: 0.85rem; margin-top: 4px; opacity: 0.92; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────
# 데이터 로드
# ─────────────────────────────────────────
@st.cache_data
def load_data():
    encodings = ['euc-kr', 'cp949', 'utf-8', 'utf-8-sig']
    df = None
    for enc in encodings:
        try:
            df = pd.read_csv(
                "한국도로공사_고속도로 교통사고 상세현황_20241231.csv",
                encoding=enc
            )
            break
        except Exception:
            continue

    if df is None:
        st.error("❌ 파일을 읽을 수 없습니다.")
        st.stop()

    df.columns = df.columns.str.strip()

    # 컬럼명 표준화
    rename_map = {}
    for c in df.columns:
        cl = c.lower()
        if '연도' in c or '년도' in c:
            rename_map[c] = '연도'
        elif '발생일' in c or '날짜' in c or '일자' in c:
            rename_map[c] = '발생일자'
        elif '시간' in c:
            rename_map[c] = '발생시간'
        elif '노선' in c:
            rename_map[c] = '노선명'
        elif '지점' in c or '위치' in c or 'km' in cl:
            rename_map[c] = '발생위치'
        elif '관할' in c:
            rename_map[c] = '관할지사'
        elif '사망' in c:
            rename_map[c] = '사망자수'
        elif '부상' in c:
            rename_map[c] = '부상자수'
        elif '사고유형' in c or '사고종류' in c or '사고형태' in c:
            rename_map[c] = '사고유형'
    df.rename(columns=rename_map, inplace=True)

    # 사고유형 없으면 마지막 컬럼 사용
    if '사고유형' not in df.columns:
        df.rename(columns={df.columns[-1]: '사고유형'}, inplace=True)

    # 날짜
    if '발생일자' in df.columns:
        df['발생일자'] = pd.to_datetime(df['발생일자'], errors='coerce')
        df['월'] = df['발생일자'].dt.month
        df['요일_한'] = df['발생일자'].dt.dayofweek.map(
            {0:'월',1:'화',2:'수',3:'목',4:'금',5:'토',6:'일'}
        )

    # 시간대
    if '발생시간' in df.columns:
        df['발생시간'] = df['발생시간'].astype(str).str.strip()
        df['시간대'] = df['발생시간'].str[:2].str.replace(':', '')
        df['시간대'] = pd.to_numeric(df['시간대'], errors='coerce')

    # 숫자
    for col in ['사망자수', '부상자수']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)

    # 파생
    if '사망자수' in df.columns and '부상자수' in df.columns:
        df['사상자수'] = df['사망자수'] + df['부상자수']

    # 연도
    if '연도' in df.columns:
        df['연도_숫자'] = df['연도'].astype(str).str.extract(r'(\d{4})')[0]
        df['연도_숫자'] = pd.to_numeric(df['연도_숫자'], errors='coerce')

    # 사고유형 정리
    df['사고유형'] = df['사고유형'].astype(str).str.strip()
    df = df[df['사고유형'].notna() & (df['사고유형'] != '') & (df['사고유형'] != 'nan')]

    return df


df_raw = load_data()

# ─────────────────────────────────────────
# 사이드바 필터
# ─────────────────────────────────────────
st.sidebar.markdown("## 🔍 필터 설정")
st.sidebar.markdown("---")

# 연도
year_options = ["전체"]
if '연도_숫자' in df_raw.columns:
    years = sorted(df_raw['연도_숫자'].dropna().unique().astype(int).tolist())
    year_options += [str(y) for y in years]
selected_year = st.sidebar.selectbox("📅 연도", year_options)

st.sidebar.markdown("---")
st.sidebar.info("📊 한국도로공사\n고속도로 교통사고 상세현황\n(2022 ~ 2024)")

# ─────────────────────────────────────────
# 필터 적용
# ─────────────────────────────────────────
df = df_raw.copy()
if selected_year != "전체" and '연도_숫자' in df.columns:
    df = df[df['연도_숫자'] == int(selected_year)]

# ─────────────────────────────────────────
# 집계
# ─────────────────────────────────────────
type_agg = df.groupby('사고유형').agg(
    사고건수=('사고유형', 'count'),
    사망자수=('사망자수', 'sum'),
    부상자수=('부상자수', 'sum'),
    사상자수=('사상자수', 'sum'),
).reset_index().sort_values('사고건수', ascending=False)

type_agg['치사율(%)'] = (type_agg['사망자수'] / type_agg['사고건수'] * 100).round(2)
type_agg['건당부상자'] = (type_agg['부상자수'] / type_agg['사고건수']).round(2)

# ─────────────────────────────────────────
# 헤더
# ─────────────────────────────────────────
st.markdown('<div class="main-header">⚠️ 고속도로 사고유형 분석 대시보드</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">한국도로공사 고속도로 교통사고 상세현황 (2022 ~ 2024)</div>', unsafe_allow_html=True)

# ─────────────────────────────────────────
# KPI 카드
# ─────────────────────────────────────────
total_acc   = len(df)
total_death = int(df['사망자수'].sum())
total_inj   = int(df['부상자수'].sum())
total_types = df['사고유형'].nunique()
death_rate  = round(total_death / total_acc * 100, 2) if total_acc > 0 else 0

kpi_data = [
    ("#667eea", f"{total_acc:,}", "총 사고 건수"),
    ("#e74c3c", f"{total_death:,}", "총 사망자 수"),
    ("#e67e22", f"{total_inj:,}",  "총 부상자 수"),
    ("#27ae60", f"{total_types}",  "사고유형 종류"),
    ("#8e44ad", f"{death_rate}%",  "전체 치사율"),
]

cols = st.columns(5)
for col, (color, val, label) in zip(cols, kpi_data):
    with col:
        st.markdown(f"""
        <div class="kpi-box" style="background:{color};">
            <div class="kpi-val">{val}</div>
            <div class="kpi-label">{label}</div>
        </div>""", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ─────────────────────────────────────────
# 탭
# ─────────────────────────────────────────
tab1, tab2, tab3, tab4 = st.tabs([
    "📊 유형별 개요",
    "🕐 시간대 · 요일 분석",
    "📅 월별 · 연도별 추이",
    "💀 피해 심층 분석",
])

# ══════════════════════════════════════════
# TAB 1 : 유형별 개요
# ══════════════════════════════════════════
with tab1:
    st.markdown('<div class="section-title">사고유형별 사고 건수</div>', unsafe_allow_html=True)

    col1, col2 = st.columns(2)

    # 수평 막대
    with col1:
        fig = px.bar(
            type_agg, x='사고건수', y='사고유형',
            orientation='h',
            color='사고건수',
            color_continuous_scale='Blues',
            text='사고건수',
            title='사고유형별 사고 건수'
        )
        fig.update_traces(textposition='outside')
        fig.update_layout(
            yaxis={'categoryorder': 'total ascending'},
            height=480,
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)'
        )
        st.plotly_chart(fig, use_container_width=True)

    # 도넛 파이
    with col2:
        fig = px.pie(
            type_agg, names='사고유형', values='사고건수',
            title='사고유형 비율',
            hole=0.42,
            color_discrete_sequence=px.colors.qualitative.Set2
        )
        fig.update_traces(textposition='inside', textinfo='percent+label')
        fig.update_layout(
            height=480,
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)'
        )
        st.plotly_chart(fig, use_container_width=True)

    # ── 사망 / 부상 그룹 바
    st.markdown('<div class="section-title">사고유형별 사망자 · 부상자 수</div>', unsafe_allow_html=True)

    fig = go.Figure()
    fig.add_trace(go.Bar(
        name='사망자수',
        x=type_agg['사고유형'], y=type_agg['사망자수'],
        marker_color='#e74c3c',
        text=type_agg['사망자수'], textposition='outside'
    ))
    fig.add_trace(go.Bar(
        name='부상자수',
        x=type_agg['사고유형'], y=type_agg['부상자수'],
        marker_color='#f39c12',
        text=type_agg['부상자수'], textposition='outside'
    ))
    fig.update_layout(
        barmode='group',
        xaxis_tickangle=-25,
        height=420,
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)'
    )
    st.plotly_chart(fig, use_container_width=True)

    # ── 치사율 & 건당부상자 비교
    st.markdown('<div class="section-title">사고유형별 치사율 · 건당 부상자 수</div>', unsafe_allow_html=True)

    col3, col4 = st.columns(2)

    with col3:
        fig = px.bar(
            type_agg.sort_values('치사율(%)', ascending=False),
            x='사고유형', y='치사율(%)',
            color='치사율(%)',
            color_continuous_scale='Reds',
            text=type_agg.sort_values('치사율(%)', ascending=False)['치사율(%)'].apply(lambda x: f"{x}%"),
            title='사고유형별 치사율 (%)'
        )
        fig.update_traces(textposition='outside')
        fig.update_layout(
            xaxis_tickangle=-25, height=400,
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)'
        )
        st.plotly_chart(fig, use_container_width=True)

    with col4:
        fig = px.bar(
            type_agg.sort_values('건당부상자', ascending=False),
            x='사고유형', y='건당부상자',
            color='건당부상자',
            color_continuous_scale='Oranges',
            text=type_agg.sort_values('건당부상자', ascending=False)['건당부상자'],
            title='사고유형별 건당 평균 부상자 수'
        )
        fig.update_traces(textposition='outside')
        fig.update_layout(
            xaxis_tickangle=-25, height=400,
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)'
        )
        st.plotly_chart(fig, use_container_width=True)

    # ── 상세 테이블
    st.markdown('<div class="section-title">사고유형별 상세 통계 테이블</div>', unsafe_allow_html=True)
    st.dataframe(
        type_agg.rename(columns={
            '사고유형':'사고유형',
            '사고건수':'사고건수',
            '사망자수':'사망자수',
            '부상자수':'부상자수',
            '사상자수':'사상자수',
            '치사율(%)':'치사율(%)',
            '건당부상자':'건당평균부상자'
        }).set_index('사고유형'),
        use_container_width=True
    )

# ══════════════════════════════════════════
# TAB 2 : 시간대 · 요일 분석
# ══════════════════════════════════════════
with tab2:

    # ── 사고유형 × 시간대 히트맵
    if '시간대' in df.columns:
        st.markdown('<div class="section-title">사고유형 × 시간대 히트맵</div>', unsafe_allow_html=True)

        th = (df.dropna(subset=['시간대'])
                .groupby(['사고유형', '시간대'])
                .size().reset_index(name='건수'))
        th_pivot = th.pivot(index='사고유형', columns='시간대', values='건수').fillna(0)
        th_pivot.columns = [f"{int(c)}시" for c in th_pivot.columns]

        fig = px.imshow(
            th_pivot,
            color_continuous_scale='YlOrRd',
            title='사고유형별 시간대 분포 (건수)',
            text_auto=True, aspect='auto'
        )
        fig.update_layout(
            height=max(350, len(th_pivot) * 45),
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)'
        )
        st.plotly_chart(fig, use_container_width=True)

        # 시간대별 유형 누적 막대
        st.markdown('<div class="section-title">시간대별 사고유형 누적 분포</div>', unsafe_allow_html=True)

        th2 = (df.dropna(subset=['시간대'])
                 .groupby(['시간대', '사고유형'])
                 .size().reset_index(name='건수'))
        fig = px.bar(
            th2, x='시간대', y='건수', color='사고유형',
            barmode='stack',
            title='시간대별 사고유형 누적 건수',
            color_discrete_sequence=px.colors.qualitative.Set2
        )
        fig.update_layout(
            xaxis_title='시간(시)', height=430,
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)'
        )
        st.plotly_chart(fig, use_container_width=True)

    # ── 사고유형 × 요일 히트맵
    if '요일_한' in df.columns:
        st.markdown('<div class="section-title">사고유형 × 요일 히트맵</div>', unsafe_allow_html=True)

        day_order = ['월','화','수','목','금','토','일']
        dw = (df.groupby(['사고유형', '요일_한'])
                .size().reset_index(name='건수'))
        dw_pivot = dw.pivot(index='사고유형', columns='요일_한', values='건수').fillna(0)
        # 요일 순서 정렬
        dw_pivot = dw_pivot.reindex(
            columns=[d for d in day_order if d in dw_pivot.columns]
        )

        fig = px.imshow(
            dw_pivot,
            color_continuous_scale='Blues',
            title='사고유형별 요일 분포 (건수)',
            text_auto=True, aspect='auto'
        )
        fig.update_layout(
            height=max(350, len(dw_pivot) * 45),
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)'
        )
        st.plotly_chart(fig, use_container_width=True)

        col1, col2 = st.columns(2)

        # 요일별 유형 누적 막대
        with col1:
            dw2 = (df.groupby(['요일_한', '사고유형'])
                     .size().reset_index(name='건수'))
            dw2['요일_한'] = pd.Categorical(dw2['요일_한'], categories=day_order, ordered=True)
            dw2 = dw2.sort_values('요일_한')
            fig = px.bar(
                dw2, x='요일_한', y='건수', color='사고유형',
                barmode='stack',
                title='요일별 사고유형 누적 건수',
                color_discrete_sequence=px.colors.qualitative.Set2
            )
            fig.update_layout(
                xaxis_title='요일', height=420,
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)'
            )
            st.plotly_chart(fig, use_container_width=True)

        # 주말 vs 평일 파이
        with col2:
            df['주말평일'] = df['요일_한'].apply(
                lambda x: '주말' if x in ['토','일'] else '평일'
            )
            wp = df.groupby(['주말평일','사고유형']).size().reset_index(name='건수')
            fig = px.sunburst(
                wp, path=['주말평일','사고유형'], values='건수',
                title='평일 / 주말별 사고유형 분포',
                color_discrete_sequence=px.colors.qualitative.Pastel
            )
            fig.update_layout(
                height=420,
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)'
            )
            st.plotly_chart(fig, use_container_width=True)

# ══════════════════════════════════════════
# TAB 3 : 월별 · 연도별 추이
# ══════════════════════════════════════════
with tab3:

    # 사고유형 × 월 히트맵
    if '월' in df.columns:
        st.markdown('<div class="section-title">사고유형 × 월 히트맵</div>', unsafe_allow_html=True)

        tm = df.groupby(['사고유형','월']).size().reset_index(name='건수')
        tm_pivot = tm.pivot(index='사고유형', columns='월', values='건수').fillna(0)
        tm_pivot.columns = [f"{int(c)}월" for c in tm_pivot.columns]

        fig = px.imshow(
            tm_pivot,
            color_continuous_scale='Greens',
            title='사고유형별 월별 분포 (건수)',
            text_auto=True, aspect='auto'
        )
        fig.update_layout(
            height=max(350, len(tm_pivot) * 45),
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)'
        )
        st.plotly_chart(fig, use_container_width=True)

        # 월별 유형 라인 차트
        st.markdown('<div class="section-title">월별 사고유형 추이 (라인)</div>', unsafe_allow_html=True)

        fig = px.line(
            tm, x='월', y='건수', color='사고유형',
            title='월별 사고유형별 건수 추이',
            markers=True,
            color_discrete_sequence=px.colors.qualitative.Set1
        )
        fig.update_layout(
            xaxis_title='월', height=430,
            xaxis=dict(tickmode='linear', tick0=1, dtick=1),
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)'
        )
        st.plotly_chart(fig, use_container_width=True)

    # 연도별 추이
    if '연도_숫자' in df.columns:
        st.markdown('<div class="section-title">연도별 사고유형 분포</div>', unsafe_allow_html=True)

        col1, col2 = st.columns(2)
        ty_yr = (df.groupby(['연도_숫자','사고유형'])
                   .size().reset_index(name='건수'))

        with col1:
            fig = px.bar(
                ty_yr, x='연도_숫자', y='건수', color='사고유형',
                barmode='stack',
                title='연도별 사고유형 누적 건수',
                color_discrete_sequence=px.colors.qualitative.Set2
            )
            fig.update_layout(
                xaxis_title='연도', height=420,
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)'
            )
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            fig = px.line(
                ty_yr, x='연도_숫자', y='건수', color='사고유형',
                title='연도별 사고유형 추이',
                markers=True,
                color_discrete_sequence=px.colors.qualitative.Set2
            )
            fig.update_layout(
                xaxis_title='연도', height=420,
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)'
            )
            st.plotly_chart(fig, use_container_width=True)

        # 연도 × 사고유형 히트맵
        st.markdown('<div class="section-title">연도 × 사고유형 히트맵</div>', unsafe_allow_html=True)

        yr_pivot = ty_yr.pivot(index='사고유형', columns='연도_숫자', values='건수').fillna(0)
        yr_pivot.columns = yr_pivot.columns.astype(int).astype(str)

        fig = px.imshow(
            yr_pivot,
            color_continuous_scale='Purples',
            title='연도별 사고유형 건수',
            text_auto=True, aspect='auto'
        )
        fig.update_layout(
            height=max(300, len(yr_pivot) * 45),
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)'
        )
        st.plotly_chart(fig, use_container_width=True)

# ══════════════════════════════════════════
# TAB 4 : 피해 심층 분석
# ══════════════════════════════════════════
with tab4:

    st.markdown('<div class="section-title">사고유형별 사상자 버블 차트</div>', unsafe_allow_html=True)

    fig = px.scatter(
        type_agg,
        x='사고건수', y='사망자수',
        size='부상자수', color='치사율(%)',
        hover_name='사고유형',
        text='사고유형',
        title='사고건수 vs 사망자수 (버블 크기=부상자수, 색상=치사율)',
        color_continuous_scale='Reds',
        size_max=60
    )
    fig.update_traces(textposition='top center')
    fig.update_layout(
        height=500,
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)'
    )
    st.plotly_chart(fig, use_container_width=True)

    col1, col2 = st.columns(2)

    # 사망자 파이
    with col1:
        st.markdown('<div class="section-title">사고유형별 사망자 비율</div>', unsafe_allow_html=True)
        fig = px.pie(
            type_agg[type_agg['사망자수'] > 0],
            names='사고유형', values='사망자수',
            title='사고유형별 사망자 비율',
            hole=0.4,
            color_discrete_sequence=px.colors.sequential.Reds_r
        )
        fig.update_traces(textposition='inside', textinfo='percent+label+value')
        fig.update_layout(
            height=430,
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)'
        )
        st.plotly_chart(fig, use_container_width=True)

    # 부상자 파이
    with col2:
        st.markdown('<div class="section-title">사고유형별 부상자 비율</div>', unsafe_allow_html=True)
        fig = px.pie(
            type_agg[type_agg['부상자수'] > 0],
            names='사고유형', values='부상자수',
            title='사고유형별 부상자 비율',
            hole=0.4,
            color_discrete_sequence=px.colors.sequential.Oranges_r
        )
        fig.update_traces(textposition='inside', textinfo='percent+label+value')
        fig.update_layout(
            height=430,
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)'
        )
        st.plotly_chart(fig, use_container_width=True)

    # 사고유형별 사망자 × 월 히트맵
    if '월' in df.columns:
        st.markdown('<div class="section-title">사고유형 × 월별 사망자 히트맵</div>', unsafe_allow_html=True)

        dm = df.groupby(['사고유형','월'])['사망자수'].sum().reset_index()
        dm_pivot = dm.pivot(index='사고유형', columns='월', values='사망자수').fillna(0)
        dm_pivot.columns = [f"{int(c)}월" for c in dm_pivot.columns]

        fig = px.imshow(
            dm_pivot,
            color_continuous_scale='Reds',
            title='사고유형별 월별 사망자 수',
            text_auto=True, aspect='auto'
        )
        fig.update_layout(
            height=max(300, len(dm_pivot) * 45),
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)'
        )
        st.plotly_chart(fig, use_container_width=True)

    # 사고유형별 사망자 × 시간대 히트맵
    if '시간대' in df.columns:
        st.markdown('<div class="section-title">사고유형 × 시간대별 사망자 히트맵</div>', unsafe_allow_html=True)

        dh = (df.dropna(subset=['시간대'])
                .groupby(['사고유형','시간대'])['사망자수'].sum().reset_index())
        dh_pivot = dh.pivot(index='사고유형', columns='시간대', values='사망자수').fillna(0)
        dh_pivot.columns = [f"{int(c)}시" for c in dh_pivot.columns]

        fig = px.imshow(
            dh_pivot,
            color_continuous_scale='OrRd',
            title='사고유형별 시간대 사망자 분포',
            text_auto=True, aspect='auto'
        )
        fig.update_layout(
            height=max(300, len(dh_pivot) * 45),
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)'
        )
        st.plotly_chart(fig, use_container_width=True)

# ─────────────────────────────────────────
# 원본 데이터
# ─────────────────────────────────────────
st.markdown("---")
with st.expander("📋 원본 데이터 보기"):
    st.markdown(f"**총 {len(df):,}건** 표시 중")
    st.dataframe(df, use_container_width=True, height=400)
    csv_out = df.to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig')
    st.download_button(
        label="📥 필터된 데이터 다운로드 (CSV)",
        data=csv_out,
        file_name="교통사고_사고유형.csv",
        mime='text/csv'
    )

st.markdown("---")
st.markdown(
    "<div style='text-align:center;color:#999;font-size:0.85rem;'>"
    "📊 한국도로공사 고속도로 교통사고 상세현황 | 당곡고등학교 AI 학습 대시보드"
    "</div>",
    unsafe_allow_html=True
)
