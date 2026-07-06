"""W2 시계열: 생산자–수용자 격차의 3개년 추세 (2021·2023·2025 더블이어).
- GAP-1 5속성(기자 자기평가 vs 수용자 평가): 깨끗한 3개년.
- GAP-2 역할7: 기자 중요도 vs 수용자 수행체감(깨끗) + 기자 실행바(2025 대상단절 캐비엇).
기자=비가중. 수용자 가중치: 2021·2025=WT, 2023=HMWT. 유효값 1~5.
크로스워크 근거: notes/03-question-mapping.md F절.
실행: ./.venv/bin/python analysis/08_timeseries_gap.py
"""
import pyreadstat, pandas as pd, numpy as np

def valid(s): s = pd.to_numeric(s, errors="coerce"); return s.where(s.between(1, 5))
def umean(df, c): v = valid(df[c]); return v.mean(), int(v.notna().sum())
def wmean(df, c, w):
    v = valid(df[c]); ww = pd.to_numeric(df[w], errors="coerce")
    m = v.notna() & ww.notna(); return np.average(v[m], weights=ww[m]), int(m.sum())

def load(p): d, _ = pyreadstat.read_sav(p); return d

PATH = {
    "j2021": "data/raw/journalist_2021/[로데이터] 제15회 언론인 조사 데이터.SAV",
    "j2023": "data/raw/journalist_2023/[로데이터] 2023 언론인 조사 원본 데이터(SAV).SAV",
    "j2025": "data/raw/journalist_2025/[로데이터] 2025 언론인 조사 원본 데이터.SAV",
    "a2021": "data/raw/audience_2021/2021 언론수용자 조사 DATA_통계표_보고서 등/2021 언론수용자 조사 DATA_공개용_최종.sav",
    "a2023": "data/raw/audience_2023/2023 언론수용자 조사 DATA_통계표 등/2. 2023 언론수용자 조사_최종데이터(공개용).sav",
    "a2025": "data/raw/audience_2025/3. 2025 언론수용자 조사_최종데이터.SAV",
}
AWT = {"2021": "WT", "2023": "HMWT", "2025": "WT"}
J = {"2021": load(PATH["j2021"]), "2023": load(PATH["j2023"]), "2025": load(PATH["j2025"])}
A = {"2021": load(PATH["a2021"]), "2023": load(PATH["a2023"]), "2025": load(PATH["a2025"])}

def jm(y, c): return umean(J[y], c)[0]                 # 기자 비가중 평균
def am(y, c): return wmean(A[y], c, AWT[y])[0]         # 수용자 가중 평균

# ---------- GAP-1 · 5속성 (기자 자기평가 vs 수용자) ----------
# (속성, 기자변수, {연도: 수용자변수})
ATTR = [
    ("공정",   "q1_1", {"2021": "Q78_1", "2023": "Q77_1", "2025": "Q85_1"}),
    ("전문",   "q1_2", {"2021": "Q78_2", "2023": "Q77_2", "2025": "Q85_2"}),
    ("정확",   "q1_3", {"2021": "Q78_3", "2023": "Q77_3", "2025": "Q85_3"}),
    ("자유",   "q1_6", {"2021": "Q78_5", "2023": "Q77_4", "2025": "Q85_4"}),
    ("영향력", "q1_5", {"2021": "Q78_6", "2023": "Q77_5", "2025": "Q85_5"}),
]
YEARS = ["2021", "2023", "2025"]
# 언론인 2021은 변수명 대문자(Q1_..), 2023·2025는 소문자(q1_..)
def jc(y, c): return c.upper() if y == "2021" else c

rows1 = []
for name, jvar, avars in ATTR:
    for y in YEARS:
        ji = jm(y, jc(y, jvar)); ap = am(y, avars[y])
        rows1.append({"속성": name, "연도": y, "기자": round(ji, 3),
                      "수용자": round(ap, 3), "격차(기자−수용자)": round(ji - ap, 3)})
g1 = pd.DataFrame(rows1)
g1_year = g1.groupby("연도")[["기자", "수용자", "격차(기자−수용자)"]].mean().round(3)

# ---------- GAP-2 · 역할7 (중요도 vs 수행체감 + 실행바) ----------
ROLE = ["정확정보", "다양의견", "해결책", "의제설정", "정부감시", "기업감시", "약자대변"]
# 수용자 수행체감 배터리 접두(연도별)
A_ROLE = {"2021": "Q80_", "2023": "Q78_", "2025": "Q86_"}
rows2 = []
for i, role in enumerate(ROLE, start=1):
    for y in YEARS:
        imp = jm(y, jc(y, f"q2_{i}"))          # 기자 중요도
        exe = jm(y, jc(y, f"q3_{i}"))          # 기자 실행(2021·2023 자사 / 2025 전반)
        perc = am(y, f"{A_ROLE[y]}{i}")        # 수용자 수행체감
        rows2.append({"역할": role, "연도": y,
                      "기자_중요도": round(imp, 3), "기자_실행": round(exe, 3),
                      "수용자_체감": round(perc, 3),
                      "중요도−체감": round(imp - perc, 3)})
g2 = pd.DataFrame(rows2)
g2_year = g2.groupby("연도")[["기자_중요도", "기자_실행", "수용자_체감", "중요도−체감"]].mean().round(3)

pd.set_option("display.unicode.east_asian_width", True)
print("### GAP-1 · 5속성 기자 자기평가 vs 수용자 (2021·2023·2025)")
print(g1.pivot(index="속성", columns="연도", values="격차(기자−수용자)").round(3).to_string())
print("\n[연도 평균] 기자·수용자·격차")
print(g1_year.to_string())

print("\n### GAP-2 · 역할7 이상-체감 격차 (기자 중요도 − 수용자 체감)")
print(g2.pivot(index="역할", columns="연도", values="중요도−체감").reindex(ROLE).round(3).to_string())
print("\n[연도 평균] 중요도·실행·체감·(중요도−체감)")
print(g2_year.to_string())
print("\n※ 기자_실행: 2021·2023='소속 언론사(자사)' / 2025='우리나라 언론 전반' → 대상 단절(캐비엇 F). 시계열 해석 주의.")

import os
os.makedirs("data/processed", exist_ok=True)
g1.to_csv("data/processed/ts_gap1_5attr.csv", index=False, encoding="utf-8-sig")
g2.to_csv("data/processed/ts_gap2_roles.csv", index=False, encoding="utf-8-sig")
g1_year.to_csv("data/processed/ts_gap1_yearmean.csv", encoding="utf-8-sig")
g2_year.to_csv("data/processed/ts_gap2_yearmean.csv", encoding="utf-8-sig")
print("\n저장: data/processed/ts_gap1_5attr.csv, ts_gap2_roles.csv, ts_gap1_yearmean.csv, ts_gap2_yearmean.csv")
