# -*- coding: utf-8 -*-
"""
평가셋 채점 파이프라인 (이중 라벨링 → gold → LLM 정확도)
notes/15-labeling-guide.md 참고.

흐름:
  1) labeling_A.csv / labeling_B.csv 를 읽어 코더 간 일치도(단순일치 %, Cohen's κ) 계산
  2) A==B 자동 확정, A!=B 는 out/reconcile_needed.csv 로 뽑아 사람이 최종판정
     - 최종판정은 evalset_150.csv 의 '최종라벨' 칸에 입력(A==B 건은 자동 채움)
  3) gold(150) 완성되면 out/gold_150.csv 저장
  4) classified_evalset_150.csv (LLM 결과)가 있으면 gold와 대조:
     전체 정확도 / 클래스별 정밀도·재현율·F1 / 혼동행렬 / 출처별 정확도
     특히 '감시' P·R·F1 = 보고서 핵심 지표

실행:
  python 04_score.py                (out/ 기준 자동 경로)
라벨이 비어 있어도 동작하며, 다음에 뭘 해야 하는지 안내한다.
표준 라이브러리 + pandas만 사용(κ 직접 구현 — sklearn 불필요).
"""
import os, sys
import pandas as pd
from filters import is_opinion  # 사설·칼럼 등 의견 장르 제외

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

OUT = "out"
LABELS = ["감시", "정보·의제", "해결책"]
ID = "평가ID"

# 사람이 흔히 다르게 쓰는 표기 → 표준 라벨로 정규화
NORMALIZE = {
    "감시": "감시", "감시견": "감시",
    "정보·의제": "정보·의제", "정보.의제": "정보·의제", "정보/의제": "정보·의제",
    "정보의제": "정보·의제", "정보": "정보·의제", "의제": "정보·의제",
    "해결책": "해결책", "해결": "해결책", "대안": "해결책", "해결안": "해결책",
}


def norm(v):
    """라벨 문자열 정규화. 빈칸/미판정('?') → None."""
    if pd.isna(v):
        return None
    s = str(v).strip().rstrip("?").strip()
    if s == "":
        return None
    return NORMALIZE.get(s, s)  # 사전에 없으면 원문 유지(→ 오타로 잡힘)


def load_coder(path, who):
    if not os.path.exists(path):
        print(f"  [없음] {path}")
        return None
    d = pd.read_csv(path)
    if ID not in d.columns or "라벨" not in d.columns:
        print(f"  [형식오류] {path}: '{ID}'·'라벨' 컬럼 필요. 실제: {list(d.columns)}")
        return None
    d = d[[ID, "라벨"]].copy()
    d["라벨"] = d["라벨"].map(norm)
    bad = d[d["라벨"].notna() & ~d["라벨"].isin(LABELS)]
    if len(bad):
        print(f"  ⚠️ [{who}] 표준 3라벨이 아닌 값 {len(bad)}건 — 오타 의심: "
              f"{sorted(bad['라벨'].unique())}")
        print(f"     해당 {ID}: {list(bad[ID])[:10]}{' ...' if len(bad) > 10 else ''}")
    filled = d["라벨"].notna().sum()
    print(f"  [{who}] {os.path.basename(path)}: {filled}/{len(d)}건 라벨됨")
    return d.rename(columns={"라벨": who})


def cohen_kappa(a, b):
    """3-클래스 Cohen's κ (동일 인덱스로 정렬된 두 시리즈, 결측 없음 가정)."""
    n = len(a)
    if n == 0:
        return None
    cats = LABELS
    po = (a.values == b.values).mean()
    pe = 0.0
    for c in cats:
        pe += (a.eq(c).mean()) * (b.eq(c).mean())
    if pe == 1.0:
        return 1.0
    return (po - pe) / (1 - pe)


def kappa_label(k):
    if k is None:
        return ""
    for lo, txt in [(0.81, "거의 완전 일치"), (0.61, "상당한 일치"),
                    (0.41, "중간 일치"), (0.21, "약한 일치"), (-1, "미미/불일치")]:
        if k >= lo:
            return f"({txt})"
    return ""


