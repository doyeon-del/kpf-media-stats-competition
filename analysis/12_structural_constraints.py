# -*- coding: utf-8 -*-
"""언론인 조사 3개년 — 구조적 제약 근거 집계 (비가중)"""
import os, sys
sys.stdout.reconfigure(encoding="utf-8")
import pandas as pd
import pyreadstat

_HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(os.path.dirname(_HERE), "data", "raw")
PATHS = {
    2021: RAW + r"\journalist_2021\[로데이터] 제15회 언론인 조사 데이터.SAV",
    2023: RAW + r"\journalist_2023\[로데이터] 2023 언론인 조사 원본 데이터(SAV).SAV",
    2025: RAW + r"\journalist_2025\[로데이터] 2025 언론인 조사 원본 데이터.SAV",
}
dfs = {}
for y, p in PATHS.items():
    df, _ = pyreadstat.read_sav(p)
    df.columns = [c.lower() for c in df.columns]
    dfs[y] = df

FACTORS = {1: "사주/사장", 2: "편집·보도국 간부", 3: "기자의 자기검열", 4: "정부나 정치권",
           5: "광고주", 6: "이익단체", 7: "시민단체", 8: "독자·시청자·네티즌", 9: "언론 관련 법·제도", 10: "기타"}

def pct(s, vals):
    s = s.dropna()
    return 100 * s.isin(vals).mean(), len(s)

print("=" * 70)
print("① 언론 자유 제한 요인 (1~3순위 언급률 %, 복수응답)")
print("=" * 70)
res = {}
# 2021/2023: 더미형 (q15_k / q13_k), 2025: 순위형 (q12, q12_m2, q12_m3)
for y, pref in [(2021, "q15_"), (2023, "q13_")]:
    d = dfs[y]
    out = {}
    for k, name in FACTORS.items():
        col = d[f"{pref}{k}"]
        sel = col.notna() & (col != 0)
        out[name] = 100 * sel.mean()
    res[y] = out
d = dfs[2025]
ranks = d[["q12", "q12_m2", "q12_m3"]]
out = {}
for k, name in FACTORS.items():
    out[name] = 100 * ranks.apply(lambda r: (r == k).any(), axis=1).mean()
res[2025] = out
tbl = pd.DataFrame(res).round(1)
print(tbl.sort_values(2025, ascending=False).to_string())

print()
print("=" * 70)
print("② 취재·보도 자유 체감 (5점: 1=전혀 자유롭지 않다)")
print("=" * 70)
for y, v in [(2021, "q14"), (2023, "q12"), (2025, "q11")]:
    s = dfs[y][v].dropna()
    print(f"{y}: 평균 {s.mean():.2f} | 자유롭지 않다(1-2) {100*s.isin([1,2]).mean():.1f}% | 자유롭다(4-5) {100*s.isin([4,5]).mean():.1f}% (n={len(s)})")

print()
print("=" * 70)
print("③ 주간 기사 보도·제작 건수 (기사 쓰는 응답자만)")
print("=" * 70)
def weekly(y, prefixes):
    d = dfs[y]
    cols = [c for c in d.columns for p in prefixes if c.startswith(p) and not c.endswith("text")]
    t = d[cols].fillna(0).sum(axis=1)
    t = t[t > 0]
    return t
for y, prefixes in [(2021, ["q8_1a", "q8_1b"]), (2023, ["q7_1a", "q7_1b"]), (2025, ["q6_1"])]:
    t = weekly(y, prefixes)
    print(f"{y}: 평균 {t.mean():.1f}건/주 | 중앙값 {t.median():.0f}건 | 상위25% {t.quantile(0.75):.0f}건+ (n={len(t)})")

print()
print("=" * 70)
print("④ 취재방식 활용도 (5점): 현장취재 vs 출입처 보도자료")
print("=" * 70)
for y, (field, pr) in [(2021, ("q8_2_1", "q8_2_2")), (2023, ("q7_2_1", "q7_2_2")), (2025, ("q6_2_1", "q6_2_3"))]:
    # 2025는 1)현장 2)직접취재 3)보도자료 — 2021/2023은 1)직접취재 2)보도자료 (현장 항목 없음)
    a = dfs[y][field].dropna(); b = dfs[y][pr].dropna()
    print(f"{y}: [{field}] 평균 {a.mean():.2f} vs 보도자료[{pr}] 평균 {b.mean():.2f} | 보도자료 활용(4-5) {100*b.isin([4,5]).mean():.1f}%")

print()
print("=" * 70)
print("⑤ 업무 여건 만족·소진 (2025 중심)")
print("=" * 70)
d = dfs[2025]
labels20 = {"q20_1": "보수", "q20_2": "업무 강도", "q20_6": "업무 자율성", "q20_8": "직업 안정성"}
for v, name in labels20.items():
    s = d[v].dropna()
    print(f"2025 {name} 만족: 평균 {s.mean():.2f} | 불만족(1-2) {100*s.isin([1,2]).mean():.1f}%")
for y, v in [(2021, "q30_6"), (2023, "q25_6")]:
    s = dfs[y][v].dropna()
    print(f"{y} 업무 자율성 만족: 평균 {s.mean():.2f} | 불만족(1-2) {100*s.isin([1,2]).mean():.1f}%")
s = d["q21_3"].dropna()
print(f"2025 '업무로 인해 탈진되었다'(4-5 동의): {100*s.isin([4,5]).mean():.1f}% (평균 {s.mean():.2f})")
s = d["q21_4"].dropna()
print(f"2025 '하는 일에 점점 회의가 든다'(4-5 동의): {100*s.isin([4,5]).mean():.1f}%")

print()
print("=" * 70)
print("⑥ 근무시간·사기·이직")
print("=" * 70)
for y, (h, m) in [(2021, ("q56_h", "q56_m")), (2023, ("q51_h", "q51_m")), (2025, ("q47", "q47_n2"))]:
    d = dfs[y]
    hrs = d[h].fillna(0) + d[m].fillna(0) / 60
    hrs = hrs[hrs > 0]
    print(f"{y}: 하루 평균 근무 {hrs.mean():.1f}시간 (n={len(hrs)})")
s = dfs[2025]["q22"].dropna()
print(f"2025 사기 저하됐다(1-2): {100*s.isin([1,2]).mean():.1f}%")
reasons25 = {1: "구조조정", 2: "낮은 임금·복지", 3: "광고·영업 부담", 4: "비전 부재", 5: "자율성 감소",
             6: "성취감 부재", 7: "과중한 업무량·강도", 8: "영향력 축소", 9: "수용자 감소",
             10: "사회적 평가 하락", 11: "과도한 비난", 12: "소송 압박", 13: "기타"}
d = dfs[2025]
sub = d[d["q22"].isin([1, 2])][["q22_1", "q22_1_m2", "q22_1_m3"]]
cnt = {name: 100 * sub.apply(lambda r: (r == k).any(), axis=1).mean() for k, name in reasons25.items()}
top = sorted(cnt.items(), key=lambda x: -x[1])[:5]
print("2025 사기 저하 이유 top5 (저하 응답자 내 언급률):")
for name, v in top:
    print(f"   {name}: {v:.1f}%")
for y, v in [(2021, "q35"), (2023, "q30"), (2025, "q25")]:
    s = dfs[y][v].dropna()
    print(f"{y} 이직 생각해봤다: {100*(s==1).mean():.1f}%")
