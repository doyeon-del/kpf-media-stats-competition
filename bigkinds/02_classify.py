# -*- coding: utf-8 -*-
"""
LLM 3묶음 분류기 v3 (Google Gemini API — 무료 등급)
입력: out/sample_XXXX.csv (01번 스크립트 산출물), 또는 인자로 CSV 경로 지정
출력: out/classified_<입력이름>.csv (표본ID, 6축 점수, 도출라벨, 근거)

⚠️ 프롬프트: prompts.py 공용 모듈 사용(05_llm_eval.py와 동일 — 2026-07-15 정확도 평가에서
   검증된 "기자가 없었어도 나왔을까" 원칙 + 6축 점수 스키마로 통일). 단일 라벨이 아니라
   감시/정보/의제/해결책/공정성/근거성 각 0~100점을 받고, 그 안에서 3분류 라벨을 도출한다
   (코파일럿 레이더 차트 스펙과 동일 — notes/11-plan-tickets.md T2.2).

⚠️ 실행 전 확인:
  1) https://aistudio.google.com/apikey 에서 무료 API 키 발급 (카드 등록 불필요)
  2) GEMINI_API_KEY 환경변수 설정

⚠️ 무료 등급 한도 (변동 가능 — aistudio 요금 페이지에서 확인):
  - 분당 요청 제한이 있어 요청 사이 SECONDS_PER_REQ초 대기함
  - 일일 요청 한도가 있어 2,448건 전체는 2~3일에 나눠 돌려야 할 수 있음
    (중단 후 재실행하면 이어서 함 — 같은 명령 다시 실행하면 됨)
  - 일정이 밀리면 표본을 960건(셀당 8건)으로 축소하는 컷라인 사용
"""
import os, json, time, sys
import pandas as pd
from prompts import CHECKLIST_ITEMS, build_prompt, parse_response, derive_label, derive_confidence
from filters import is_opinion  # 사설·칼럼 등 의견 장르 제외 (notes/16 확정 규칙)

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

try:
    from google import genai
    from google.genai import types
except ImportError:
    os.system(f"{sys.executable} -m pip install google-genai -q")
    from google import genai
    from google.genai import types

# 입력: 인자로 CSV 경로를 주면 그 파일, 없으면 out/sample_* 중 최신 자동 선택
# 출력: 입력 파일명 기준 out/classified_<입력이름>.csv (파일럿/본분류 결과 분리)
if len(sys.argv) > 1:
    INPUT_PATH = sys.argv[1]
else:
    INPUT_PATH = os.path.join("out", sorted(f for f in os.listdir("out") if f.startswith("sample_"))[-1])
OUT_PATH = os.path.join("out", "classified_" + os.path.splitext(os.path.basename(INPUT_PATH))[0] + ".csv")

MODEL = "gemini-3.1-flash-lite"  # 무료 등급 사용 가능 확인됨 (2.5 계열은 이 키에서 할당량 0)
SECONDS_PER_REQ = 7              # 분당 요청 제한(RPM) 대응 — 05_llm_eval 142건 무사고 실측값. 장시간 무인 실행이라 안전 우선
BATCH_SAVE_EVERY = 50

# ── 프롬프트는 prompts.py 공용 모듈(05_llm_eval.py·서비스와 동일 SSOT) ──
SCORE_COLS = (["역할_감시", "역할_정보·의제", "역할_해결책", "감시점수"]
              + [f"체크_{it}" for it in CHECKLIST_ITEMS])

GEN_CONFIG = types.GenerateContentConfig(
    response_mime_type="application/json",  # JSON 출력 강제 — 파싱 실패 방지
    max_output_tokens=700,                  # 체크리스트+개선제안 3개까지 담기게 넉넉히
    temperature=0,
)

def classify_one(client, row):
    msg = build_prompt(row["언론사"], row["제목"], row["본문"])
    r = client.models.generate_content(model=MODEL, contents=msg, config=GEN_CONFIG)
    text = (r.text or "").strip()
    try:
        return parse_response(json.loads(text)), None
    except Exception:
        return None, text[:200]

