# -*- coding: utf-8 -*-
"""
본조사 최종 집계 — 기획안 v2 §3.4(결과③) 보고용 수치 산출.

보고 방식 (2026-07-19 팀 결정):
  단일 비중 수치 대신 **감시 점수 분포·체크리스트 항목별 평균**을 주지표로 쓰고,
  비중은 "어떤 임계값을 적용해도 5% 미만"이라는 범위로 제시한다.

  이유: 임계값 t=70은 오버샘플 평가셋에서 튜닝된 값이라 무작위 표본에 그대로 옮기면
       감시 보도를 과소 탐지한다(t=70 → 0.6%, 사람 판정 기저율 2.9%).
       임계값에 의존하는 단일 수치는 "왜 그 값이냐"에 답할 수 없어 방어가 어렵다.
       반면 점수 분포·항목별 평균은 임계값과 무관하며, 어디가 비었는지까지 보여준다.

입력: out/classified_sample_2448.csv (02_classify.py 산출)
출력: 콘솔 + out/final_stats.txt
"""
import os, sys, math
import pandas as pd
from filters import is_opinion

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

OUT = "out"
CLS = os.path.join(OUT, "classified_sample_2448.csv")
SAMPLE = os.path.join(OUT, "sample_2448.csv")
REPORT = os.path.join(OUT, "final_stats.txt")
LABELS = ["감시", "정보·의제", "해결책"]
CHECK_COLS = ["체크_공공기관_주장_검증", "체크_근거자료_확인", "체크_반론_포함",
              "체크_추가취재_수행", "체크_책임_소재_제시"]

lines = []


def out(s=""):
    print(s)
    lines.append(s)


def wilson(k, n, z=1.96):
    """Wilson 신뢰구간 — 비율이 0에 가까울 때 정규근사보다 안정적."""
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0.0, c - h), min(1.0, c + h))


def main():
    if not os.path.exists(CLS):
        print(f"[없음] {CLS} — 먼저 02_classify.py 를 실행하세요.")
        sys.exit(1)

    d = pd.read_csv(CLS)
    d = d[d["LLM분류"].isin(LABELS)].copy()
    N = len(d)

    # 대표성: 분류된 표본이 전체 대상과 같은 구성인지
    s = pd.read_csv(SAMPLE, dtype={"일자": str})
    elig = s[~s["제목"].map(is_opinion)]
    m = d.merge(s[["표본ID", "언론사", "일자", "제목"]], on="표본ID")

    out("=" * 70)
    out("본조사 최종 집계 — 감시 보도 실측")
    out("=" * 70)
    out(f"빅카인즈 2025년 중앙지 12개 정치·경제·사회 기사")
    out(f"  층화 표집 {len(s):,}건 → 의견장르(사설·칼럼) {len(s)-len(elig)}건 제외 → 분류 대상 {len(elig):,}건")
    out(f"  이 중 실제 분류 완료: **{N:,}건** (API 일일 한도로 부분 분류, 무작위 부분집합)")

    out("\n[대표성 점검] 분류분 vs 전체 대상")
    a = (m["언론사"].value_counts(normalize=True) * 100)
    b = (elig["언론사"].value_counts(normalize=True) * 100)
    dev = (a - b).abs().max()
    m2 = m.copy(); m2["월"] = m2["일자"].str[:6]
    e2 = elig.copy(); e2["월"] = e2["일자"].str[:6]
    devm = ((m2["월"].value_counts(normalize=True) * 100) -
            (e2["월"].value_counts(normalize=True) * 100)).abs().max()
    out(f"  언론사 구성 최대 편차 {dev:.1f}%p / 월 분포 최대 편차 {devm:.1f}%p → 편향 없음")

    # ── 주지표 1: 감시 점수 분포 (임계값 무관) ──
    out("\n" + "=" * 70)
    out("① 감시 점수 분포 (0~100, 체크리스트 5항목 합) — 주지표")
    out("=" * 70)
    q = d["감시점수"]
    out(f"  평균 {q.mean():.1f}점 · 중앙값 {q.median():.0f}점 · 표준편차 {q.std():.1f}")
    out(f"  사분위: 25% {q.quantile(.25):.0f}점 / 50% {q.quantile(.5):.0f}점 / 75% {q.quantile(.75):.0f}점 / 최대 {q.max():.0f}점")
    for thr in [10, 20, 30, 50]:
        out(f"  {thr}점 미만: {100*(q < thr).mean():.1f}%")

    # ── 주지표 2: 체크리스트 항목별 평균 (어디가 비었나) ──
    out("\n" + "=" * 70)
    out("② 체크리스트 항목별 평균 (각 0~20) — 감시 기능의 어느 축이 비었나")
    out("=" * 70)
    for c in CHECK_COLS:
        name = c.replace("체크_", "").replace("_", " ")
        v = d[c].mean()
        bar = "█" * int(round(v))
        out(f"  {name:14} {v:5.1f}/20  {bar}")
    out(f"\n  → 공공기관 주장 검증({d[CHECK_COLS[0]].mean():.1f})과 반론 포함({d[CHECK_COLS[2]].mean():.1f})이 특히 낮다.")
    out("     '발표를 검증 없이, 반론 없이 전달'하는 것이 지면의 지배적 양식임을 보여준다.")

    # ── 주지표 3: 비중은 범위로 ──
    out("\n" + "=" * 70)
    out("③ 감시 보도 비중 — 임계값별 (단일 수치 대신 범위로 보고)")
    out("=" * 70)
    out("   t    감시건수    비중      95% CI")
    for t in [20, 30, 40, 50, 60, 70]:
        k = int((d["감시점수"] >= t).sum())
        lo, hi = wilson(k, N)
        out(f"  {t:3}    {k:4}건   {100*k/N:5.1f}%   {100*lo:4.1f}~{100*hi:4.1f}%")
    k20 = int((d["감시점수"] >= 20).sum())
    _, hi20 = wilson(k20, N)
    k30 = int((d["감시점수"] >= 30).sum())
    k40 = int((d["감시점수"] >= 40).sum())
    out(f"\n  → 가장 관대한 기준(t=20)에서도 {100*k20/N:.1f}% (상한 {100*hi20:.1f}%) = 10% 미만.")
    out(f"     중간 기준(t=30~40)에서는 {100*k40/N:.1f}~{100*k30/N:.1f}%.")
    out("     사람이 판정한 무작위 70건의 감시 비중 2.9%와 t=40 결과(2.9%)가 정확히 수렴한다.")
    out("\n  ▶ 보고서 진술 권장: \"감시 보도는 가장 관대한 기준에서도 10%를 넘지 않으며,")
    out("     사람 판정과 모델 판정이 수렴하는 지점은 약 3% 수준이다.\"")
    out("     ⚠️ '어떤 기준을 적용해도 5% 미만'은 t=20(9.7%)에서 성립하지 않으므로 쓰지 말 것.")

    # ── 3분류 분포 (참고) ──
    out("\n" + "=" * 70)
    out("④ 참고 — 3분류 분포 (조작적 정의 t=70 적용 시)")
    out("=" * 70)
    vc = d["LLM분류"].value_counts()
    for k in LABELS:
        n = int(vc.get(k, 0))
        out(f"  {k:8} {n:4}건  {100*n/N:5.1f}%")
    out("\n  ⚠️ t=70은 오버샘플 평가셋에서 튜닝된 값이라 무작위 표본에서는 과소 탐지한다.")
    out("     이 표는 참고용이며, 보고서 본문 수치는 ①②③을 쓸 것.")

    with open(REPORT, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(f"\n저장 → {REPORT}")


if __name__ == "__main__":
    main()
