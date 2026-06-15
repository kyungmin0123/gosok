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
    page_title="고속도로 교통사고 대시보드",
    page_icon="🚗",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ─────────────────────────────────────────
# CSS 스타일
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
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 12px;
        padding: 20px;
        color: white;
        text-align: center;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
    }
    .metric-card-red {
        background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        border-radius: 12px;
        padding: 20px;
        color: white;
        text-align: center;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
    }
    .metric-card-green {
        background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
        border-radius: 12px;
        padding: 20px;
        color: white;
        text-align: center;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
    }
    .metric-card-orange {
        background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%);
        border-radius: 12px;
        padding: 20px;
        color: white;
        text-align: center;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
    }
    .section-title {
        font-size: 1.3rem;
        font-weight: 600;
        color: #2c3e50;
        border-left: 4px solid #667eea;
        padding-left: 12px;
        margin: 25px 0 15px 0;
    }
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

    # 사고유형 컬럼이 없으면 마지막 컬럼 사용
    if '사고유형' not in df.columns:
        df.rename(columns={df.columns[-1]: '사고유형'}, inplace=True)

    # 날짜 파싱
    if '발생일자' in df.columns:
        df['발생일자'] = pd.to_datetime(df['발생일자'], errors='coerce')
        df['월'] = df['발생일자'].dt.month
        df['요일_한'] = df['발생일자'].dt.dayofweek.map(
            {0:'월', 1:'화', 2:'수', 3:'목', 4:'금', 5:'토', 6:'일'}
        )

    # 시간대 파싱
    if '발생시간' in df.columns:
        df['발생시간'] = df['발생시간'].astype(str).str.strip()
        df['시간대'] = df['발생시간'].str[:2].str.replace(':', '')
        df['시간대'] = pd.to_numeric(df['시간대'], errors='coerce')

    # 숫자 컬럼
    for col in ['사망자수', '부상자수']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)

    # 파생 컬럼
    if '사망자수' in df.columns and '부상자수' in df.columns:
        df['사상자수'] = df['사망자수'] + df['부상자수']
        df['사고심각도'] = '인명피해 없음'
        df.loc[df['부상자수'] > 0, '사고심각도'] = '부상'
        df.loc[df['사망자수'] > 0, '사고심각도'] = '사망'

    # 연도 숫자화
    if '연도' in df.columns:
        df['연도_숫자'] = df['연도'].astype(str).str.extract(r'(\d{4})')[0]
        df['연도_숫자'] = pd.to_numeric(df['연도_숫자'], errors='coerce')

    return df


df_raw = load_data()

# ─────────────────────────────────────────
# 사이드바 : 연도 필터만
# ─────────────────────────────────────────
st.sidebar.markdown("## 🔍 필터 설정")
st.sidebar.markdown("---")

year_options = ["전체"]
if '연도_숫자' in df_raw.columns:
    years = sorted(df_raw['연도_숫자'].dropna().unique().astype(int).tolist())
    year_options += [str(y) for y in years]
selected_year = st.sidebar.selectbox("📅 연도 선택", year_options)

st.sidebar.markdown("---")
st.sidebar.info("📊 한국도로공사\n고속도로 교통사고 상세현황\n(2022 ~ 2024)")

# ─────────────────────────────────────────
# 필터링
# ─────────────────────────────────────────
df = df_raw.copy()
if selected_year != "전체" and '연도_숫자' in df.columns:
    df = df[df['연도_숫자'] == int(selected_year)]

# ─────────────────────────────────────────
# 헤더
# ─────────────────────────────────────────
st.markdown('<div class="main-header">🚗 고속도로 교통사고 대시보드</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">한국도로공사 고속도로 교통사고 상세현황 (2022 ~ 2024)</div>', unsafe_allow_html=True)

# ─────────────────────────────────────────
# KPI 카드
# ─────────────────────────────────────────
st.markdown('<div class="section-title">📌 핵심 지표</div>', unsafe_allow_html=True)

total_acc   = len(df)
total_death = int(df['사망자수'].sum()) if '사망자수' in df.columns else 0
total_inj   = int(df['부상자수'].sum()) if '부상자수' in df.columns else 0
death_rate  = round(total_death / total_acc * 100, 2) if total_acc > 0 else 0
avg_inj     = round(total_inj   / total_acc, 2)       if total_acc > 0 else 0