def main():
    if not os.environ.get("GEMINI_API_KEY"):
        print("GEMINI_API_KEY 환경변수가 없습니다. https://aistudio.google.com/apikey 에서 발급 후 설정하세요.")
        sys.exit(1)

    df = pd.read_csv(INPUT_PATH)
    id_col = "표본ID" if "표본ID" in df.columns else "평가ID"  # 본조사/평가셋 형식 모두 지원

    # 의견 장르(사설·칼럼 등) 제외 — notes/16 확정 규칙.
    # 3분류 rubric은 '보도기사의 역할'용이라 사설·칼럼은 감시 쪽으로 구조적 쏠림 → 감시 비중 부풀림.
    # LLM 호출 전에 드롭해야 API 비용도 아끼고 집계 모수도 맞는다.
    n_before = len(df)
    df = df[~df["제목"].map(is_opinion)].copy()
    if n_before != len(df):
        print(f"[의견장르 제외] 사설·칼럼 등 {n_before - len(df)}건 드롭 "
              f"({n_before} → {len(df)}건, 제목 마커 기준)")

    out_path = OUT_PATH
    done = set()
    if os.path.exists(out_path):  # 중단 후 재개 지원 (일일 한도 걸리면 다음날 그대로 재실행)
        prev = pd.read_csv(out_path)
        done = set(prev[id_col])
        results = prev.to_dict("records")
        print(f"[재개] 기존 {len(done)}건 건너뜀")
    else:
        results = []

    client = genai.Client()  # GEMINI_API_KEY 환경변수 자동 인식
    todo = df[~df[id_col].isin(done)]
    # 2번째 인자로 이번 실행에서 처리할 최대 건수 지정 가능 (일일 한도·시간 관리용)
    #   예) python 02_classify.py out/sample_2448.csv 500
    if len(sys.argv) > 2:
        limit = int(sys.argv[2])
        if limit < len(todo):
            print(f"[제한] 이번 실행은 {limit}건까지만 처리 (남은 대상 {len(todo)}건)")
            todo = todo.head(limit)
    print(f"[분류] 대상 {len(todo)}건 / 모델 {MODEL} / 입력 {INPUT_PATH} → 출력 {out_path}")
    print(f"       요청 간격 {SECONDS_PER_REQ}초 — 예상 소요 약 {len(todo) * SECONDS_PER_REQ // 60}분 (일일 한도 도달 시 중단 후 내일 재실행)")

    for i, (_, row) in enumerate(todo.iterrows(), 1):
        try:
            parsed, err = classify_one(client, row)
        except Exception as e:
            emsg = str(e)
            if "429" in emsg or "RESOURCE_EXHAUSTED" in emsg:
                print(f"  요청 한도 도달({row[id_col]}) — 60초 후 재시도")
                time.sleep(60)
            else:
                print(f"  오류({row[id_col]}): {emsg[:80]} — 10초 후 재시도")
                time.sleep(10)
            try:
                parsed, err = classify_one(client, row)
            except Exception as e2:
                emsg2 = str(e2)
                if "429" in emsg2 or "RESOURCE_EXHAUSTED" in emsg2:
                    # 일일 한도 소진으로 판단 — 저장하고 종료 (내일 재실행하면 이어서 함)
                    pd.DataFrame(results).to_csv(out_path, index=False, encoding="utf-8-sig")
                    print(f"[중단] 일일 한도 소진 추정. {len(results)}건 저장됨 — 내일 같은 명령으로 재실행하세요.")
                    sys.exit(0)
                parsed, err = None, emsg2[:120]
        rec = {id_col: row[id_col], "LLM오류": "" if parsed else "파싱실패"}
        if parsed is None:
            for c in SCORE_COLS:
                rec[c] = None
            rec["LLM분류"] = "파싱실패"
            rec["LLM확신도"] = ""
            rec["LLM근거"] = err or ""
            rec["improvements"] = ""
        else:
            for c in SCORE_COLS:
                rec[c] = parsed[c]
            rec["LLM분류"] = derive_label(parsed)
            rec["LLM확신도"] = derive_confidence(parsed)
            rec["LLM근거"] = parsed["reason"]
            rec["improvements"] = " | ".join(map(str, parsed["improvements"]))
        results.append(rec)
        if i % BATCH_SAVE_EVERY == 0:
            pd.DataFrame(results).to_csv(out_path, index=False, encoding="utf-8-sig")
            print(f"  ...{i}/{len(todo)} 저장")
        time.sleep(SECONDS_PER_REQ)

    pd.DataFrame(results).to_csv(out_path, index=False, encoding="utf-8-sig")
    print(f"[완료] {out_path}")
    print(pd.DataFrame(results)["LLM분류"].value_counts())

if __name__ == "__main__":
    main()
