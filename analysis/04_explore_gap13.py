"""GAP① 5속성 / GAP③ 문제점 — 언론인2025·수용자2025 항목 확인."""
import pyreadstat, re

j, jm = pyreadstat.read_sav("data/raw/journalist_2025/[로데이터] 2025 언론인 조사 원본 데이터.SAV", metadataonly=True)
a, am = pyreadstat.read_sav("data/raw/audience_2025/3. 2025 언론수용자 조사_최종데이터.SAV", metadataonly=True)
jl = dict(zip(jm.column_names, jm.column_labels))
al = dict(zip(am.column_names, am.column_labels))

print("### 언론인2025 — q1 (5속성+신뢰)")
for c in jm.column_names:
    if re.match(r"^q1_\d+$", c): print(f"  {c}: {jl[c]}")

print("\n### 언론인2025 — 문제점/심각성 배터리 탐색 (라벨에 오보·낚시·어뷰징·편파·가짜·심각)")
for c in jm.column_names:
    lab = str(jl.get(c, ""))
    if re.search(r"오보|낚시|어뷰징|편파|가짜|허위·조작|찌라시|받아쓰기|심각|문제점", lab):
        print(f"  {c}: {lab}")

print("\n### 수용자2025 — Q85 (5속성)")
for c in am.column_names:
    if re.match(r"^Q85_\d+$", c): print(f"  {c}: {al[c]}")

print("\n### 수용자2025 — Q91 (문제점 8종)")
for c in am.column_names:
    if re.match(r"^Q91_\d+$", c): print(f"  {c}: {al[c]}")
