# -*- coding: utf-8 -*-
"""
LLM 분류기 정확도 검증용 평가셋 조립
배경: 본조사 표본(2,448건)은 랜덤·층화라 감시 기사가 ~10%뿐 → 랜덤 표본만으로는
     "AI가 감시를 감시라고 맞히는지" 검증 불가. 평가셋만 감시·해결책 후보를
     오버샘플링해서 만든다. (본조사 표본 sample_2448.csv는 건드리지 않음)

입력 (data_eval/ 폴더, 파일명 정확히 일치해야 함):
  eval_watchdog_pool.xlsx  제목 (단독 OR 의혹 OR 입수 OR 취재 OR 내부문건)
  eval_dandok.xlsx         제목 '단독'만
  eval_solution.xlsx       제목 (해법 OR 대안 OR 개선 방안 OR 해외 사례)
  ※ 모두 2025년 / 중앙지 12개 / 정치·경제·사회 조건으로 받은 것

산출:
  out/pilot_45.csv    파일럿 45건 (감시후보 30 = watchdog 20 + dandok 10, 해결책후보 15) seed=101
  out/evalset_150.csv 평가셋 150건 (감시후보 50 = watchdog 35 + dandok 15, 해결책후보 30,
                      랜덤 70 = gold_150에서) seed=202
  - 파일럿에 쓴 기사는 평가셋에서 식별자 기준 제외 (튜닝 데이터로 채점 금지)
  - 기존 pilot_30(프롬프트 튜닝에 사용)도 랜덤 70에서 제외
"""
import os, sys
import pandas as pd

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

DATA_EVAL = "data_eval"
OUT_DIR = "out"
SEED_PILOT = 101
SEED_EVAL = 202
VALID_CATS = {"정치", "경제", "사회"}
VALID_PRESS = {"경향신문", "국민일보", "내일신문", "동아일보", "문화일보", "서울신문",
               "세계일보", "아시아투데이", "조선일보", "중앙일보", "한겨레", "한국일보"}
COLS = ["뉴스 식별자", "일자", "언론사", "제목", "본문",
        "특성추출(가중치순 상위 50개)", "URL"]

EXPECTED = {
    "watchdog": os.path.join(DATA_EVAL, "eval_watchdog_pool.xlsx"),
    "dandok":   os.path.join(DATA_EVAL, "eval_dandok.xlsx"),
    "solution": os.path.join(DATA_EVAL, "eval_solution.xlsx"),
}
missing = [p for p in EXPECTED.values() if not os.path.exists(p)]
if missing:
    print("다음 파일이 없습니다. 빅카인즈에서 받은 뒤 이 이름으로 바꿔서 data_eval/에 넣어주세요:")
    for p in missing:
        print(" -", p)
    sys.exit(1)


def load_clean(path):
    """01번과 동일한 전처리."""
    d = pd.read_excel(path, converters={"뉴스 식별자": str})
    n0 = len(d)
    d["일자"] = d["일자"].astype(str)
    bad = d[~d["일자"].str.startswith("2025")]
    if len(bad):
        raise SystemExit(f"[중단] {path}: 2025년이 아닌 기사 {len(bad)}건 "
                         f"(연도: {sorted(bad['일자'].str[:4].unique())}). 다시 받아주세요.")
    d = d[d["언론사"].isin(VALID_PRESS)]
    d = d[d["분석제외 여부"].isna()]
    d["대분류"] = d["통합 분류1"].astype(str).str.split(">").str[0]
    d = d[d["대분류"].isin(VALID_CATS)]
    d = d[d["본문"].astype(str).str.len() >= 100]
    d = d.drop_duplicates(subset=["뉴스 식별자"]).copy()
    print(f"[전처리] {os.path.basename(path)}: {n0} → {len(d)}")
    return d


def sample_n(df, n, seed, name):
    if len(df) < n:
        raise SystemExit(f"[중단] {name} 풀이 {len(df)}건뿐이라 {n}건을 못 뽑습니다.")
    return df.sample(n=n, random_state=seed)


