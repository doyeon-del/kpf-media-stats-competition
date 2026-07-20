# -*- coding: utf-8 -*-
"""
§6.3 시연(표 7) 근거 산출 — 실제 기사 before/after 재평가.

배경: 본문 표 7의 18점 → 76점은 기획 단계의 예시값이었다. 실측값으로 교체하기 위해
     본조사 485건에서 '보도자료를 거의 그대로 옮겨 쓴' 실제 기사를 골라 before 점수를 확인하고,
     서비스가 생성한 개선 제안 3가지를 반영한 개선본을 작성해 동일 프롬프트로 재평가한다.

⚠️ 개선본(after)은 실제 보도된 기사가 아니라 **연구진이 개선 제안을 반영해 작성한 수정본**이다.
   보고서에도 그렇게 명시해야 한다(실제 기사인 것처럼 쓰면 안 됨).

실행: python 07_demo_before_after.py
출력: out/demo_before_after.txt
"""
import os, sys, json, time
import pandas as pd
from google import genai
from google.genai import types
from prompts import build_prompt, parse_response, derive_label, CHECKLIST_ITEMS, WATCH_THRESHOLD

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

MODEL = "gemini-3.1-flash-lite"
TARGET_ID = "S0119"  # 아래에서 실제 ID로 교체됨
GEN = types.GenerateContentConfig(response_mime_type="application/json",
                                  max_output_tokens=700, temperature=0)

# 개선본: 서비스가 제시한 개선 제안 3가지를 반영해 작성한 수정본
# (① 재무제표 세부 항목 분석 ② 업계 관계자 인터뷰 ③ 부채비율 등 재무 지표 검증)
AFTER_BODY = (
    "동부건설은 올해 3분기까지 수익성과 재무 안정성이 동시에 개선됐다고 14일 밝혔다. "
    "회사는 원가 혁신과 선별 수주, 재무구조 정상화를 이유로 들었다. "
    "그러나 본지가 금융감독원 전자공시시스템에 제출된 3분기 보고서를 확인한 결과, "
    "영업이익 173억원 가운데 상당 부분은 판매관리비 축소와 일부 현장의 공사손실충당금 환입에서 나온 것으로 "
    "회사가 강조한 '원가 혁신'의 효과와는 성격이 달랐다. "
    "부채비율은 전년 동기 대비 낮아졌으나, 이는 자본 확충이 아니라 총차입금 상환에 따른 것으로 "
    "현금성 자산도 함께 줄었다. "
    "회사가 '선별 수주'라고 설명한 신규 수주 감소분에 대해 하도급 업체 관계자는 "
    "\"발주 물량 자체가 줄어 현장에서 체감하는 일감은 오히려 부족하다\"고 말했다. "
    "건설업계 재무 분석을 담당하는 한 신용평가사 연구원은 \"일회성 요인을 제외하면 "
    "본질적 수익성 회복으로 보기에는 이르다\"고 평가했다. "
    "동부건설 관계자는 이에 대해 \"충당금 환입은 정상적인 회계 처리이며, "
    "수익성 개선 추세는 유효하다\"고 반박했다."
)


def evaluate(client, press, title, body):
    msg = build_prompt(press, title, body)
    r = client.models.generate_content(model=MODEL, contents=msg, config=GEN)
    return parse_response(json.loads((r.text or "").strip()))


def show(tag, p, lines):
    def w(s):
        print(s); lines.append(s)
    w(f"\n[{tag}] 감시 점수 {p['감시점수']}/100  (판정: {derive_label(p)})")
    for it in CHECKLIST_ITEMS:
        v = p[f"체크_{it}"]
        mark = "충족" if v >= 12 else ("부분 충족" if v >= 6 else "미충족")
        w(f"   {it.replace('_',' '):16} {v:2}/20  {mark}")
    w(f"   근거: {p['reason'][:150]}")
    return p


def main():
    d = pd.read_csv("out/classified_sample_2448.csv")
    s = pd.read_csv("out/sample_2448.csv")
    m = d.merge(s[["표본ID", "제목", "본문", "언론사"]], on="표본ID")
    row = m[m["제목"].str.contains("동부건설", na=False)].iloc[0]

    lines = []
    def w(s=""):
        print(s); lines.append(s)

    w("=" * 70)
    w("§6.3 시연 — 실제 기사 before/after 재평가")
    w("=" * 70)
    w(f"대상: {row['언론사']} | {row['제목']}")
    w(f"표본ID: {row['표본ID']}")
    w(f"\n[before 본문]\n{row['본문'][:220]}")
    w(f"\n[서비스가 생성한 개선 제안]")
    for i, s_ in enumerate(str(row["improvements"]).split(" | "), 1):
        w(f"   {i}. {s_}")

    client = genai.Client()
    w("\n" + "-" * 70)
    before = evaluate(client, row["언론사"], row["제목"], row["본문"])
    show("BEFORE (실제 보도된 기사)", before, lines)

    time.sleep(7)
    after_title = "동부건설 3분기 영업익 173억 원가 혁신 효과?  충당금 환입이 상당분"
    after = evaluate(client, row["언론사"], after_title, AFTER_BODY)
    show("AFTER (개선 제안 반영한 수정본 — 연구진 작성)", after, lines)

    w("\n" + "=" * 70)
    w(f"결과: {before['감시점수']}점 → {after['감시점수']}점 "
      f"(+{after['감시점수']-before['감시점수']}점)")
    w("=" * 70)
    w("\n표 7에 넣을 항목별 충족 여부:")
    w(f"{'항목':18}{'개선 전':>10}{'개선 후':>10}")
    for it in CHECKLIST_ITEMS:
        f = lambda v: "충족" if v >= 12 else ("부분 충족" if v >= 6 else "미충족")
        w(f"{it.replace('_',' '):18}{f(before[f'체크_{it}']):>10}{f(after[f'체크_{it}']):>10}")

    with open("out/demo_before_after.txt", "w", encoding="utf-8") as fp:
        fp.write("\n".join(lines) + "\n")
    print("\n저장 → out/demo_before_after.txt")


if __name__ == "__main__":
    main()
