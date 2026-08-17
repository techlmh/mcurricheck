import openpyxl
import pandas as pd
import io

def parse_curriculum_xlsm(uploaded_file):
    """
    업로드된 엑셀 파일 객체를 읽어 데이터프레임으로 변환합니다.
    """
    # 메모리 상의 파일을 openpyxl로 로드
    file_bytes = uploaded_file.read()
    wb = openpyxl.load_workbook(io.BytesIO(file_bytes), data_only=True)
    
    # 1. 기초 정보 추출
    base_info = {"학교명": "알 수 없음", "지원청명": "알 수 없음", "설립별": "알 수 없음"}
    if '기초입력' in wb.sheetnames:
        ws_base = wb['기초입력']
        base_info = {
            "학년도": ws_base['C2'].value,
            "지원청명": ws_base['C3'].value,
            "설립별": ws_base['C4'].value,
            "학교명": ws_base['C5'].value
        }

    # 2. 학년별 데이터 파싱
    curriculum_data = []
    grade_sheets = ['1학년', '2학년', '3학년']
    
    for sheet_name in grade_sheets:
        if sheet_name not in wb.sheetnames:
            continue
            
        ws = wb[sheet_name]
        current_category = ""
        current_subject_group = ""
        
        # 8행부터 데이터 추출
        for row in range(8, 50):
            category = ws.cell(row=row, column=1).value
            subject_group = ws.cell(row=row, column=2).value
            subject_name = ws.cell(row=row, column=3).value
            
            if category: current_category = str(category).replace('\n', ' ').strip()
            if subject_group: current_subject_group = str(subject_group).replace('\n', ' ').strip()
            
            if not subject_name:
                continue
                
            item = {
                "학교명": base_info["학교명"],
                "학년": sheet_name,
                "대분류": current_category,
                "교과군": current_subject_group,
                "과목명": str(subject_name).strip(),
                "기준시수": ws.cell(row=row, column=6).value or 0,
                "편성시수": ws.cell(row=row, column=8).value or 0,
                "증감시수": ws.cell(row=row, column=10).value or 0,
                "학교자율시간": ws.cell(row=row, column=12).value or 0
            }
            curriculum_data.append(item)
            
    return base_info, pd.DataFrame(curriculum_data)
