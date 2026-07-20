# -*- coding: utf-8 -*-
"""
LLM 분류기(Gemini) 정확도 평가 — gold(out/adjudication_draft.csv 최종라벨) vs Gemini 재분류.
기획안 v2 §3.4(결과③ 검증 절차)·§6.4(신뢰성 검증)에 들어갈 정확도·불일치 항목을 산출한다.

배경: 골든셋은 조정관이 라벨_A·라벨_B를 대조해 최종라벨까지 확정한 병합본(out/adjudication_draft.csv).
  '최종라벨'이 사설/서평(제외 대상)이면 평가 모수에서 뺀다(3분류 판정 대상 아님).
  (실측: 150건 중 사설 7 + 서평 1 = 8건 제외 → 유효 142건. 감시 12 / 정보·의제 128 / 해결책 2)

모델: gemini-3.1-flash-lite (gemini-2.5-flash는 이 키에서 404 — 2026-07-15 사용자 확인).
프롬프트: prompts.py 공용 모듈(02_classify.py·서비스와 동일 SSOT). 단일 호출로 3역할 점수 +
  감시 체크리스트 5항목(각 0~20, 합=감시점수) + 근거 + 개선제안 3개를 받는다(기획안 v2 §6).

라벨 도출 두 갈래(작업현황_기획안v2.md: 조작적 정의는 팀 미결정 → 여기서 데이터로 뒷받침):
  (1) 3역할 점수 argmax → 3분류 라벨(주지표, threshold 없음). gold와 대조해 정확도·혼동행렬.
  (2) 감시 점수(체크리스트 합)에 임계값 t 스윕 → "감시 보도 %"용 조작적 정의 후보.
      각 t에서 감시 vs 비감시 정밀도·재현율·F1을 출력해 팀이 t를 고르게 한다.

실행:
  python 05_llm_eval.py
  - out/classified_adjudication_eval_v2.csv : LLM 원점수(이어쓰기 저장, 중단 후 재실행 시 이어서 함)
  - out/llm_eval_result.csv   : 행 단위 상세(gold/LLM/정오/확신도/역할점수/체크리스트/감시점수/근거/개선제안)
  - out/llm_eval_summary.txt  : 정확도·혼동행렬·감시 이분 P/R/F1·임계값 스윕·확신도별·오분류·불일치 항목
"""
import os, sys, json, time, shutil
import pandas as pd
from prompts import (LABELS, ROLE_AXES, CHECKLIST_ITEMS,
                     build_prompt, parse_response, derive_label, derive_confidence)

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

try:
    from google import genai
    from google.genai import types
except ImportError:
    os.system(f"{sys.executable} -m pip install google-genai -q")
    from google import genai
    from google.genai import types

OUT = "out"
ID = "평가ID"
EXCLUDE_VALUES = {"사설", "서평"}

# 조정 완료된 병합본의 원본 위치(로컬 경로). 없으면 out/adjudication_draft.csv 를 직접 두면 된다.
GOLD_SRC = os.environ.get("GOLD_SRC", "")
GOLD_PATH = os.path.join(OUT, "adjudication_draft.csv")
CLASSIFIED_PATH = os.path.join(OUT, "classified_adjudication_eval_v2.csv")
RESULT_PATH = os.path.join(OUT, "llm_eval_result.csv")
SUMMARY_PATH = os.path.join(OUT, "llm_eval_summary.txt")

MODEL = "gemini-3.1-flash-lite"
SECONDS_PER_REQ = 7
BATCH_SAVE_EVERY = 20
THRESHOLDS = [50, 55, 60, 65, 70, 75, 80]  # 감시 점수 조작적 정의 후보

# LLM 원점수 CSV 컬럼 순서
SCORE_COLS = (["역할_감시", "역할_정보·의제", "역할_해결책", "감시점수"]
              + [f"체크_{it}" for it in CHECKLIST_ITEMS])

GEN_CONFIG = types.GenerateContentConfig(
    response_mime_type="application/json",
    max_output_tokens=700,  # 체크리스트+개선제안 3개까지 담기게 넉넉히
    temperature=0,
)


def classify_one(client, row):
    msg = build_prompt(row["언론사"], row["제목"], row["본문"])
    r = client.models.generate_content(model=MODEL, contents=msg, config=GEN_CONFIG)
    text = (r.text or "").strip()
    try:
        parsed = parse_response(json.loads(text))
        return parsed, None
    except Exception:
        return None, text[:200]


def load_gold():
    if not os.path.exists(GOLD_PATH):
        if not os.path.exists(GOLD_SRC):
            print(f"[없음] gold 소스 파일이 없습니다: {GOLD_SRC}")
            sys.exit(1)
        shutil.copy(GOLD_SRC, GOLD_PATH)
        print(f"[복사] {GOLD_SRC}\n     → {GOLD_PATH}")
    d = pd.read_csv(GOLD_PATH)
    need = {ID, "최종라벨", "언론사", "제목", "본문", "URL"}
    missing = need - set(d.columns)
    if missing:
        print(f"[형식오류] {GOLD_PATH}: 컬럼 {missing} 없음. 실제: {list(d.columns)}")
        sys.exit(1)
    return d


