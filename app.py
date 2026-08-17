"""2027학년도 중학교 교육과정 편성 자율 점검 Streamlit 대시보드."""

from __future__ import annotations

from io import BytesIO

import pandas as pd
import streamlit as st

from auditor import FAIL, PASS, REVIEW, SHEET_ORDER, audit_all_schools, audit_school
from utils import flatten_curriculum_data, parse_curriculum_xlsm

st.set_page_config(page_title="2027 중학교 교육과정 점검", page_icon="📘", layout="wide")

if "school_payloads" not in st.session_state:
    st.session_state.school_payloads = []
if "processing_errors" not in st.session_state:
    st.session_state.processing_errors = []


def status_style(value: str) -> str:
    """점검표의 판정값을 색으로 구분한다."""
    styles = {
        PASS: "background-color: #d1fae5; color: #065f46; font-weight: 700; text-align: center;",
        FAIL: "background-color: #fee2e2; color: #991b1b; font-weight: 700; text-align: center;",
        REVIEW: "background-color: #fef3c7; color: #92400e; font-weight: 700; text-align: center;",
    }
    return styles.get(value, "")


def make_download_file(school_payloads: list[dict]) -> bytes:
    """전체 학교 점검 결과를 다중 시트 엑셀 파일로 생성한다."""
    matrix_df, evidence_df, summary_df = audit_all_schools(school_payloads)
    raw_rows = []
    for payload in school_payloads:
        raw_rows.extend(flatten_curriculum_data(payload))
    raw_df = pd.DataFrame(raw_rows)

    output = BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        summary_df.to_excel(writer, index=False, sheet_name="학교별 총평")
        matrix_df.to_excel(writer, index=False, sheet_name="점검결과")
        evidence_df.to_excel(writer, index=False, sheet_name="점검근거")
        raw_df.to_excel(writer, index=False, sheet_name="원시편제데이터")

        workbook = writer.book
        header_format = workbook.add_format({"bold": True, "bg_color": "#1F4E78", "font_color": "#FFFFFF", "border": 1, "text_wrap": True})
        pass_format = workbook.add_format({"bg_color": "#D1FAE5", "font_color": "#065F46", "bold": True, "align": "center"})
        fail_format = workbook.add_format({"bg_color": "#FEE2E2", "font_color": "#991B1B", "bold": True, "align": "center"})
        review_format = workbook.add_format({"bg_color": "#FEF3C7", "font_color": "#92400E", "bold": True, "align": "center"})

        for sheet_name, frame in {
            "학교별 총평": summary_df,
            "점검결과": matrix_df,
            "점검근거": evidence_df,
            "원시편제데이터": raw_df,
        }.items():
            worksheet = writer.sheets[sheet_name]
            worksheet.freeze_panes(1, 0)
            worksheet.set_row(0, 34, header_format)
            worksheet.autofilter(0, 0, max(len(frame), 1), max(len(frame.columns) - 1, 0))
            for column_index, column_name in enumerate(frame.columns):
                width = 15
                if column_name in {"점검 기준", "판정 근거", "총평"}:
                    width = 62
                elif column_name in {"학교명", "파일명"}:
                    width = 20
                elif column_name in SHEET_ORDER:
                    width = 13
                worksheet.set_column(column_index, column_index, width)

        result_sheet = writer.sheets["점검결과"]
        for column_index, column_name in enumerate(matrix_df.columns):
            if column_name in SHEET_ORDER:
                result_sheet.conditional_format(1, column_index, max(len(matrix_df), 1), column_index, {"type": "text", "criteria": "containing", "value": PASS, "format": pass_format})
                result_sheet.conditional_format(1, column_index, max(len(matrix_df), 1), column_index, {"type": "text", "criteria": "containing", "value": FAIL, "format": fail_format})
                result_sheet.conditional_format(1, column_index, max(len(matrix_df), 1), column_index, {"type": "text", "criteria": "containing", "value": REVIEW, "format": review_format})

    return output.getvalue()