def prf_table(gold, pred):
    """클래스별 정밀도·재현율·F1 + support. gold/pred: 정렬된 시리즈."""
    rows = []
    for c in LABELS:
        tp = ((pred == c) & (gold == c)).sum()
        fp = ((pred == c) & (gold != c)).sum()
        fn = ((pred != c) & (gold == c)).sum()
        sup = (gold == c).sum()
        p = tp / (tp + fp) if (tp + fp) else 0.0
        r = tp / (tp + fn) if (tp + fn) else 0.0
        f1 = 2 * p * r / (p + r) if (p + r) else 0.0
        rows.append({"클래스": c, "정밀도": round(p, 3), "재현율": round(r, 3),
                     "F1": round(f1, 3), "정답수(support)": int(sup)})
    return pd.DataFrame(rows)


def main():
    print("=" * 68)
    print("STEP 1 — 코더 간 일치도 (이중 라벨링)")
    print("=" * 68)
    A = load_coder(os.path.join(OUT, "labeling_A.csv"), "A")
    B = load_coder(os.path.join(OUT, "labeling_B.csv"), "B")
    if A is None or B is None:
        print("\n두 코더 파일이 모두 필요합니다. labeling_A.csv / labeling_B.csv 를 채워주세요.")
        return

    # 의견 장르(사설·칼럼 등) 제외 — 채점·집계 모수는 보도기사로 한정
    eval_path = os.path.join(OUT, "evalset_150.csv")
    ev = pd.read_csv(eval_path)
    opinion_ids = set(ev[ev["제목"].map(is_opinion)][ID])
    if opinion_ids:
        print(f"\n[의견장르 제외] 사설·칼럼 등 {len(opinion_ids)}건을 채점·집계에서 제외 "
              f"(제목 마커 기준, 라벨링 파일은 그대로 둠)")
        A = A[~A[ID].isin(opinion_ids)]
        B = B[~B[ID].isin(opinion_ids)]
        ev = ev[~ev[ID].isin(opinion_ids)].copy()

    m = A.merge(B, on=ID, how="outer")
    both = m.dropna(subset=["A", "B"])  # 둘 다 라벨된 건만 일치도 계산
    print(f"\n둘 다 라벨된 건: {len(both)}/{len(m)}")
    if len(both) == 0:
        print("아직 겹치는 라벨이 없습니다. 각자 라벨링을 진행한 뒤 다시 실행하세요.")
        return

    agree = (both["A"] == both["B"]).mean()
    k = cohen_kappa(both["A"].reset_index(drop=True), both["B"].reset_index(drop=True))
    print(f"단순 일치율: {agree*100:.1f}%")
    print(f"Cohen's κ : {k:.3f} {kappa_label(k)}")
    print("\nA×B 혼동행렬(행=A, 열=B):")
    print(pd.crosstab(both["A"], both["B"]).reindex(index=LABELS, columns=LABELS, fill_value=0).to_string())

    disagree = both[both["A"] != both["B"]]
    print(f"\n불일치 {len(disagree)}건 → 상의해서 최종판정 필요.")

    print("\n" + "=" * 68)
    print("STEP 2 — gold(최종 정답) 구성")
    print("=" * 68)
    # ev 는 STEP 1 에서 로드·의견장르 제외 완료 (보도기사만)
    ev["최종라벨_n"] = ev["최종라벨"].map(norm) if "최종라벨" in ev.columns else None

    # A==B 자동 확정
    gold = {}
    for _, row in both.iterrows():
        if row["A"] == row["B"]:
            gold[row[ID]] = row["A"]
    # 불일치·미완: evalset_150 의 '최종라벨'에서 채움
    manual = {}
    if "최종라벨" in ev.columns:
        for _, r in ev.iterrows():
            v = norm(r["최종라벨"])
            if v in LABELS:
                manual[r[ID]] = v
    # 최종 우선순위: 사람이 최종라벨에 명시한 값 > A==B 자동값
    resolved = {**gold, **manual}

    all_ids = list(ev[ID])
    unresolved = [i for i in all_ids if i not in resolved]
    # 불일치인데 아직 최종라벨 없는 건을 따로 파일로
    need = disagree[~disagree[ID].isin(manual)]
    if len(need):
        rec = ev[ev[ID].isin(need[ID])][[ID, "제목"]].merge(
            need[[ID, "A", "B"]], on=ID)
        rec["최종라벨"] = ""
        rec_path = os.path.join(OUT, "reconcile_needed.csv")
        rec.to_csv(rec_path, index=False, encoding="utf-8-sig")
        print(f"불일치 {len(need)}건 → {rec_path} 저장. "
              f"두 사람이 상의해 evalset_150.csv의 '최종라벨' 칸을 채운 뒤 재실행하세요.")

    print(f"확정된 gold: {len(resolved)}/{len(all_ids)}  (미확정 {len(unresolved)})")
    if unresolved:
        # 미확정 사유 분해
        both_ids = set(both[ID])
        not_both = [i for i in unresolved if i not in both_ids]
        if not_both:
            print(f"  · 아직 한쪽 이상 라벨 안 된 건: {len(not_both)}")
        if len(need):
            print(f"  · 불일치 미조정 건: {len(need)}")

    if len(resolved) == len(all_ids):
        gdf = pd.DataFrame({ID: all_ids})
        gdf["gold"] = gdf[ID].map(resolved)
        gdf.to_csv(os.path.join(OUT, "gold_150.csv"), index=False, encoding="utf-8-sig")
        print(f"✅ gold 150건 완성 → {os.path.join(OUT, 'gold_150.csv')}")

    print("\n" + "=" * 68)
    print("STEP 3 — LLM 정확도 채점 (gold vs Gemini 분류)")
    print("=" * 68)
    cls_path = os.path.join(OUT, "classified_evalset_150.csv")
    if not os.path.exists(cls_path):
        print(f"[없음] {cls_path}")
        print("→ 먼저 평가셋을 LLM으로 분류하세요:  python 02_classify.py out/evalset_150.csv")
        return
    if len(resolved) < len(all_ids):
        print("gold가 아직 완성되지 않아 채점은 확정된 건만 대상으로 합니다.")

    cls = pd.read_csv(cls_path)
    cls["LLM"] = cls["LLM분류"].map(norm)
    scored = cls[cls[ID].isin(resolved)].copy()
    scored["gold"] = scored[ID].map(resolved)
    scored = scored.dropna(subset=["LLM", "gold"])
    n = len(scored)
    if n == 0:
        print("채점 가능한(gold와 LLM 둘 다 있는) 건이 없습니다.")
        return

    acc = (scored["LLM"] == scored["gold"]).mean()
    print(f"채점 대상: {n}건 | 전체 정확도: {acc*100:.1f}%\n")
    print("클래스별 성능 (gold 기준):")
    print(prf_table(scored["gold"].reset_index(drop=True),
                    scored["LLM"].reset_index(drop=True)).to_string(index=False))
    print("\n혼동행렬 (행=gold 정답, 열=LLM 예측):")
    print(pd.crosstab(scored["gold"], scored["LLM"]).reindex(
        index=LABELS, columns=LABELS, fill_value=0).to_string())

    # 출처별 정확도 (감시후보/랜덤 등에서 얼마나 맞히나)
    if "출처" in ev.columns:
        src = ev[[ID, "출처"]]
        s2 = scored.merge(src, on=ID)
        print("\n출처별 정확도:")
        for name, g in s2.groupby("출처"):
            a = (g["LLM"] == g["gold"]).mean()
            print(f"  {name:9s} {a*100:5.1f}%  (n={len(g)})")

    # 보고서 핵심: '감시' 재현율 = 실제 감시 기사를 감시라고 맞힌 비율
    watch = prf_table(scored["gold"].reset_index(drop=True),
                      scored["LLM"].reset_index(drop=True))
    w = watch[watch["클래스"] == "감시"].iloc[0]
    print(f"\n★ 보고서 핵심 지표 — '감시' 정밀도 {w['정밀도']}, 재현율 {w['재현율']}, F1 {w['F1']}")
    print("  (재현율=실제 감시를 놓치지 않는 정도 / 정밀도=감시라 한 것이 진짜 감시인 정도)")

    out_report = os.path.join(OUT, "score_report.txt")
    with open(out_report, "w", encoding="utf-8") as f:
        f.write(f"채점 {n}건 | 정확도 {acc*100:.1f}% | 코더 κ {k:.3f}\n\n")
        f.write(prf_table(scored["gold"].reset_index(drop=True),
                          scored["LLM"].reset_index(drop=True)).to_string(index=False))
    print(f"\n요약 저장 → {out_report}")


if __name__ == "__main__":
    main()
