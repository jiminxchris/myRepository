import streamlit as st
import pandas as pd
import requests
import datetime
import plotly.express as px

# =====================================================================
# [설정] 복사한 구글 Apps Script 웹 앱 URL을 아래에 입력하세요.
# =====================================================================
APPS_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbxqV2D3xJocojGOJargIr5ASgst1O-ET8JDZFv-sTuANEDEeYLhxDmRBy0Vaz3xN__cQQ/exec"

st.set_page_config(page_title="팀 예산 관리 대시보드", page_icon="📊", layout="wide")

# --- 데이터 연동 함수 ---
@st.cache_data(ttl=5) # 5초마다 데이터 갱신
def load_data():
    if "YOUR_APPS_SCRIPT" in APPS_SCRIPT_URL or not APPS_SCRIPT_URL.startswith("http"):
        return pd.DataFrame(columns=['id', 'month', 'member', 'category', 'amount', 'timestamp'])
    try:
        response = requests.get(APPS_SCRIPT_URL)
        if response.status_code == 200:
            data = response.json()
            if data:
                df = pd.DataFrame(data)
                df['amount'] = pd.to_numeric(df['amount'])
                return df
        return pd.DataFrame(columns=['id', 'month', 'member', 'category', 'amount', 'timestamp'])
    except Exception as e:
        st.error(f"데이터를 불러오는 중 오류가 발생했습니다: {e}")
        return pd.DataFrame(columns=['id', 'month', 'member', 'category', 'amount', 'timestamp'])

# 💡 디버깅 기능이 강화되고 버그가 방지된 save_data 함수
def save_data(data):
    if "YOUR_APPS_SCRIPT" in APPS_SCRIPT_URL or not APPS_SCRIPT_URL.startswith("http"):
        st.warning("먼저 소스 코드 상단의 APPS_SCRIPT_URL을 설정해주세요.")
        return False
    try:
        # 1. 구글 302 리다이렉트 버그를 막기 위해 allow_redirects=False 로 설정
        response = requests.post(APPS_SCRIPT_URL, json=data, allow_redirects=False)
        
        # 2. 구글이 리다이렉트 주소를 주면, 헤더를 깨끗하게 비운 GET 요청으로 수동 이동
        if response.status_code == 302:
            redirect_url = response.headers.get('Location')
            response = requests.get(redirect_url)
            
        if response.status_code == 200:
            try:
                res_json = response.json()
                if res_json.get('status') == 'success':
                    return True
            except Exception:
                # JSON 파싱 실패 시 구글이 보낸 에러 화면(HTML)을 그대로 노출합니다.
                st.error("💡 구글 스크립트 실행 중 에러가 발생했습니다. 아래 메시지를 확인하세요:")
                st.code(response.text[:1000], language="html")
                return False
        else:
            st.error(f"구글 서버 연결 실패 (상태 코드: {response.status_code})")
            return False
            
    except Exception as e:
        st.error(f"데이터 저장 중 네트워크 오류가 발생했습니다: {e}")
        if 'response' in locals():
            st.error("구글 서버 응답 내용:")
            st.code(response.text[:500])
        return False

# --- UI 레이아웃 ---
st.title("📊 팀 예산 관리 시스템")
st.markdown("부장님 보고용 월별 예산 취합 및 대시보드 (DB: Google Sheets)")

tab1, tab2 = st.tabs(["데이터 입력", "전체 대시보드"])

