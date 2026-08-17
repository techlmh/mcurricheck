import streamlit as st
import pandas as pd
import io
from utils import parse_curriculum_xlsm
from auditor import audit_curriculum

st.set_page_config(page_title="2027 중학교 교육과정 점검 시스템", layout="wide")

# 세션 상태 초기화 (데이터 저장용)
if 'all_data' not in st.session_state:
    st.session_state.all_data = pd.DataFrame()
if 'school_summaries' not in st.session_state:
    st.session_state.school_summaries = []

st.title("🚀 2027학년도 중학교 교육과정 실시간 점검 시스템")
st.markdown("학교에서 제출한 `.xlsm` 파일을 업로드하면 즉시 지침 준수 여부를 점검합니다.")

# 사이드바: 파일 업로드 및 초기화
with st.sidebar:
    st.header("📁 파일 관리")
    uploaded_files = st.file_uploader("편제표 파일 업로드 (.xlsm)", type=['xlsm'], accept_multiple_files=True)
    
    if st.button("🔄 데이터 일괄 초기화", help="업로드된 모든 데이터와 결과를 삭제합니다."):
        st.session_state.all_data = pd.DataFrame()
        st.session_state.school_summaries = []
        st.rerun()

    if uploaded_files:
        if st.button("✅ 업로드 파일 분석 시작"):
            new_data_list = []
            for uploaded_file in uploaded_files:
                base, df = parse_curriculum_xlsm(uploaded_file)
                new_data_list.append(df)
            
            if new_data_list:
                st.session_state.all_data = pd.concat(new_data_list, ignore_index=True)
                st.success(f"{len(uploaded_files)}개 학교 데이터 분석 완료!")

# 메인 화면 로직
if not st.session_state.all_data.empty:
    df = st.session_state.all_data
    schools = df['학교명'].unique()
    
    # 엑셀 다운로드 버튼 (전체 결과)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='종합편성현황')
    
    st.download_button(
        label="📥 전체 학교 점검 결과 엑셀 다운로드",
        data=output.getvalue(),
        file_name="2027_교육과정_점검결과_종합.xlsx",
        mime="application/vnd.ms-excel"
    )

    # 학교별 탭 구성
    tabs = st.tabs(list(schools))

    for i, school in enumerate(schools):
        with tabs[i]:
            st.subheader(f"🏫 {school} 점검 리포트")
            
            # 점검 실행
            audit_result, summary = audit_curriculum(df, school)
            
            # 1. 점검표 미리보기 (자율 점검표 서식)
            st.markdown("#### [2027학년도 중학교 교육과정 편성 자율 점검표]")
            st.table(audit_result)
            
            # 2. 학교별 총평
            st.info(summary)
            
            # 3. 세부 데이터 확인
            with st.expander("🔍 세부 편성 데이터 확인"):
                st.dataframe(df[df['학교명'] == school])
else:
    st.info("왼쪽 사이드바에서 학교별 교육과정 편제표(.xlsm) 파일을 업로드해 주세요.")
    
    # 가이드 표시
    st.markdown("""
    ---
    ### 💡 사용 방법
    1. 왼쪽 사이드바의 **'파일 업로드'** 영역에 학교별 편제표 파일을 드래그 앤 드롭합니다.
    2. **'업로드 파일 분석 시작'** 버튼을 클릭합니다.
    3. 상단에 생성된 **학교별 탭**을 클릭하여 점검 결과와 총평을 확인합니다.
    4. **'엑셀 다운로드'**를 통해 전체 결과를 저장할 수 있습니다.
    5. 새로운 작업을 시작하려면 **'데이터 일괄 초기화'** 버튼을 누르세요.
    """)