def norm_gold(v):
    if pd.isna(v):
        return None
    s = str(v).strip()
    if s in EXCLUDE_VALUES or s == "":
        return None
    return s if s in LABELS else None


def classify_all(df):
    done = {}
    if os.path.exists(CLASSIFIED_PATH):
        prev = pd.read_csv(CLASSIFIED_PATH)
        for _, r in prev.iterrows():
            done[r[ID]] = r.to_dict()
        print(f"[재개] 기존 {len(done)}건 건너뜀")
    results = list(done.values())

    client = genai.Client()
    todo = df[~df[ID].isin(done.keys())]
    print(f"[분류] 대상 {len(todo)}건 / 모델 {MODEL} / 요청 간격 {SECONDS_PER_REQ}초 "
          f"(예상 약 {len(todo) * SECONDS_PER_REQ // 60}분)")

    for i, (_, row) in enumerate(todo.iterrows(), 1):
        try:
            parsed, err = classify_one(client, row)
        except Exception as e:
            emsg = str(e)
            if "429" in emsg or "RESOURCE_EXHAUSTED" in emsg:
                print(f"  요청 한도 도달({row[ID]}) — 60초 후 재시도")
                time.sleep(60)
            else:
                print(f"  오류({row[ID]}): {emsg[:80]} — 10초 후 재시도")
                time.sleep(10)
            try:
                parsed, err = classify_one(client, row)
            except Exception as e2:
                emsg2 = str(e2)
                if "429" in emsg2 or "RESOURCE_EXHAUSTED" in emsg2:
                    pd.DataFrame(results).to_csv(CLASSIFIED_PATH, index=False, encoding="utf-8-sig")
                    print(f"[중단] 일일 한도 소진 추정. {len(results)}건 저장됨 — 나중에 재실행하면 이어서 함.")
                    sys.exit(0)
                parsed, err = None, emsg2[:120]

        rec = {ID: row[ID], "LLM오류": ""}
        if parsed is None:
            rec["LLM오류"] = "파싱실패"
            for c in SCORE_COLS:
                rec[c] = None
            rec["reason"] = err or ""
            rec["improvements"] = ""
        else:
            rec["역할_감시"] = parsed["역할_감시"]
            rec["역할_정보·의제"] = parsed["역할_정보·의제"]
            rec["역할_해결책"] = parsed["역할_해결책"]
            rec["감시점수"] = parsed["감시점수"]
            for it in CHECKLIST_ITEMS:
                rec[f"체크_{it}"] = parsed[f"체크_{it}"]
            rec["reason"] = parsed["reason"]
            rec["improvements"] = " | ".join(map(str, parsed["improvements"]))
        results.append(rec)
        if i % BATCH_SAVE_EVERY == 0:
            pd.DataFrame(results).to_csv(CLASSIFIED_PATH, index=False, encoding="utf-8-sig")
            print(f"  ...{i}/{len(todo)} 저장")
        time.sleep(SECONDS_PER_REQ)

    pd.DataFrame(results).to_csv(CLASSIFIED_PATH, index=False, encoding="utf-8-sig")
    print(f"[완료] LLM 점수 → {CLASSIFIED_PATH}")
    return pd.read_csv(CLASSIFIED_PATH)


def prf(gold_pos, pred_pos):
    tp = int((pred_pos & gold_pos).sum())
    fp = int((pred_pos & ~gold_pos).sum())
    fn = int((~pred_pos & gold_pos).sum())
    p = tp / (tp + fp) if (tp + fp) else 0.0
    r = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * p * r / (p + r) if (p + r) else 0.0
    return p, r, f1, tp, fp, fn