c1, c2, c3, c4, c5 = st.columns(5)

with c1:
    st.markdown(f"""
    <div class="metric-card">
        <div style="font-size:1.8rem;font-weight:700;">{total_acc:,}</div>
        <div style="font-size:0.9rem;margin-top:5px;">총 사고 건수</div>
    </div>""", unsafe_allow_html=True)
with c2:
    st.markdown(f"""
    <div class="metric-card-red">
        <div style="font-size:1.8rem;font-weight:700;">{total_death:,}</div>
        <div style="font-size:0.9rem;margin-top:5px;">총 사망자 수</div>
    </div>""", unsafe_allow_html=True)
with c3:
    st.markdown(f"""
    <div class="metric-card-green">
        <div style="font-size:1.8rem;font-weight:700;">{total_inj:,}</div>
        <div style="font-size:0.9rem;margin-top:5px;">총 부상자 수</div>
    </div>""", unsafe_allow_html=True)
with c4:
    st.markdown(f"""
    <div class="metric-card-orange">
        <div style="font-size:1.8rem;font-weight:700;">{death_rate}%</div>
        <div style="font-size:0.9rem;margin-top:5px;">치사율</div>
    </div>""", unsafe_allow_html=True)
with c5:
    st.markdown(f"""
    <div class="metric-card">
        <div style="font-size:1.8rem;font-weight:700;">{avg_inj}</div>
        <div style="font-size:0.9rem;margin-top:5px;">사고당 평균 부상자</div>
    </div>""", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ─────────────────────────────────────────
# 탭 : 시간 분석 / 노선 분석 / 피해 분석
# ─────────────────────────────────────────
tab1, tab2, tab3 = st.tabs([
    "📅 시간 분석",
    "🛣️ 노선 분석",
    "💀 피해 분석"
])

# ══════════════════════════════════════════
# TAB 1 : 시간 분석
# ══════════════════════════════════════════
with tab1:
    st.markdown('<div class="section-title">📅 시간 분석</div>', unsafe_allow_html=True)

    col1, col2 = st.columns(2)

    # 연도별 사고 건수
    with col1:
        if '연도_숫자' in df.columns:
            yr_df = df.groupby('연도_숫자').size().reset_index(name='사고건수')
            fig = go.Figure(go.Bar(
                x=yr_df['연도_숫자'].astype(str),
                y=yr_df['사고건수'],
                marker_color='#667eea',
                text=yr_df['사고건수'],
                textposition='outside'
            ))
            fig.update_layout(
                title='연도별 사고 건수',
                xaxis_title='연도', yaxis_title='건수',
                height=380,
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)'
            )
            st.plotly_chart(fig, use_container_width=True)

    # 월별 사고 건수
    with col2:
        if '월' in df.columns:
            month_map = {1:'1월',2:'2월',3:'3월',4:'4월',5:'5월',6:'6월',
                         7:'7월',8:'8월',9:'9월',10:'10월',11:'11월',12:'12월'}
            mo_df = df.groupby('월').size().reset_index(name='건수')
            mo_df['월명'] = mo_df['월'].map(month_map)
            fig = px.line(mo_df, x='월명', y='건수',
                          title='월별 사고 건수',
                          markers=True,
                          color_discrete_sequence=['#f5576c'])
            fig.update_traces(line_width=2.5, marker_size=8)
            fig.update_layout(
                xaxis_title='월', yaxis_title='건수',
                height=380,
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)'
            )
            st.plotly_chart(fig, use_container_width=True)

    col3, col4 = st.columns(2)

    # 시간대별 사고
    with col3:
        if '시간대' in df.columns:
            hr_df = df.groupby('시간대').size().reset_index(name='건수')
            hr_df = hr_df.dropna().sort_values('시간대')
            fig = px.bar(hr_df, x='시간대', y='건수',
                         title='시간대별 사고 건수 (0~23시)',
                         color='건수',
                         color_continuous_scale='Plasma')
            fig.update_layout(
                xaxis_title='시간(시)', yaxis_title='건수',
                height=380,
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)'
            )
            st.plotly_chart(fig, use_container_width=True)

    # 요일별 사고
    with col4:
        if '요일_한' in df.columns:
            day_order = ['월','화','수','목','금','토','일']
            day_df = df.groupby('요일_한').size().reset_index(name='건수')
            day_df['요일_한'] = pd.Categorical(
                day_df['요일_한'], categories=day_order, ordered=True
            )
            day_df = day_df.sort_values('요일_한')
            colors = ['#667eea','#667eea','#667eea','#667eea','#667eea','#f5576c','#f5576c']
            fig = go.Figure(go.Bar(
                x=day_df['요일_한'],
                y=day_df['건수'],
                marker_color=colors[:len(day_df)],
                text=day_df['건수'],
                textposition='outside'
            ))
            fig.update_layout(
                title='요일별 사고 건수 (주말=빨강)',
                xaxis_title='요일', yaxis_title='건수',
                height=380,
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)'
            )
            st.plotly_chart(fig, use_container_width=True)

    # 연도 × 월 히트맵
    if '연도_숫자' in df.columns and '월' in df.columns:
        st.markdown('<div class="section-title">📊 연도 × 월 사고 히트맵</div>', unsafe_allow_html=True)
        heat = df.groupby(['연도_숫자','월']).size().reset_index(name='건수')
        heat_pivot = heat.pivot(index='연도_숫자', columns='월', values='건수').fillna(0)
        heat_pivot.columns = [f"{int(c)}월" for c in heat_pivot.columns]
        heat_pivot.index = heat_pivot.index.astype(int).astype(str)
        fig = px.imshow(heat_pivot,
                        color_continuous_scale='YlOrRd',
                        title='연도별 월별 사고 건수 히트맵',
                        text_auto=True, aspect='auto')
        fig.update_layout(height=300,
                          plot_bgcolor='rgba(0,0,0,0)',
                          paper_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig, use_container_width=True)

