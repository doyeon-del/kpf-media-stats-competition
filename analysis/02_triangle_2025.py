"""W2-2: 2025 7개 역할 3각비교 (기자 중요도 / 기자 실천인식 / 수용자 수행체감).

- 기자(언론인조사): 비가중 평균  q2_x(중요도), q3_x(실천)
- 수용자(수용자조사): 가중평균(WT) Q86_x(수행 체감)
- 유효값 1~5만 사용(9=모름/무응답 등 제외)
"""
import pyreadstat, pandas as pd, numpy as np

ROLES = [
    "사회현안 정확한 정보제공", "다양한 의견 제시", "해결책 제시",
    "중요 사회문제 의제설정", "정부·공인 감시", "기업활동 감시", "사회적 약자 대변",
]

jpath = "data/raw/journalist_2025/[로데이터] 2025 언론인 조사 원본 데이터.SAV"
apath = "data/raw/audience_2025/3. 2025 언론수용자 조사_최종데이터.SAV"
jdf, _ = pyreadstat.read_sav(jpath)
adf, _ = pyreadstat.read_sav(apath)

def valid(s):
    s = pd.to_numeric(s, errors="coerce")
    return s.where(s.between(1, 5))

def umean(df, col):
    v = valid(df[col]); return v.mean(), v.notna().sum()

def wmean(df, col, w="WT"):
    v = valid(df[col]); ww = pd.to_numeric(df[w], errors="coerce")
    m = v.notna() & ww.notna()
    return np.average(v[m], weights=ww[m]), int(m.sum())

rows = []
for i, name in enumerate(ROLES, 1):
    imp, n_imp = umean(jdf, f"q2_{i}")      # 기자 중요도
    exe, n_exe = umean(jdf, f"q3_{i}")      # 기자 실천 인식
    perc, n_per = wmean(adf, f"Q86_{i}")    # 수용자 수행 체감
    rows.append({
        "역할": name,
        "기자_중요도": round(imp, 3),
        "기자_실천인식": round(exe, 3),
        "수용자_수행체감": round(perc, 3),
        "격차_중요도−체감": round(imp - perc, 3),
        "격차_기자실천−수용체감": round(exe - perc, 3),
    })

res = pd.DataFrame(rows)
pd.set_option("display.unicode.east_asian_width", True)
print(res.to_string(index=False))
print(f"\nn(언론인)={valid(jdf['q2_1']).notna().sum()}, n(수용자,가중전)={valid(adf['Q86_1']).notna().sum()}")
print(f"전체 평균 — 기자 중요도 {res.기자_중요도.mean():.2f} / 기자 실천 {res.기자_실천인식.mean():.2f} / 수용자 체감 {res.수용자_수행체감.mean():.2f}")

res.to_csv("data/processed/triangle_2025.csv", index=False, encoding="utf-8-sig")
print("\n저장: data/processed/triangle_2025.csv")