def main():
    gold_raw = load_gold()
    gold_raw["gold"] = gold_raw["최종라벨"].map(norm_gold)
    excluded = gold_raw[gold_raw["gold"].isna()]
    valid = gold_raw[gold_raw["gold"].notna()].copy()
    print(f"[gold] 전체 {len(gold_raw)}건 — 제외(사설/서평/미기입 등) {len(excluded)}건 → 유효 {len(valid)}건")
    print(valid["gold"].value_counts().reindex(LABELS, fill_value=0).to_string())

    cls = classify_all(valid)
    parse_fail = cls[cls["감시점수"].isna()]
    if len(parse_fail):
        print(f"\n⚠️ LLM 파싱실패 {len(parse_fail)}건 — 채점 제외: {list(parse_fail[ID])}")
    cls_ok = cls.dropna(subset=["감시점수"]).copy()

    def _mk_parsed(r):
        return {"역할_감시": r["역할_감시"], "역할_정보·의제": r["역할_정보·의제"],
                "역할_해결책": r["역할_해결책"], "감시점수": r["감시점수"]}
    cls_ok["LLM"] = cls_ok.apply(lambda r: derive_label(_mk_parsed(r)), axis=1)
    cls_ok["LLM확신도"] = cls_ok.apply(lambda r: derive_confidence(_mk_parsed(r)), axis=1)

    keep = [ID, "LLM", "LLM확신도"] + SCORE_COLS + ["reason", "improvements"]
    m = valid.merge(cls_ok[keep], on=ID, how="left")
    scored = m[m["LLM"].notna()].copy()
    scored["correct"] = scored["gold"] == scored["LLM"]
    n = len(scored)

    lines = []

    def out(s=""):
        print(s)
        lines.append(s)

    out("=" * 70)
    out(f"STEP 1 — 3역할 argmax 라벨 vs gold  (주지표, n={n})")
    out("=" * 70)
    acc = scored["correct"].mean()
    out(f"전체 정확도: {acc*100:.1f}%  ({int(scored['correct'].sum())}/{n})")
    out("\n혼동행렬 (행=gold, 열=LLM, 라벨=3역할 점수 argmax):")
    out(pd.crosstab(scored["gold"], scored["LLM"]).reindex(
        index=LABELS, columns=LABELS, fill_value=0).to_string())

    out("\n" + "=" * 70)
    out("STEP 2 — 감시 vs 비감시 이분 지표 (해결책 표본이 적어 이게 주지표)")
    out("=" * 70)
    g_w = scored["gold"] == "감시"
    p, r, f1, tp, fp, fn = prf(g_w, scored["LLM"] == "감시")
    out(f"[argmax 기준] 정밀도 {p:.3f} · 재현율 {r:.3f} · F1 {f1:.3f}  (TP={tp} FP={fp} FN={fn})")
    out(f"감시 점수(0~100) 평균: gold=감시 {scored[g_w]['감시점수'].mean():.1f}점 "
        f"vs gold≠감시 {scored[~g_w]['감시점수'].mean():.1f}점")

    out("\n" + "=" * 70)
    out("STEP 3 — 감시 점수 임계값 스윕 (조작적 정의 t 결정용 — 감시점수 ≥ t 이면 감시)")
    out("=" * 70)
    out("  t   정밀도  재현율   F1    감시예측수")
    best = None
    for t in THRESHOLDS:
        pred_w = scored["감시점수"] >= t
        p, r, f1, tp, fp, fn = prf(g_w, pred_w)
        mark = ""
        if best is None or f1 > best[1]:
            best = (t, f1)
            mark = ""
        out(f" {t:>3}  {p:5.3f}  {r:5.3f}  {f1:5.3f}   {int(pred_w.sum())}")
    out(f"→ F1 최대 임계값: t={best[0]} (F1={best[1]:.3f}). 팀이 최종 조작적 정의로 확정할 것.")

    out("\n" + "=" * 70)
    out("STEP 4 — 확신도별 정확도 (1·2위 역할 점수 격차 기반)")
    out("=" * 70)
    for lvl in ["높음", "중간", "낮음"]:
        gsub = scored[scored["LLM확신도"] == lvl]
        if len(gsub):
            out(f"  {lvl}: 정확도 {gsub['correct'].mean()*100:.1f}%  (n={len(gsub)})")

    out("\n" + "=" * 70)
    out("STEP 5 — 불일치 항목 분석 (본문 6.4절 '불일치는 주로 __항목에서 발생')")
    out("=" * 70)
    wrong = scored[~scored["correct"]]
    if len(wrong):
        pair = wrong.apply(lambda r: f"gold={r['gold']}→LLM={r['LLM']}", axis=1)
        out("오분류 방향별 건수:")
        out(pair.value_counts().to_string())
        out("\n체크리스트 항목별 평균점수 — 오분류(감시↔정보·의제) 기사에서 어느 항목이 흔들리나:")
        conf = wrong[wrong["gold"].isin(["감시", "정보·의제"]) & wrong["LLM"].isin(["감시", "정보·의제"])]
        if len(conf):
            for it in CHECKLIST_ITEMS:
                out(f"  {it}: {conf[f'체크_{it}'].mean():.1f}/20")

    out("\n" + "=" * 70)
    out("STEP 6 — 오분류 사례 목록")
    out("=" * 70)
    w2 = scored[~scored["correct"]][[ID, "gold", "LLM", "LLM확신도", "감시점수", "제목"]]
    out(f"오분류 {len(w2)}건")
    if len(w2):
        out(w2.to_string(index=False))

    with open(SUMMARY_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(f"\n요약 저장 → {SUMMARY_PATH}")

    result = scored[[ID, "언론사", "제목", "gold", "LLM", "correct", "LLM확신도"]
                    + SCORE_COLS + ["reason", "improvements", "URL"]] \
        .rename(columns={"gold": "gold라벨", "LLM": "LLM라벨", "correct": "정답여부"})
    result.to_csv(RESULT_PATH, index=False, encoding="utf-8-sig")
    print(f"행 단위 결과 저장 → {RESULT_PATH} ({len(result)}건, 역할점수+체크리스트+개선제안 포함)")


if __name__ == "__main__":
    main()