# ══════════════════════════════════════════
# TAB 2 : 노선 분석
# ══════════════════════════════════════════
with tab2:
    st.markdown('<div class="section-title">🛣️ 노선별 분석</div>', unsafe_allow_html=True)

    if '노선명' not in df.columns:
        st.warning("노선명 컬럼을 찾을 수 없습니다.")
    else:
        top_n = st.slider("상위 노선 수 선택", 5, 30, 15, key="route_n")
        col1, col2 = st.columns(2)

        # 사고 건수 상위 노선 수평 막대
        with col1:
            route_cnt = df['노선명'].value_counts().head(top_n).reset_index()
            route_cnt.columns = ['노선명','사고건수']
            fig = px.bar(route_cnt, x='사고건수', y='노선명',
                         orientation='h',
                         title=f'사고 건수 상위 {top_n}개 노선',
                         color='사고건수',
                         color_continuous_scale='Viridis',
                         text='사고건수')
            fig.update_traces(textposition='outside')
            fig.update_layout(
                height=520,
                yaxis={'categoryorder':'total ascending'},
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)'
            )
            st.plotly_chart(fig, use_container_width=True)

        # 사고건수 vs 사망자수 버블
        with col2:
            if '사망자수' in df.columns:
                route_agg = df.groupby('노선명').agg(
                    사고건수=('노선명','count'),
                    사망자수=('사망자수','sum'),
                    부상자수=('부상자수','sum')
                ).reset_index()
                route_agg['치사율'] = (
                    route_agg['사망자수'] / route_agg['사고건수'] * 100
                ).round(2)
                top_bubble = route_agg.nlargest(top_n, '사망자수')
                fig = px.scatter(top_bubble,
                                 x='사고건수', y='사망자수',
                                 size='부상자수', color='치사율',
                                 hover_name='노선명',
                                 title=f'노선별 사고건수 vs 사망자수 (버블=부상자수)',
                                 color_continuous_scale='Reds',
                                 size_max=40)
                fig.update_layout(
                    height=520,
                    plot_bgcolor='rgba(0,0,0,0)',
                    paper_bgcolor='rgba(0,0,0,0)'
                )
                st.plotly_chart(fig, use_container_width=True)

        # 상위 10개 노선 연도별 추이
        if '연도_숫자' in df.columns:
            st.markdown('<div class="section-title">주요 노선 연도별 추이 (상위 10개)</div>',
                        unsafe_allow_html=True)
            top10 = df['노선명'].value_counts().head(10).index.tolist()
            ry_df = (df[df['노선명'].isin(top10)]
                     .groupby(['연도_숫자','노선명'])
                     .size().reset_index(name='건수'))
            fig = px.line(ry_df, x='연도_숫자', y='건수', color='노선명',
                          title='주요 노선별 연도 추이',
                          markers=True)
            fig.update_layout(
                height=420, xaxis_title='연도',
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)'
            )
            st.plotly_chart(fig, use_container_width=True)

        # 노선별 사상자 스택 바
        if '사망자수' in df.columns:
            st.markdown('<div class="section-title">노선별 사상자 현황 (상위 15개)</div>',
                        unsafe_allow_html=True)
            top_dmg = df.groupby('노선명').agg(
                사망자수=('사망자수','sum'),
                부상자수=('부상자수','sum')
            ).reset_index()
            top_dmg['합계'] = top_dmg['사망자수'] + top_dmg['부상자수']
            top_dmg = top_dmg.nlargest(15, '합계')
            fig = go.Figure()
            fig.add_trace(go.Bar(name='부상자수', x=top_dmg['노선명'],
                                 y=top_dmg['부상자수'], marker_color='#f39c12'))
            fig.add_trace(go.Bar(name='사망자수', x=top_dmg['노선명'],
                                 y=top_dmg['사망자수'], marker_color='#e74c3c'))
            fig.update_layout(
                barmode='stack',
                xaxis_tickangle=-40,
                title='노선별 사망 / 부상자 합계',
                height=430,
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)'
            )
            st.plotly_chart(fig, use_container_width=True)

