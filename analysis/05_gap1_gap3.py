"""GAP① 언론 5속성(2025) + GAP③ 뉴스 문제점 심각성(2023, 공통항목).
기자=비가중, 수용자=WT 가중. 유효값 1~5."""
import pyreadstat, pandas as pd, numpy as np

def valid(s): s = pd.to_numeric(s, errors="coerce"); return s.where(s.between(1, 5))
def umean(df, c): v = valid(df[c]); return v.mean(), int(v.notna().sum())
def wmean(df, c, w="WT"):
    v = valid(df[c]); ww = pd.to_numeric(df[w], errors="coerce")
    m = v.notna() & ww.notna(); return np.average(v[m], weights=ww[m]), int(m.sum())

# ---------- GAP① 5속성 (2025) ----------
j25, _ = pyreadstat.read_sav("data/raw/journalist_2025/[로데이터] 2025 언론인 조사 원본 데이터.SAV")
a25, _ = pyreadstat.read_sav("data/raw/audience_2025/3. 2025 언론수용자 조사_최종데이터.SAV")
# 의미 기준 매핑(순서 다름): 자유=j q1_6↔a Q85_4, 영향력=j q1_5↔a Q85_5
G1 = [("공정", "q1_1", "Q85_1"), ("전문", "q1_2", "Q85_2"), ("정확", "q1_3", "Q85_3"),
      ("자유", "q1_6", "Q85_4"), ("영향력", "q1_5", "Q85_5")]
r1 = []
for name, jc, ac in G1:
    ji, _ = umean(j25, jc); ap, _ = wmean(a25, ac)
    r1.append({"속성": name, "기자_자기평가": round(ji,3), "수용자_평가": round(ap,3),
               "격차(기자−수용자)": round(ji-ap,3)})
df1 = pd.DataFrame(r1)
# 참고: 기자 신뢰 자기평가
trust_j,_ = umean(j25,"q1_4")

# ---------- GAP③ 뉴스 문제점 심각성 (2023, 공통 6항목) ----------
j23, jm23 = pyreadstat.read_sav("data/raw/journalist_2023/[로데이터] 2023 언론인 조사 원본 데이터(SAV).SAV")
a23, am23 = pyreadstat.read_sav("data/raw/audience_2023/2023 언론수용자 조사 DATA_통계표 등/2. 2023 언론수용자 조사_최종데이터(공개용).sav")
jl23 = dict(zip(jm23.column_names, jm23.column_labels)); al23 = dict(zip(am23.column_names, am23.column_labels))
WT23 = "HMWT"  # 수용자2023 가중치 변수명(2025=WT와 다름)
has_wt23 = WT23 in am23.column_names
# 공통 항목: 기자 q16_x ↔ 수용자 Q83_x (오보·낚시성·어뷰징·편파·광고성·가짜뉴스)
G3 = [("오보","q16_1","Q83_1"),("낚시성","q16_2","Q83_2"),("어뷰징","q16_3","Q83_3"),
      ("편파","q16_4","Q83_4"),("광고성","q16_5","Q83_5"),("가짜뉴스","q16_7","Q83_8")]
print("### GAP③ 매핑 라벨 검증")
for n,jc,ac in G3:
    print(f"  [{n}] 기자 {jc}: {jl23.get(jc)}  ||  수용자 {ac}: {al23.get(ac)}")
print(f"  수용자2023 WT 존재: {has_wt23}")

r3 = []
for n, jc, ac in G3:
    ji,_ = umean(j23, jc)
    ap = wmean(a23, ac, WT23)[0] if has_wt23 else umean(a23, ac)[0]
    r3.append({"문제점": n, "기자_심각성": round(ji,3), "수용자_심각성": round(ap,3),
               "격차(수용자−기자)": round(ap-ji,3)})
df3 = pd.DataFrame(r3)

pd.set_option("display.unicode.east_asian_width", True)
print("\n### GAP① 언론 5속성 자기평가 vs 수용자평가 (2025)")
print(df1.to_string(index=False))
print(f"기자 신뢰 자기평가 q1_4 = {trust_j:.2f} (참고)")
print(f"평균 — 기자 {df1.기자_자기평가.mean():.2f} / 수용자 {df1.수용자_평가.mean():.2f}")
print("\n### GAP③ 뉴스 문제점 심각성 (2023, 공통6)")
print(df3.to_string(index=False))
print(f"평균 — 기자 {df3.기자_심각성.mean():.2f} / 수용자 {df3.수용자_심각성.mean():.2f}")

df1.to_csv("data/processed/gap1_5attr_2025.csv", index=False, encoding="utf-8-sig")
df3.to_csv("data/processed/gap3_problems_2023.csv", index=False, encoding="utf-8-sig")
print("\n저장: data/processed/gap1_5attr_2025.csv, gap3_problems_2023.csv")