# [탭 1] 데이터 입력 폼 및 최근 내역
with tab1:
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.subheader("📝 내역 입력")
        with st.form("budget_form", clear_on_submit=True):
            member = st.selectbox("팀원 선택", ["부장님", "팀원1", "팀원2", "팀원3", "팀원4"])
            
            today = datetime.date.today()
            selected_date = st.date_input("결제 일자", value=today)
            
            category = st.selectbox("예산 항목", ["수선유지비", "비품", "개량공사"])
            amount = st.number_input("사용 금액 (원)", min_value=0, step=1000)
            
            submitted = st.form_submit_button("기록 저장하기", use_container_width=True)
            
            if submitted:
                new_data = {
                    "id": int(datetime.datetime.now().timestamp() * 1000),
                    "month": selected_date.strftime("%Y-%m-%d"),
                    "member": member,
                    "category": category,
                    "amount": amount
                }
                with st.spinner("구글 시트에 저장 중..."):
                    if save_data(new_data):
                        st.success("예산 데이터가 정상적으로 기록되었습니다.")
                        st.cache_data.clear() 
                        st.rerun()

    with col2:
        st.subheader("📂 최근 입력 내역 (구글 시트 연동)")
        df = load_data()
        if not df.empty:
            display_df = df.sort_values(by='id', ascending=False).drop(columns=['id', 'timestamp'], errors='ignore')
            styled_df = display_df.style.format({"amount": "{:,.0f}원"})
            st.dataframe(styled_df, use_container_width=True, hide_index=True)
        else:
            st.info("등록된 데이터가 없거나 구글 시트에 연결되지 않았습니다.")


# [탭 2] 데이터 분석 및 대시보드
with tab2:
    st.subheader("전체 대시보드")
    df = load_data()
    
    if df.empty:
        st.info("대시보드를 표시할 데이터가 없습니다.")
    else:
        total_amount = df['amount'].sum()
        
        cat_group = df.groupby('category')['amount'].sum()
        top_category = cat_group.idxmax() if not cat_group.empty else "-"
        top_category_val = cat_group.max() if not cat_group.empty else 0
        
        data_count = len(df)
        
        c1, c2, c3 = st.columns(3)
        c1.metric("전체 누적 사용액", f"{total_amount:,.0f}원")
        c2.metric("최대 사용 항목", f"{top_category}", f"{top_category_val:,.0f}원", delta_color="off")
        c3.metric("총 데이터 건수", f"{data_count}건")
        
        st.divider()
        
        chart_col1, chart_col2 = st.columns(2)
        
        with chart_col1:
            st.markdown("##### 🏠 항목별 예산 분포")
            cat_sum = df.groupby('category')['amount'].sum().reset_index()
            fig_donut = px.pie(cat_sum, values='amount', names='category', hole=0.5, 
                               color_discrete_sequence=['#3b82f6', '#10b981', '#8b5cf6'])
            fig_donut.update_traces(textposition='inside', textinfo='percent+label')
            st.plotly_chart(fig_donut, use_container_width=True)
            
        with chart_col2:
            st.markdown("##### 👥 팀원별 누적 사용액")
            mem_sum = df.groupby('member')['amount'].sum().reset_index()
            fig_bar = px.bar(mem_sum, x='member', y='amount', text='amount', 
                             color_discrete_sequence=['#60a5fa'])
            fig_bar.update_traces(texttemplate='%{text:,.0f}', textposition='outside')
            fig_bar.update_layout(yaxis_title="사용 금액 (원)", xaxis_title="팀원")
            st.plotly_chart(fig_bar, use_container_width=True)
            
        st.divider()
        
        st.markdown("##### 📅 월별/항목별 요약 테이블 (취합본)")
        try:
            df['month_group'] = df['month'].astype(str).str[:7]
            pivot_df = pd.pivot_table(df, values='amount', index='month_group', columns='category', aggfunc='sum', fill_value=0)
            
            for cat in ["수선유지비", "비품", "개량공사"]:
                if cat not in pivot_df.columns:
                    pivot_df[cat] = 0
                    
            pivot_df['월간 총합'] = pivot_df.sum(axis=1)
            pivot_df = pivot_df.sort_index(ascending=False)
            
            st.dataframe(
                pivot_df.style.format("{:,.0f}"),
                use_container_width=True
            )
        except Exception as e:
            st.warning("표를 생성하기에 데이터가 충분하지 않습니다.")
