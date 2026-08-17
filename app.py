import streamlit as st
import pandas as pd
import io
from auditor import audit_curriculum

st.set_page_config(page_title="2027 중학교 교육과정 점검 시스템", layout="wide")

st.title("📊 2027학년도 중학교 교육과정 편성 점검 대시보드")
st.markdown("학교별 교육과정 편제표를 분석하고 지침 준수 여부를 자동으로 점검합니다.")

# 데이터 로드 (실제 환경에서는 파일 업로드 또는 GitHub 데이터 연동)
@st.cache_data
def load_data():
    # 앞서 생성한 통합 CSV 파일을 읽어옵니다.
    try:
        return pd.to_csv("multi_school_parsed.csv") # 실제 경로나 업로드된 파일
    except:
        # 테스트용 더미 데이터 로직 (생략 가능)
        return pd.read_csv("multi_school_parsed.csv")

try:
    df = pd.read_csv("multi_school_parsed.csv")
    schools = df['학교명'].unique()
    
    # 사이드바: 전체 결과 다운로드
    st.sidebar.header("📁 데이터 내보내기")
    
    # 엑셀 다운로드 기능
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='전체데이터')
        # 학교별 점검 결과 시트 추가 가능
    
    st.sidebar.download_button(
        label="📥 모든 학교 결과 엑셀 다운로드",
        data=output.getvalue(),
        file_name="2027_교육과정_점검결과_종합.xlsx",
        mime="application/vnd.ms-excel"
    )

    # 메인 화면: 학교별 탭
    tabs = st.tabs(list(schools))

    for i, school in enumerate(schools):
        with tabs[i]:
            st.subheader(f"🏫 {school} 점검 결과")
            
            # 점검 실행
            audit_result, summary = audit_curriculum(df, school)
            
            # 점검표 미리보기
            st.table(audit_result)
            
            # 학교별 총평
            st.info(summary)
            
            # 세부 편성 현황 보기
            with st.expander("🔍 세부 편성 내역 보기"):
                st.dataframe(df[df['학교명'] == school])

except Exception as e:
    st.error(f"데이터를 불러오는 중 오류가 발생했습니다: {e}")
    st.info("먼저 교육과정 파일을 파싱하여 'multi_school_parsed.csv' 파일을 생성해야 합니다.")
