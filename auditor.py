"""2027학년도 중학교 교육과정 편성 자율 점검표 기반 시트별 점검 엔진."""

from __future__ import annotations

from typing import Any, Callable

import pandas as pd

SHEET_ORDER = ("1학년", "2학년", "3학년", "학년전체")
PASS = "○"
FAIL = "×"
REVIEW = "검토 필요"

# 자율 점검표에 제시된 순서와 문구를 그대로 반영한다.
CHECKLIST = (
    ("01", "교과 시수", "교과(군)별 증감 범위(3년간 기준시수의 20%)를 초과하지 않았는가?", "교과 교육과정을 정상적으로 운영할 수 있는 범위 내에서 증감"),
    ("02", "교과 시수", "체육, 예술(음악/미술) 기준 시수를 준수하였는가?", "각 교과(군) 272시간 이상"),
    ("03", "교과 시수", "국어, 수학, 영어 통합하여 102시간 범위에서 증감하였는가?", "|국어 증감| + |수학 증감| + |영어 증감| ≤ 102"),
    ("04", "교과 시수", "정보는 68시간 이상 편성하였는가?", "정보 수업 시수와 정보 관련 학교자율시간을 모두 포함"),
    ("05", "선택", "선택 과목 개설 시 학생 선택권을 실질적으로 보장하고 있는가?", "종교 과목은 종교 이외 과목을 포함하여 복수 편성"),
    ("06", "선택", "학생 선택권을 주는 경우 성취도 산출 과목과 성취도 미산출 과목을 복수 개설하지 않았는가?", "과목군·시간표가 확인 가능한 범위에서 자동 점검"),
    ("07", "창·체", "창의적 체험활동 증감 범위(3년간 기준시수의 20%)를 초과하지 않았는가?", "기준 306시간, 245~367시간; 학교스포츠클럽 순증은 예외"),
    ("08", "창·체", "창의적 체험활동의 세부 영역은 균형 있게 편성하였는가?", "자율·자치, 동아리, 진로 영역의 3년간 편성 여부"),
    ("09", "학교자율시간", "학교자율시간은 3년 중 한 학기 이상 편성하였는가?", "한 학기 이상 운영"),
    ("10", "학교자율시간", "학교자율시간 과목은 한 학기 33~34시간으로 편성하였는가?", "학기별 1주 수업 시간 확보"),
    ("11", "학교자율시간", "학교자율시간 과목이 학기별로 이수되도록 편성하였는가?", "동일 과목의 2개 학기 분산 운영 불가"),
    ("12", "자유학기", "자유학기 활동은 교과 및 창의적 체험활동을 활용하여 102시간 편성하였는가?", "교과(군) 및 창체 기준시수 20% 범위 내 활용"),
    ("13", "자유학기", "자유학기 활동 2영역은 모두 편성하였는가?", "영역별 최소 17시간 이상"),
    ("14", "종합", "학기당 이수과목은 8개 이내로 편성하였는가?", "체육·예술·교양 선택·학교자율시간 과목은 제외"),
    ("15", "종합", "체육은 매 학기 편성하였는가?", "모든 학기에 체육 운영 시수가 있어야 함"),
    ("16", "종합", "범교과 학습 주제는 교과와 창의적 체험활동 등 교육 활동 전반에 걸쳐 통합적으로 운영하도록 계획하였는가?", "연간 교육과정 운영계획 등 별도 문서 확인 필요"),
    ("17", "종합", "협력종합예술활동은 중학교 3년 중 최소 1개 학기 이상 총 17시간 이상 운영하도록 계획하였는가?", "최소 17시간"),
)

UNSCORED_ELECTIVES = ("환경", "보건", "진로와 직업")
SCORED_ELECTIVES = ("한문", "생활 일본어", "생활 중국어", "중국어", "일본어")


def number(value: Any) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def pretty(value: float) -> int | float:
    return int(value) if float(value).is_integer() else round(value, 1)


def contains(value: str, token: str) -> bool:
    return token.replace(" ", "") in (value or "").replace(" ", "")


def has_token(row: dict[str, Any], *tokens: str) -> bool:
    fields = " ".join(str(row.get(field, "")) for field in ("group", "subject", "detail"))
    return any(contains(fields, token) for token in tokens)


def row_hours(row: dict[str, Any]) -> float:
    return number(row.get("operation_hours"))


def status_record(check_id: str, category: str, standard: str, status: str, evidence: str) -> dict[str, str]:
    return {
        "점검ID": check_id,
        "구분": category,
        "점검 기준": standard,
        "결과": status,
        "판정 근거": evidence,
    }


