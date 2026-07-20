# -*- coding: utf-8 -*-
"""
결과② (§3.3) 근거 집계 — 언론인 생성형 AI 활용 실태 (2023 vs 2025, 비가중)

⚠️ 2023년 원자료는 변수 라벨이 전부 비어 있어(360개 중 0개) 코드북 PDF 대조로 매핑함.
   (보고서 '연구의 한계' 4번에 명시된 방식)

문항 매핑 (코드북 확인 완료)
  2023 문43 [q43_1~q43_9]  활용 중인 생성 AI 도구 모두 선택 — **⑨=활용하지 않고 있다**
       → 활용률 = 1 − (q43_9 선택 비율)
  2023 문43-1 [q43_1_1~3]  활용 분야 우선순위 3개 (활용자만)
  2023 문46 [q46]          소속사 AI 가이드라인 보유 (①보유 ②미보유 ③모름)
  2025 문38 [q38]          생성형 AI 활용 여부 (①예 ②아니오)
  2025 문38-1 [q38_1~_m10] 활용 분야 복수응답
  2025 문40 [q40]          AI 가이드라인 인지 여부

⚠️ 2023·2025 문항 워딩이 다르다:
   - 활용 여부: 2023은 '도구를 고르시오(⑨=미활용)', 2025는 '활용합니까(예/아니오)' → 직접 비교 시 주의
   - 가이드라인: 2023은 '소속사 보유', 2025는 '인지' → **다른 개념. 시계열로 묶지 말 것**
"""
import os, sys
import pandas as pd
import pyreadstat

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

_HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(os.path.dirname(_HERE), "data", "raw")
P23 = RAW + r"\journalist_2023\[로데이터] 2023 언론인 조사 원본 데이터(SAV).SAV"
P25 = RAW + r"\journalist_2025\[로데이터] 2025 언론인 조사 원본 데이터.SAV"

AREA23 = {1: "텍스트·이미지 생성", 2: "자료 수집·분류", 3: "녹취·번역·교정",
          4: "아이템 구상", 5: "팩트체킹", 6: "독자분석·개인화", 7: "기타"}

d23, _ = pyreadstat.read_sav(P23)
d23.columns = [c.lower() for c in d23.columns]
d25, m25 = pyreadstat.read_sav(P25)
d25.columns = [c.lower() for c in d25.columns]

out = []
def p(s=""):
    print(s); out.append(s)

p("=" * 68)
p("① 생성형 AI 활용률")
p("=" * 68)
n23 = len(d23)
non_user23 = d23["q43_9"].notna().sum()          # ⑨ 활용하지 않고 있다
rate23 = 100 * (n23 - non_user23) / n23
p(f"2023 (문43): 전체 {n23:,}명 중 미활용 {non_user23:,}명 → 활용률 **{rate23:.1f}%**")

n25 = d25["q38"].notna().sum()
user25 = (d25["q38"] == 1).sum()
rate25 = 100 * user25 / n25
p(f"2025 (문38): 전체 {n25:,}명 중 활용 {user25:,}명 → 활용률 **{rate25:.1f}%**")
p(f"\n→ 2023 {rate23:.1f}% → 2025 {rate25:.1f}%  (+{rate25-rate23:.1f}%p)")
p("⚠️ 문항 워딩이 달라(도구 선택형 vs 예/아니오) 엄밀한 동일 지표 비교는 아님. 경향으로 해석할 것.")

p("\n" + "=" * 68)
p("② 활용 분야 — '정보 전달성 업무에 집중'되는지")
p("=" * 68)
p("2023 (문43-1, 활용자 우선순위 1~3위 언급률):")
sub = d23[["q43_1_1", "q43_1_2", "q43_1_3"]]
base = sub.notna().any(axis=1).sum()
for k, name in AREA23.items():
    cnt = sub.apply(lambda r: (r == k).any(), axis=1).sum()
    p(f"   {name:16} {100*cnt/base:5.1f}%")
p(f"   (활용자 n={base:,})")

p("\n2025 (문38-1, 복수응답 언급률):")
cols25 = ["q38_1"] + [f"q38_1_m{i}" for i in range(2, 11)]
cols25 = [c for c in cols25 if c in d25.columns]
sub25 = d25[cols25]
base25 = sub25.notna().any(axis=1).sum()
lab25 = m25.variable_value_labels.get("q38_1", {})
rows = []
for k, name in sorted(lab25.items()):
    cnt = sub25.apply(lambda r: (r == k).any(), axis=1).sum()
    rows.append((100 * cnt / base25, str(name)))
for pct, name in sorted(rows, reverse=True):
    p(f"   {name:34} {pct:5.1f}%")
p(f"   (활용자 n={base25:,})")

p("\n" + "=" * 68)
p("③ AI 가이드라인")
p("=" * 68)
g23 = d23["q46"].dropna()
p(f"2023 (문46, 소속사 보유 여부): 보유 {100*(g23==1).mean():.1f}% / "
  f"미보유 {100*(g23==2).mean():.1f}% / 모름 {100*(g23==3).mean():.1f}%")
g25 = d25["q40"].dropna()
vl = m25.variable_value_labels.get("q40", {})
p(f"2025 (문40, 가이드라인 인지 여부) — 값라벨 {vl}")
for k, v in sorted(vl.items()):
    p(f"   {v}: {100*(g25==k).mean():.1f}%")
p("\n⚠️ 2023은 '소속사 보유', 2025는 '인지'로 **묻는 개념이 다르다.**")
p("   보고서 표 5(P2)의 '2023 __% → 2025 __%, 가이드라인 보유 __%'를 하나의 시계열처럼 쓰면 안 된다.")
p("   → 2023 보유율만 단일 수치로 쓰거나, 두 해를 각각 다른 지표로 명시해 제시할 것.")

with open("out_ai_usage.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(out) + "\n")
print("\n저장 → analysis/out_ai_usage.txt")
