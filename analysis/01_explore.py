"""W2-1: 2025 언론인/수용자 .sav 메타데이터 탐색 — 변수명·가중치 확인."""
import pyreadstat, re

FILES = {
    "journalist_2025": "data/raw/journalist_2025/[로데이터] 2025 언론인 조사 원본 데이터.SAV",
    "audience_2025":   "data/raw/audience_2025/3. 2025 언론수용자 조사_최종데이터.SAV",
}

def show(tag, path):
    df, meta = pyreadstat.read_sav(path, metadataonly=True)
    print(f"\n{'='*70}\n{tag}  (n_rows={meta.number_rows}, n_cols={meta.number_columns})\n{'='*70}")
    cols = meta.column_names
    labels = dict(zip(meta.column_names, meta.column_labels))

    # 가중치 후보
    wt = [c for c in cols if re.search(r"(weight|wt|가중|wgt)", c, re.I)
          or re.search(r"가중", str(labels.get(c, "")))]
    print(f"[가중치 후보] {wt}")
    for c in wt:
        print(f"    {c}: {labels.get(c)}")

    # 관심 변수 패턴(언론인 q2/q3/q1, 수용자 Q77/Q85/Q86/Q78)
    pats = r"^(q2_|q3_|q1_|Q2_|Q3_|Q1_|Q77_|Q85_|Q86_|Q78_|Q91_|Q83_)"
    hit = [c for c in cols if re.match(pats, c)]
    print(f"[관심 변수 {len(hit)}개] {hit}")
    for c in hit[:40]:
        print(f"    {c}: {labels.get(c)}")

for tag, path in FILES.items():
    show(tag, path)