def render_school_report(payload: dict) -> None:
    """학교 탭 하나에 점검표·근거·상세 데이터·총평을 표시한다."""
    metadata = payload["metadata"]
    matrix_df, evidence_df, summary = audit_school(payload)

    st.subheader(f"{metadata['학교명']} 점검 결과")
    st.caption(
        f"학년도 {metadata.get('학년도', '')} · {metadata.get('지원청명', '')} · {metadata.get('설립별', '')} · 원본 파일: {metadata.get('파일명', '')}"
    )
    st.markdown(
        "**판정 표시:** ○ 자동 점검상 준수 · × 미준수 또는 필수 입력 누락 · 검토 필요 편제표만으로 판정할 수 없어 별도 운영계획·시간표 확인 필요"
    )

    styled = matrix_df.style.map(status_style, subset=list(SHEET_ORDER))
    st.dataframe(styled, use_container_width=True, hide_index=True, height=685)

    st.markdown("#### 시트별 판정 근거")
    evidence_tabs = st.tabs(list(SHEET_ORDER))
    for index, sheet_name in enumerate(SHEET_ORDER):
        with evidence_tabs[index]:
            sheet_evidence = evidence_df[evidence_df["점검시트"] == sheet_name][["구분", "점검 기준", "결과", "판정 근거"]]
            sheet_styled = sheet_evidence.style.map(status_style, subset=["결과"])
            st.dataframe(sheet_styled, use_container_width=True, hide_index=True, height=580)

    with st.expander("시트별 원시 편제 데이터 확인", expanded=False):
        raw_rows = flatten_curriculum_data(payload)
        raw_df = pd.DataFrame(raw_rows)
        raw_tabs = st.tabs(list(SHEET_ORDER))
        for index, sheet_name in enumerate(SHEET_ORDER):
            with raw_tabs[index]:
                st.dataframe(raw_df[raw_df["점검시트"] == sheet_name], use_container_width=True, hide_index=True)

    st.divider()
    st.markdown("#### 학교별 총평")
    fail_count = int((matrix_df[list(SHEET_ORDER)] == FAIL).sum().sum())
    review_count = int((matrix_df[list(SHEET_ORDER)] == REVIEW).sum().sum())
    if fail_count:
        st.error(summary)
    elif review_count:
        st.warning(summary)
    else:
        st.success(summary)


st.title("2027학년도 중학교 교육과정 편성 자율 점검")
st.write("제출된 교육과정 편제표(`.xlsm`)를 업로드하면 **1학년·2학년·3학년·학년전체** 시트를 각각 판정하여 자율 점검표 형식으로 제공합니다.")

with st.sidebar:
    st.header("파일 관리")
    uploaded_files = st.file_uploader(
        "교육과정 편제표 업로드 (.xlsm)",
        type=["xlsm"],
        accept_multiple_files=True,
        help="Excel에서 수식 계산 후 저장한 2027학년도 중학교 교육과정 편제표 파일을 업로드하세요.",
    )

    if st.button("업로드 파일 점검 시작", type="primary", use_container_width=True, disabled=not uploaded_files):
        parsed_payloads = []
        errors = []
        used_school_names = set()
        for uploaded_file in uploaded_files or []:
            try:
                payload = parse_curriculum_xlsm(uploaded_file, source_name=uploaded_file.name)
                school_name = payload["metadata"]["학교명"]
                if school_name in used_school_names:
                    raise ValueError(f"중복 학교명입니다: {school_name}")
                used_school_names.add(school_name)
                parsed_payloads.append(payload)
            except Exception as exc:
                errors.append(f"{uploaded_file.name}: {exc}")
        st.session_state.school_payloads = parsed_payloads
        st.session_state.processing_errors = errors
        if parsed_payloads:
            st.success(f"{len(parsed_payloads)}개 학교 파일을 시트별로 파싱하여 점검했습니다.")
        if errors:
            st.error("일부 파일을 처리하지 못했습니다. 아래 오류 목록을 확인하세요.")

    if st.button("업로드·점검 결과 일괄 초기화", use_container_width=True, help="현재 세션에 저장된 모든 업로드 파일 데이터와 점검 결과를 삭제합니다."):
        st.session_state.school_payloads = []
        st.session_state.processing_errors = []
        st.rerun()

    st.divider()
    st.caption("초기화는 현재 브라우저 세션의 처리 데이터만 삭제하며, 원본 파일은 서버에 저장하지 않습니다.")

if st.session_state.processing_errors:
    with st.expander("처리 오류 보기", expanded=True):
        for error in st.session_state.processing_errors:
            st.error(error)

school_payloads = st.session_state.school_payloads
if not school_payloads:
    st.info("왼쪽 파일 관리 영역에서 하나 이상의 `.xlsm` 파일을 업로드한 후 **업로드 파일 점검 시작**을 선택하세요.")
    st.markdown(
        """
        ### 처리 절차
        1. 학교별 교육과정 편제표 파일을 복수 선택하여 업로드합니다.
        2. 각 학교는 별도 탭으로 표시되며, 자율 점검표의 17개 기준에 대해 4개 시트의 결과를 한 표에서 확인합니다.
        3. 표 아래의 **시트별 판정 근거**에서 계산값과 미준수 사유를 확인합니다.
        4. 작업을 새로 시작하려면 **업로드·점검 결과 일괄 초기화**를 선택합니다.
        """
    )
else:
    download_data = make_download_file(school_payloads)
    st.download_button(
        label="전체 학교 점검 결과 엑셀 다운로드",
        data=download_data,
        file_name="2027학년도_중학교_교육과정_시트별_점검결과.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        type="secondary",
    )

    school_tabs = st.tabs([payload["metadata"]["학교명"] for payload in school_payloads])
    for index, payload in enumerate(school_payloads):
        with school_tabs[index]:
            render_school_report(payload)
