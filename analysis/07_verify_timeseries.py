"""W2 시계열 확장 착수 전 검증.
2021·2023 언론인 / 2021·2022 수용자 .sav 메타데이터를 스캔해
5속성·역할7·문제점8 문항과 가중치 변수의 연도별 변수명/라벨을 대조한다.
메타데이터만 읽으므로 빠르다. 실행: ./.venv/bin/python analysis/07_verify_timeseries.py
"""
import pyreadstat

FILES = {
    "journalist_2021": "data/raw/journalist_2021/[로데이터] 제15회 언론인 조사 데이터.SAV",
    "journalist_2023": "data/raw/journalist_2023/[로데이터] 2023 언론인 조사 원본 데이터(SAV).SAV",
    "journalist_2025": "data/raw/journalist_2025/[로데이터] 2025 언론인 조사 원본 데이터.SAV",
    "audience_2021":   "data/raw/audience_2021/2021 언론수용자 조사 DATA_통계표_보고서 등/2021 언론수용자 조사 DATA_공개용_최종.sav",
    "audience_2022":   "data/raw/audience_2022/2022 언론수용자 조사 DATA_통계표_보고서 등/데이터/2022 언론수용자 조사_개인용_공개용 데이터.SAV",
    "audience_2023":   "data/raw/audience_2023/2023 언론수용자 조사 DATA_통계표 등/2. 2023 언론수용자 조사_최종데이터(공개용).sav",
    "audience_2025":   "data/raw/audience_2025/3. 2025 언론수용자 조사_최종데이터.SAV",
}

# 개념별 라벨 키워드(부분일치). 워딩이 연도별로 미세하게 달라 넓게 잡는다.
CONCEPTS = {
    "5속성(공정/전문/정확/자유/영향)": ["공정", "전문", "정확", "자유롭", "영향력"],
    "역할7(감시/대변/의제/해결)":       ["감시", "대변", "의제", "해결책", "다양한 의견", "정보를 제공", "정확한 정보"],
    "문제점8(오보/낚시/어뷰징/편파/가짜)": ["오보", "낚시", "어뷰징", "받아쓰", "편파", "광고성", "가짜뉴스", "허위"],
    "가중치":                            ["가중", "weight", "wt"],
}

def scan(tag, path):
    print(f"\n{'='*70}\n### {tag}\n{'='*70}")
    try:
        _, meta = pyreadstat.read_sav(path, metadataonly=True)
    except Exception as e:
        print(f"  [읽기 실패] {e}")
        return
    labels = dict(zip(meta.column_names, meta.column_labels))
    print(f"  총 변수 {len(meta.column_names)}개")
    for concept, kws in CONCEPTS.items():
        hits = []
        for name, lab in labels.items():
            lab_s = (lab or "")
            name_s = name or ""
            if any(k.lower() in lab_s.lower() or k.lower() in name_s.lower() for k in kws):
                hits.append((name, lab_s))
        print(f"\n  --- {concept} ({len(hits)} hit) ---")
        for name, lab in hits[:40]:
            print(f"    {name:14} | {lab[:60]}")

if __name__ == "__main__":
    for tag, path in FILES.items():
        scan(tag, path)