def subject_group_rows(payload: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    """자율 점검표의 교과(군) 단위로 과목 행을 묶는다."""
    groups: dict[str, list[dict[str, Any]]] = {
        "국어": [],
        "사회(역사 포함)/도덕": [],
        "수학": [],
        "과학/기술·가정/정보": [],
        "체육": [],
        "예술(음악/미술)": [],
        "영어": [],
        "선택": [],
    }
    for row in payload["subjects"]:
        if has_token(row, "국어"):
            groups["국어"].append(row)
        elif has_token(row, "사회", "역사", "도덕"):
            groups["사회(역사 포함)/도덕"].append(row)
        elif has_token(row, "수학"):
            groups["수학"].append(row)
        elif has_token(row, "과학", "기술·가정", "정보"):
            groups["과학/기술·가정/정보"].append(row)
        elif has_token(row, "체육"):
            groups["체육"].append(row)
        elif has_token(row, "예술", "음악", "미술"):
            groups["예술(음악/미술)"].append(row)
        elif has_token(row, "영어"):
            groups["영어"].append(row)
        elif has_token(row, "선택", "한문", "중국어", "일본어", "환경", "보건", "진로와 직업"):
            groups["선택"].append(row)
    return groups


def group_hours(rows: list[dict[str, Any]]) -> tuple[float, float]:
    """세부 과목 행의 기준시수와 실제 운영시수를 합산한다."""
    standard = sum(number(row.get("standard_hours")) for row in rows)
    operation = sum(row_hours(row) for row in rows)
    return standard, operation


def check_subject_range(payload: dict[str, Any]) -> tuple[str, str]:
    violations: list[str] = []
    checked: list[str] = []
    for group, rows in subject_group_rows(payload).items():
        if not rows:
            continue
        standard, operation = group_hours(rows)
        if standard <= 0:
            continue
        lower, upper = standard * 0.8, standard * 1.2
        text = f"{group} {pretty(operation)}/{pretty(standard)}"
        if lower <= operation <= upper:
            checked.append(text)
        else:
            violations.append(f"{text} (허용 {pretty(lower)}~{pretty(upper)})")
    if violations:
        return FAIL, "; ".join(violations)
    if not checked:
        return REVIEW, "교과(군) 운영 시수를 읽지 못했습니다. 원본 시트와 수식 결과를 확인하세요."
    return PASS, "; ".join(checked)


def check_pe_art(payload: dict[str, Any]) -> tuple[str, str]:
    groups = subject_group_rows(payload)
    pe = group_hours(groups["체육"])[1]
    art = group_hours(groups["예술(음악/미술)"])[1]
    if pe >= 272 and art >= 272:
        return PASS, f"체육 {pretty(pe)}시간, 예술 {pretty(art)}시간"
    failures = []
    if pe < 272:
        failures.append(f"체육 {pretty(pe)}시간")
    if art < 272:
        failures.append(f"예술 {pretty(art)}시간")
    return FAIL, ", ".join(failures) + " (각 272시간 이상 필요)"


def check_core_subjects(payload: dict[str, Any]) -> tuple[str, str]:
    groups = subject_group_rows(payload)
    details: list[str] = []
    total = 0.0
    for group in ("국어", "수학", "영어"):
        standard, operation = group_hours(groups[group])
        difference = abs(operation - standard)
        total += difference
        details.append(f"{group} {pretty(operation - standard):+}")
    status = PASS if total <= 102 else FAIL
    return status, f"절대값 합계 {pretty(total)}시간 ({', '.join(details)})"


def check_information_hours(payload: dict[str, Any]) -> tuple[str, str]:
    direct = sum(row_hours(row) for row in payload["subjects"] if has_token(row, "정보"))
    autonomy = sum(row_hours(row) for row in payload["autonomy_courses"] if has_token(row, "정보"))
    total = direct + autonomy
    status = PASS if total >= 68 else FAIL
    return status, f"정보 교과 {pretty(direct)}시간 + 정보 관련 학교자율시간 {pretty(autonomy)}시간 = {pretty(total)}시간"


def active_electives(payload: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        row for row in payload["subjects"]
        if has_token(row, "선택", "한문", "중국어", "일본어", "환경", "보건", "진로와 직업")
        and row_hours(row) > 0
    ]


def check_elective_choice(payload: dict[str, Any]) -> tuple[str, str]:
    electives = active_electives(payload)
    names = sorted({row["subject"] for row in electives})
    religion = [name for name in names if "종교" in name]
    non_religion = [name for name in names if "종교" not in name]
    if any(set(name) == {"_"} for name in names):
        return REVIEW, f"운영 시수가 있는 선택 기타 과목의 명칭이 미기재됨: {', '.join(names)}"
    if religion and not non_religion:
        return FAIL, f"종교 과목만 편성됨: {', '.join(religion)}"
    if len(names) < 2:
        return FAIL, f"편성된 선택 과목 {len(names)}개: {', '.join(names) or '없음'}"
    if religion:
        return PASS, f"종교 과목과 비종교 과목을 복수 편성: {', '.join(names)}"
    return PASS, f"편제상 선택 과목 {len(names)}개 편성: {', '.join(names)} (실제 수강신청·시간표는 별도 확인)"


def check_elective_assessment_mix(payload: dict[str, Any]) -> tuple[str, str]:
    elective_rows = active_electives(payload)
    if any(set(row.get("subject", "")) == {"_"} for row in elective_rows):
        return REVIEW, "운영 시수가 있는 선택 기타 과목의 명칭이 미기재되어 성취도 산출 여부를 판정할 수 없습니다."
    groups: dict[str, list[str]] = {}
    for row in elective_rows:
        code = str(row.get("selection_code") or "미분류")
        groups.setdefault(code, []).append(row["subject"])

    mixed: list[str] = []
    examined: list[str] = []
    for code, names in groups.items():
        scored = [name for name in names if any(token in name for token in SCORED_ELECTIVES)]
        unscored = [name for name in names if any(token in name for token in UNSCORED_ELECTIVES)]
        if scored and unscored:
            mixed.append(f"선택군 {code}: 성취도 산출({', '.join(scored)}) + 미산출({', '.join(unscored)})")
        elif names:
            examined.append(f"선택군 {code}: {', '.join(names)}")

    if mixed:
        return FAIL, "; ".join(mixed)
    if not examined:
        return REVIEW, "선택군·성취도 산출 여부를 판정할 수 있는 과목이 없습니다. 과목 편성 및 평가계획을 확인하세요."
    return PASS, "; ".join(examined) + " (과목별 성취도 산출 여부는 학교생활기록부 지침으로 최종 확인)"


def check_creative_hours(payload: dict[str, Any]) -> tuple[str, str]:
    creative_rows = payload["creative"]
    sports = sum(row_hours(row) for row in creative_rows if has_token(row, "학교스포츠클럽"))
    non_sports = sum(row_hours(row) for row in creative_rows if not has_token(row, "학교스포츠클럽"))
    status = PASS if 245 <= non_sports <= 367 else FAIL
    evidence = f"창체(학교스포츠클럽 제외) {pretty(non_sports)}시간 / 허용 245~367시간"
    if sports > 0:
        evidence += f"; 학교스포츠클럽 {pretty(sports)}시간은 순증 가능 여부 별도 확인"
    return status, evidence


def check_creative_balance(payload: dict[str, Any]) -> tuple[str, str]:
    areas = {
        "자율·자치": sum(row_hours(row) for row in payload["creative"] if has_token(row, "자율·자치")),
        "동아리": sum(row_hours(row) for row in payload["creative"] if has_token(row, "동아리") and not has_token(row, "학교스포츠클럽")),
        "진로": sum(row_hours(row) for row in payload["creative"] if has_token(row, "진로")),
    }
    missing = [area for area, hours in areas.items() if hours <= 0]
    evidence = ", ".join(f"{area} {pretty(hours)}시간" for area, hours in areas.items())
    if missing:
        return FAIL, evidence + f"; 미편성 영역: {', '.join(missing)}"
    return PASS, evidence


def active_autonomy_courses(payload: dict[str, Any]) -> list[dict[str, Any]]:
    return [row for row in payload["autonomy_courses"] if row_hours(row) > 0 and (row.get("subject") or row.get("detail") or row.get("group"))]


def check_autonomy_exists(payload: dict[str, Any]) -> tuple[str, str]:
    semester_hours = payload["autonomy_totals"]
    active = {semester: hours for semester, hours in semester_hours.items() if number(hours) > 0}
    if active:
        return PASS, ", ".join(f"{semester} {pretty(number(hours))}시간" for semester, hours in active.items())
    return FAIL, "학교자율시간 운영 시수가 없습니다."


def check_autonomy_hours(payload: dict[str, Any]) -> tuple[str, str]:
    active = {semester: number(hours) for semester, hours in payload["autonomy_totals"].items() if number(hours) > 0}
    invalid = {semester: hours for semester, hours in active.items() if hours not in {33, 34}}
    if not active:
        return FAIL, "학교자율시간 운영 시수가 없습니다."
    if invalid:
        return FAIL, ", ".join(f"{semester} {pretty(hours)}시간" for semester, hours in invalid.items()) + " (학기당 33~34시간 필요)"
    return PASS, ", ".join(f"{semester} {pretty(hours)}시간" for semester, hours in active.items())


def check_autonomy_completion(payload: dict[str, Any]) -> tuple[str, str]:
    courses = active_autonomy_courses(payload)
    if not courses:
        return FAIL, "학교자율시간 과목명·운영 시수를 찾지 못했습니다."
    split_courses: list[str] = []
    completed: list[str] = []
    for row in courses:
        name = row.get("subject") or row.get("detail") or row.get("group")
        active = {semester: number(hours) for semester, hours in row["operation_by_semester"].items() if number(hours) > 0}
        if len(active) != 1 or next(iter(active.values())) not in {33, 34}:
            split_courses.append(f"{name}: " + ", ".join(f"{semester} {pretty(hours)}시간" for semester, hours in active.items()))
        else:
            semester, hours = next(iter(active.items()))
            completed.append(f"{name}({semester} {pretty(hours)}시간)")
    if split_courses:
        return FAIL, "분산·비정규 편성: " + "; ".join(split_courses)
    return PASS, "; ".join(completed)


def check_free_semester_total(payload: dict[str, Any]) -> tuple[str, str]:
    active = {semester: number(hours) for semester, hours in payload["free_semester_totals"].items() if number(hours) > 0}
    if not active:
        return FAIL, "자유학기 활동 시수(합계)가 없습니다."
    invalid = {semester: hours for semester, hours in active.items() if hours != 102}
    if invalid:
        return FAIL, ", ".join(f"{semester} {pretty(hours)}시간" for semester, hours in invalid.items()) + " (102시간 필요)"
    return PASS, ", ".join(f"{semester} {pretty(hours)}시간" for semester, hours in active.items())


def check_free_semester_areas(payload: dict[str, Any]) -> tuple[str, str]:
    active = [(row.get("group") or row.get("subject") or "미분류", row_hours(row)) for row in payload["free_semester"] if row_hours(row) > 0]
    valid = [(name, hours) for name, hours in active if hours >= 17]
    evidence = ", ".join(f"{name} {pretty(hours)}시간" for name, hours in active) or "영역 데이터 없음"
    if len(valid) >= 2:
        return PASS, evidence
    return FAIL, evidence + " (2개 영역 이상, 각 17시간 이상 필요)"


def check_course_count(payload: dict[str, Any]) -> tuple[str, str]:
    counts = payload["course_count"]
    invalid = {semester: number(value) for semester, value in counts.items() if number(value) > 8}
    active = {semester: number(value) for semester, value in counts.items() if number(value) > 0}
    if invalid:
        return FAIL, ", ".join(f"{semester} {pretty(value)}과목" for semester, value in invalid.items())
    if not active:
        return REVIEW, "이수과목 수 행의 계산값을 읽지 못했습니다."
    return PASS, ", ".join(f"{semester} {pretty(value)}과목" for semester, value in active.items())


def check_pe_every_semester(payload: dict[str, Any]) -> tuple[str, str]:
    pe_rows = [row for row in payload["subjects"] if row.get("subject") == "체육"]
    if not pe_rows:
        return FAIL, "체육 과목 행이 없습니다."
    hours = pe_rows[0]["operation_by_semester"]
    missing = [semester for semester, value in hours.items() if number(value) <= 0]
    if missing:
        return FAIL, "미편성 학기: " + ", ".join(missing)
    return PASS, ", ".join(f"{semester} {pretty(number(value))}시간" for semester, value in hours.items())


def check_cross_curricular(_: dict[str, Any]) -> tuple[str, str]:
    return REVIEW, "편제표만으로 범교과 주제의 교과·창체 통합 운영계획을 확인할 수 없습니다. 학교 교육과정 운영계획을 첨부하여 수동 확인하세요."


def check_collaborative_art(payload: dict[str, Any]) -> tuple[str, str]:
    hours = number(payload.get("collaborative_art_hours"))
    status = PASS if hours >= 17 else FAIL
    return status, f"협력종합예술활동 {pretty(hours)}시간"


CHECK_FUNCTIONS: dict[str, Callable[[dict[str, Any]], tuple[str, str]]] = {
    "01": check_subject_range,
    "02": check_pe_art,
    "03": check_core_subjects,
    "04": check_information_hours,
    "05": check_elective_choice,
    "06": check_elective_assessment_mix,
    "07": check_creative_hours,
    "08": check_creative_balance,
    "09": check_autonomy_exists,
    "10": check_autonomy_hours,
    "11": check_autonomy_completion,
    "12": check_free_semester_total,
    "13": check_free_semester_areas,
    "14": check_course_count,
    "15": check_pe_every_semester,
    "16": check_cross_curricular,
    "17": check_collaborative_art,
}


def audit_sheet(payload: dict[str, Any]) -> pd.DataFrame:
    """시트 1개에 대해 자율 점검표 17개 기준을 모두 판정한다."""
    rows: list[dict[str, str]] = []
    for check_id, category, standard, note in CHECKLIST:
        status, evidence = CHECK_FUNCTIONS[check_id](payload)
        rows.append(status_record(check_id, category, standard, status, evidence + (f" | 기준: {note}" if note else "")))
    return pd.DataFrame(rows)


def audit_school(school_payload: dict[str, Any]) -> tuple[pd.DataFrame, pd.DataFrame, str]:
    """학교 1개에 대해 4개 시트 결과를 가로형 점검표와 근거표로 반환한다."""
    matrix = pd.DataFrame(
        [{"점검ID": check_id, "구분": category, "점검 기준": standard} for check_id, category, standard, _ in CHECKLIST]
    )
    evidence_frames: list[pd.DataFrame] = []

    for sheet_name in SHEET_ORDER:
        result = audit_sheet(school_payload["sheets"][sheet_name])
        matrix = matrix.merge(result[["점검ID", "결과"]].rename(columns={"결과": sheet_name}), on="점검ID", how="left")
        evidence = result.copy()
        evidence.insert(0, "점검시트", sheet_name)
        evidence_frames.append(evidence)

    evidence_df = pd.concat(evidence_frames, ignore_index=True)
    status_values = matrix[list(SHEET_ORDER)].to_numpy().ravel().tolist()
    fail_count = sum(value == FAIL for value in status_values)
    review_count = sum(value == REVIEW for value in status_values)
    pass_count = sum(value == PASS for value in status_values)
    school = school_payload["metadata"]["학교명"]

    summary = (
        f"{school}의 4개 시트·17개 기준(총 {len(status_values)}건) 점검 결과입니다. "
        f"준수 {pass_count}건, 미준수 {fail_count}건, 수동 검토 필요 {review_count}건입니다."
    )
    if fail_count:
        summary += " 미준수(×) 항목의 시수·편성 방식을 우선 수정한 뒤 재점검하세요."
    if review_count:
        summary += " ‘검토 필요’ 항목은 편제표 외의 시간표·수강신청·연간운영계획 자료를 함께 확인해야 합니다."
    return matrix, evidence_df, summary


def audit_all_schools(school_payloads: list[dict[str, Any]]) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """여러 학교의 가로형 결과, 세부 근거, 메타데이터를 엑셀 내보내기용으로 생성한다."""
    matrices: list[pd.DataFrame] = []
    evidence_list: list[pd.DataFrame] = []
    summaries: list[dict[str, Any]] = []

    for payload in school_payloads:
        matrix, evidence, summary = audit_school(payload)
        metadata = payload["metadata"]
        matrix.insert(0, "학교명", metadata["학교명"])
        matrix.insert(1, "학년도", metadata.get("학년도"))
        evidence.insert(0, "학교명", metadata["학교명"])
        evidence.insert(1, "학년도", metadata.get("학년도"))
        matrices.append(matrix)
        evidence_list.append(evidence)
        summaries.append(
            {
                **metadata,
                "총평": summary,
                "미준수(×)": int((matrix[list(SHEET_ORDER)] == FAIL).sum().sum()),
                "검토 필요": int((matrix[list(SHEET_ORDER)] == REVIEW).sum().sum()),
                "준수(○)": int((matrix[list(SHEET_ORDER)] == PASS).sum().sum()),
            }
        )

    return (
        pd.concat(matrices, ignore_index=True) if matrices else pd.DataFrame(),
        pd.concat(evidence_list, ignore_index=True) if evidence_list else pd.DataFrame(),
        pd.DataFrame(summaries),
    )