def finalize(parts, id_prefix, seed, path):
    """출처 붙여 합치고 셔플, 평가ID·빈 라벨 컬럼 부여, 저장."""
    df = pd.concat(parts, ignore_index=True)
    assert df["뉴스 식별자"].duplicated().sum() == 0, "산출물 내부에 중복 식별자"
    df = df.sample(frac=1, random_state=seed).reset_index(drop=True)  # 순서 셔플(출처 편향 방지)
    df["평가ID"] = [id_prefix + str(i).zfill(4) for i in range(1, len(df) + 1)]
    df["라벨_A"] = ""; df["라벨_B"] = ""; df["최종라벨"] = ""
    # '출처'는 맨 뒤: 라벨링용으로 열 때 가리기 쉽도록
    out = df[["평가ID"] + COLS + ["라벨_A", "라벨_B", "최종라벨", "출처"]]
    out.to_csv(path, index=False, encoding="utf-8-sig")
    print(f"\n[저장] {path} ({len(out)}건)")
    print(out["출처"].value_counts().to_string())
    return out


def tag(df, source):
    d = df[COLS].copy()
    d["출처"] = source
    return d


watch = load_clean(EXPECTED["watchdog"])
dand = load_clean(EXPECTED["dandok"])
sol = load_clean(EXPECTED["solution"])

# ===== 산출물 1: 파일럿 45건 =====
# dandok은 watchdog_pool의 부분집합일 수 있음('단독'이 검색어에 포함) → dandok 먼저 뽑고 제외
p_dand = sample_n(dand, 10, SEED_PILOT, "dandok(파일럿)")
p_watch = sample_n(watch[~watch["뉴스 식별자"].isin(p_dand["뉴스 식별자"])], 20, SEED_PILOT, "watchdog(파일럿)")
p_sol = sample_n(sol, 15, SEED_PILOT, "solution(파일럿)")
pilot = finalize([tag(p_watch, "watchdog"), tag(p_dand, "dandok"), tag(p_sol, "solution")],
                 "P", SEED_PILOT, os.path.join(OUT_DIR, "pilot_45.csv"))
pilot_ids = set(pilot["뉴스 식별자"])

# ===== 산출물 2: 평가셋 150건 =====
e_dand = sample_n(dand[~dand["뉴스 식별자"].isin(pilot_ids)], 15, SEED_EVAL, "dandok(평가셋)")
used = pilot_ids | set(e_dand["뉴스 식별자"])
e_watch = sample_n(watch[~watch["뉴스 식별자"].isin(used)], 35, SEED_EVAL, "watchdog(평가셋)")
used |= set(e_watch["뉴스 식별자"])
e_sol = sample_n(sol[~sol["뉴스 식별자"].isin(used)], 30, SEED_EVAL, "solution(평가셋)")
used |= set(e_sol["뉴스 식별자"])

# 랜덤 70: gold_150에서 — 컬럼 보강 위해 sample_2448과 표본ID로 조인
gold = pd.read_csv(os.path.join(OUT_DIR, "gold_150_for_labeling.csv"))
s2448 = pd.read_csv(os.path.join(OUT_DIR, "sample_2448.csv"), dtype={"뉴스 식별자": str})
s2448["일자"] = s2448["일자"].astype(str)
g = s2448[s2448["표본ID"].isin(set(gold["표본ID"]))].copy()

# 기존 pilot_30은 프롬프트 튜닝에 사용됨 → 랜덤 70 후보에서 제외
p30_path = os.path.join(OUT_DIR, "pilot_30_ids.txt")
if os.path.exists(p30_path):
    p30 = set(open(p30_path, encoding="utf-8").read().split())
    g = g[~g["표본ID"].isin(p30)]
    print(f"\n[제외] 기존 pilot_30 (프롬프트 튜닝 사용분) {len(p30)}건 → 랜덤 후보 {len(g)}건")
g = g[~g["뉴스 식별자"].isin(used)]
e_rand = sample_n(g, 70, SEED_EVAL, "random(평가셋)")

evalset = finalize([tag(e_watch, "watchdog"), tag(e_dand, "dandok"),
                    tag(e_sol, "solution"), tag(e_rand, "random")],
                   "E", SEED_EVAL, os.path.join(OUT_DIR, "evalset_150.csv"))

# ===== 검증 출력 =====
overlap_pe = pilot_ids & set(evalset["뉴스 식별자"])
print(f"\n[검증] 파일럿 ∩ 평가셋: {len(overlap_pe)}건 (0이어야 함)")
assert len(overlap_pe) == 0
overlap_main = set(evalset["뉴스 식별자"]) & set(s2448["뉴스 식별자"])
print(f"[참고] 평가셋 ∩ 본조사 표본 2,448: {len(overlap_main)}건 (겹쳐도 무방)")
print("\n완료. 다음 단계: pilot_45로 프롬프트 튜닝 → evalset_150 수기 라벨링 → 채점")
