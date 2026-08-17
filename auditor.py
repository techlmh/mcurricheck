import pandas as pd
import numpy as np

def audit_curriculum(df, school_name):
    """
    특정 학교의 데이터를 바탕으로 2027학년도 교육과정 지침 준수 여부를 점검합니다.
    """
    school_df = df[df['학교명'] == school_name]
    results = []
    
    # 1. 총 수업 시간 수 점검 (3개년 합계)
    total_hours = school_df['편성시수'].sum()
    results.append({
        "구분": "총 수업시수",
        "점검 기준": "3년간 최소 3,366시간 이상",
        "결과": "○" if total_hours >= 3366 else "×",
        "상세 내용": f"현재 {total_hours}시간 편성"
    })
    
    # 2. 체육 시수 점검
    pe_hours = school_df[school_df['교과군'].str.contains('체육', na=False)]['편성시수'].sum()
    results.append({
        "구분": "체육 시수",
        "점검 기준": "기준 시수(272시간) 이상 편성",
        "결과": "○" if pe_hours >= 272 else "×",
        "상세 내용": f"현재 {pe_hours}시간 편성"
    })
    
    # 3. 예술 시수 점검
    art_hours = school_df[school_df['교과군'].str.contains('예술', na=False)]['편성시수'].sum()
    results.append({
        "구분": "예술 시수",
        "점검 기준": "기준 시수(272시간) 이상 편성",
        "결과": "○" if art_hours >= 272 else "×",
        "상세 내용": f"현재 {art_hours}시간 편성"
    })
    
    # 4. 국·수·영 증감 범위 점검
    core_subjects = ['국어', '수학', '영어']
    core_diff = school_df[school_df['교과군'].isin(core_subjects)]['증감시수'].abs().sum()
    results.append({
        "구분": "국·수·영 증감",
        "점검 기준": "통합 102시간 이내 증감",
        "결과": "○" if core_diff <= 102 else "×",
        "상세 내용": f"현재 절대값 합계 {core_diff}시간"
    })
    
    # 5. 정보 시수 점검
    info_hours = school_df[school_df['과목명'].str.contains('정보', na=False)]['편성시수'].sum()
    results.append({
        "구분": "정보 시수",
        "점검 기준": "68시간 이상 편성",
        "결과": "○" if info_hours >= 68 else "×",
        "상세 내용": f"현재 {info_hours}시간 편성"
    })

    # 6. 학교자율시간 점검
    autonomy_hours = school_df['학교자율시간'].sum() if '학교자율시간' in school_df.columns else 0
    results.append({
        "구분": "학교자율시간",
        "점검 기준": "한 학기 33~34시간 편성",
        "결과": "○" if autonomy_hours >= 33 else "×",
        "상세 내용": f"현재 {autonomy_hours}시간 편성"
    })

    audit_df = pd.DataFrame(results)
    
    # 총평 생성
    fail_count = len(audit_df[audit_df['결과'] == '×'])
    if fail_count == 0:
        summary = f"✅ {school_name}은(는) 모든 교육과정 편성 지침을 준수하고 있습니다."
    else:
        summary = f"⚠️ {school_name}은(는) {fail_count}건의 지침 미준수 항목이 발견되었습니다. 시수 조정을 검토하십시오."
        
    return audit_df, summary