# ══════════════════════════════════════════
# TAB 3 : 피해 분석
# ══════════════════════════════════════════
with tab3:
    st.markdown('<div class="section-title">💀 피해 분석</div>', unsafe_allow_html=True)

    col1, col2 = st.columns(2)

    # 사고 심각도 도넛
    with col1:
        if '사고심각도' in df.columns:
            sev_df = df['사고심각도'].value_counts().reset_index()
            sev_df.columns = ['심각도','건수']
            color_map = {
                '사망':        '#e74c3c',
                '부상':        '#e67e22',
                '인명피해 없음': '#2ecc71'
            }
            fig = px.pie(sev_df, names='심각도', values='건수',
                         title='사고 심각도 분포',
                         hole=0.45,
                         color='심각도',
                         color_discrete_map=color_map)
            fig.update_traces(textposition='inside',
                              textinfo='percent+label+value')
            fig.update_layout(height=430,
                              plot_bgcolor='rgba(0,0,0,0)',
                              paper_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig, use_container_width=True)

    # 월별 사망/부상 그룹 바
    with col2:
        if '월' in df.columns and '사망자수' in df.columns:
            mv_df = df.groupby('월').agg(
                사망자수=('사망자수','sum'),
                부상자수=('부상자수','sum')
            ).reset_index()
            fig = go.Figure()
            fig.add_trace(go.Bar(name='부상자수', x=mv_df['월'],
                                 y=mv_df['부상자수'], marker_color='#f39c12'))
            fig.add_trace(go.Bar(name='사망자수', x=mv_df['월'],
                                 y=mv_df['사망자수'], marker_color='#e74c3c'))
            fig.update_layout(
                title='월별 사망 / 부상자 현황',
                barmode='group',
                xaxis_title='월', yaxis_title='명',
                height=430,
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)'
            )
            st.plotly_chart(fig, use_container_width=True)

    col3, col4 = st.columns(2)

    # 시간대별 이중축
    with col3:
        if '시간대' in df.columns and '사망자수' in df.columns:
            hd_df = df.groupby('시간대').agg(
                사망자수=('사망자수','sum'),
                사고건수=('시간대','count')
            ).reset_index().dropna().sort_values('시간대')
            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=hd_df['시간대'], y=hd_df['사고건수'],
                name='사고건수', marker_color='#bdc3c7', opacity=0.7
            ))
            fig.add_trace(go.Scatter(
                x=hd_df['시간대'], y=hd_df['사망자수'],
                name='사망자수', mode='lines+markers',
                line=dict(color='#e74c3c', width=2.5),
                marker_size=7, yaxis='y2'
            ))
            fig.update_layout(
                title='시간대별 사고건수 & 사망자수',
                xaxis_title='시간(시)',
                yaxis=dict(title='사고건수'),
                yaxis2=dict(title='사망자수', overlaying='y', side='right'),
                legend=dict(x=0.7, y=1.1),
                height=430,
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)'
            )
            st.plotly_chart(fig, use_container_width=True)

    # 연도별 사망/부상 서브플롯
    with col4:
        if '연도_숫자' in df.columns and '사망자수' in df.columns:
            yr_dmg = df.groupby('연도_숫자').agg(
                사망자수=('사망자수','sum'),
                부상자수=('부상자수','sum')
            ).reset_index()
            fig = make_subplots(rows=1, cols=2,
                                subplot_titles=('연도별 사망자수','연도별 부상자수'))
            fig.add_trace(
                go.Scatter(x=yr_dmg['연도_숫자'].astype(str),
                           y=yr_dmg['사망자수'],
                           mode='lines+markers+text',
                           text=yr_dmg['사망자수'],
                           textposition='top center',
                           line=dict(color='#e74c3c', width=3),
                           marker_size=10, name='사망자수'),
                row=1, col=1
            )
            fig.add_trace(
                go.Scatter(x=yr_dmg['연도_숫자'].astype(str),
                           y=yr_dmg['부상자수'],
                           mode='lines+markers+text',
                           text=yr_dmg['부상자수'],
                           textposition='top center',
                           line=dict(color='#f39c12', width=3),
                           marker_size=10, name='부상자수'),
                row=1, col=2
            )
            fig.update_layout(
                height=430, showlegend=False,
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)'
            )
            st.plotly_chart(fig, use_container_width=True)

    # 요일별 사고건수 / 부상 / 사망
    if '요일_한' in df.columns and '사망자수' in df.columns:
        st.markdown('<div class="section-title">요일별 사고건수 / 부상자 / 사망자</div>',
                    unsafe_allow_html=True)
        day_order = ['월','화','수','목','금','토','일']
        wd_df = df.groupby('요일_한').agg(
            사망자수=('사망자수','sum'),
            부상자수=('부상자수','sum'),
            사고건수=('요일_한','count')
        ).reset_index()
        wd_df['요일_한'] = pd.Categorical(wd_df['요일_한'],
                                          categories=day_order, ordered=True)
        wd_df = wd_df.sort_values('요일_한')
        fig = go.Figure()
        fig.add_trace(go.Bar(name='사고건수', x=wd_df['요일_한'],
                             y=wd_df['사고건수'], marker_color='#95a5a6'))
        fig.add_trace(go.Bar(name='부상자수', x=wd_df['요일_한'],
                             y=wd_df['부상자수'], marker_color='#f39c12'))
        fig.add_trace(go.Bar(name='사망자수', x=wd_df['요일_한'],
                             y=wd_df['사망자수'], marker_color='#e74c3c'))
        fig.update_layout(
            barmode='group',
            title='요일별 사고건수 / 부상자수 / 사망자수',
            xaxis_title='요일', yaxis_title='명/건',
            height=420,
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)'
        )
        st.plotly_chart(fig, use_container_width=True)

# ─────────────────────────────────────────
# 원본 데이터 뷰어
# ─────────────────────────────────────────
st.markdown("---")
with st.expander("📋 원본 데이터 보기"):
    st.markdown(f"**총 {len(df):,}건** 표시 중")
    st.dataframe(df, use_container_width=True, height=400)
    csv_out = df.to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig')
    st.download_button(
        label="📥 필터된 데이터 다운로드 (CSV)",
        data=csv_out,
        file_name="교통사고_필터링.csv",
        mime='text/csv'
    )

st.markdown("---")
st.markdown(
    "<div style='text-align:center;color:#999;font-size:0.85rem;'>"
    "📊 한국도로공사 고속도로 교통사고 상세현황 | 당곡고등학교 AI 학습 대시보드"
    "</div>",
    unsafe_allow_html=True
)
