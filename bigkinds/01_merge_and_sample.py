# -*- coding: utf-8 -*-
"""
빅카인즈 구성날짜 표집 파일 병합 → 정제 → 매체×월 층화 추출
사용법:
  1) NewsResult_*.xlsx 24개를 data/ 폴더에 모은다
  2) python 01_merge_and_sample.py
산출물:
  out/pool_clean.csv    정제된 전체 풀 (분류·중복 필터 후)
  out/sample_2448.csv   층화 추출 표본 (매체×월 × PER_CELL건)
  out/sampling_log.txt  정제·추출 과정 수치 기록 (보고서 p6용)
"""
import glob, os, re, sys
import pandas as pd

# Windows cp949 콘솔에서 이모지 출력 시 UnicodeEncodeError 방지
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# ===== 설정 =====
DATA_DIR = "data"
OUT_DIR = "out"
PER_CELL = 17          # 매체×월 셀당 추출 건수 (12매체×12월×17 = 2,448)
SEED = 42              # 재현성 (보고서에 명시)
VALID_CATS = {"정치", "경제", "사회"}
# 모집단 매체 12개 (중앙지) — 다운로드 시 언론사 필터 누락 방어
VALID_PRESS = {"경향신문", "국민일보", "내일신문", "동아일보", "문화일보", "서울신문",
               "세계일보", "아시아투데이", "조선일보", "중앙일보", "한겨레", "한국일보"}
# 통신사 전재 의심 필터용 (기고자/본문 패턴). 필요 시 보완.
WIRE_PATTERNS = ["연합뉴스", "뉴시스", "뉴스1", "newsis", "yna"]

os.makedirs(OUT_DIR, exist_ok=True)
log_lines = []
def log(msg):
    print(msg)
    log_lines.append(str(msg))

# ===== 1. 병합 =====
files = sorted(glob.glob(os.path.join(DATA_DIR, "NewsResult_*.xlsx")))
log(f"[병합] 파일 {len(files)}개 발견")
assert len(files) > 0, "data/ 폴더에 NewsResult_*.xlsx 파일이 없습니다"

dfs = []
for f in files:
    d = pd.read_excel(f, converters={"뉴스 식별자": str})
    d["_source_file"] = os.path.basename(f)
    dfs.append(d)
    log(f"  - {os.path.basename(f)}: {len(d)}건")
df = pd.concat(dfs, ignore_index=True)
log(f"[병합] 총 {len(df)}건")

# ===== 2. 정제 =====
n0 = len(df)

# 2-0. 모집단 연도(2025) 밖 기사 차단 — 다운로드 시 연도 실수 방지 가드
df["일자"] = df["일자"].astype(str)
wrong_year = df[~df["일자"].str.startswith("2025")]
if len(wrong_year):
    bad = sorted(wrong_year["일자"].str[:4].unique())
    raise SystemExit(f"[중단] 2025년이 아닌 기사 {len(wrong_year)}건 발견 (연도: {bad}). "
                     f"해당 파일을 빅카인즈에서 2025년으로 다시 받아주세요.")

# 2-0b. 모집단 매체 12개 외 언론사 제거 — 다운로드 시 언론사 필터 누락 방어
n_press = len(df)
df = df[df["언론사"].isin(VALID_PRESS)].copy()
if n_press != len(df):
    log(f"[정제] 모집단 외 언론사 제거: {n_press} → {len(df)} (언론사 필터 없이 받은 파일 포함 추정)")

# 2-1. 빅카인즈 자체 판정 중복·예외 제거
df = df[df["분석제외 여부"].isna()].copy()
log(f"[정제] 분석제외(중복·예외) 제거: {n0} → {len(df)}")

# 2-2. 대분류1이 정치/경제/사회인 기사만 (분류2·3 매칭으로 섞여 들어온 문화·스포츠 등 제거)
df["대분류"] = df["통합 분류1"].astype(str).str.split(">").str[0]
n1 = len(df)
df = df[df["대분류"].isin(VALID_CATS)].copy()
log(f"[정제] 대분류1 재필터(정치·경제·사회): {n1} → {len(df)}")

# 2-3. 뉴스 식별자 기준 중복 제거 (파일 간 중복 방지)
n2 = len(df)
df = df.drop_duplicates(subset=["뉴스 식별자"]).copy()
log(f"[정제] 식별자 중복 제거: {n2} → {len(df)}")

# 2-4. 통신사 전재 의심 기사 플래그 (제거하지 않고 표시만 — 포함/제외 두 버전 산출용)
pat = "|".join(WIRE_PATTERNS)
df["통신사전재_의심"] = (
    df["기고자"].astype(str).str.contains(pat, case=False, na=False)
    | df["본문"].astype(str).str[:60].str.contains(pat, case=False, na=False)
)
log(f"[정제] 통신사 전재 의심 플래그: {df['통신사전재_의심'].sum()}건 (제거하지 않음, 분석 시 두 버전 산출)")

# 2-5. 초단신 제거 (본문 100자 미만 — 포토뉴스·단신)
n3 = len(df)
df = df[df["본문"].astype(str).str.len() >= 100].copy()
log(f"[정제] 100자 미만 단신 제거: {n3} → {len(df)}")

# 2-6. 월 컬럼 생성
df["일자"] = df["일자"].astype(str)
df["월"] = df["일자"].str[4:6].astype(int)

# 풀 저장
pool_path = os.path.join(OUT_DIR, "pool_clean.csv")
df.to_csv(pool_path, index=False, encoding="utf-8-sig")
log(f"[저장] 정제 풀: {pool_path} ({len(df)}건)")

# 매체×월 셀 현황
pivot = df.pivot_table(index="언론사", columns="월", values="뉴스 식별자", aggfunc="count", fill_value=0)
log("\n[셀 현황] 매체×월 기사 수:")
log(pivot.to_string())
short_cells = (pivot < PER_CELL).sum().sum()
if short_cells:
    log(f"⚠️ {PER_CELL}건 미만 셀 {short_cells}개 — 해당 셀은 전량 사용됨(아래 추출 로직)")

# ===== 3. 층화 추출 =====
def sample_cell(g):
    n = min(PER_CELL, len(g))
    return g.sample(n=n, random_state=SEED)

idx = []
for _, g in df.groupby(["언론사", "월"]):
    n = min(PER_CELL, len(g))
    idx.extend(g.sample(n=n, random_state=SEED).index.tolist())
sample = df.loc[idx].reset_index(drop=True)
sample = sample.sample(frac=1, random_state=SEED).reset_index(drop=True)  # 순서 셔플(라벨링 편향 방지)
sample["표본ID"] = ["S" + str(i).zfill(4) for i in range(1, len(sample) + 1)]

sample_path = os.path.join(OUT_DIR, f"sample_{len(sample)}.csv")
cols = ["표본ID", "뉴스 식별자", "일자", "월", "언론사", "기고자", "제목",
        "통합 분류1", "대분류", "키워드", "특성추출(가중치순 상위 50개)",
        "본문", "URL", "통신사전재_의심"]
sample[cols].to_csv(sample_path, index=False, encoding="utf-8-sig")
log(f"\n[추출] 층화 표본 {len(sample)}건 저장: {sample_path}")
log(f"       (매체×월 셀당 {PER_CELL}건, seed={SEED})")

# ===== 4. 검증용 150건 분리 =====
gold = sample.sample(n=150, random_state=SEED)
gold_path = os.path.join(OUT_DIR, "gold_150_for_labeling.csv")
gold_cols = ["표본ID", "언론사", "일자", "제목", "본문", "라벨_A", "라벨_B", "최종라벨"]
g = gold.copy()
g["라벨_A"] = ""; g["라벨_B"] = ""; g["최종라벨"] = ""
g[gold_cols].to_csv(gold_path, index=False, encoding="utf-8-sig")
log(f"[검증셋] 수기 라벨링용 150건: {gold_path} (라벨_A/라벨_B 컬럼 비워둠 — 각자 독립 기입)")

with open(os.path.join(OUT_DIR, "sampling_log.txt"), "w", encoding="utf-8") as f:
    f.write("\n".join(log_lines))
log("\n완료. sampling_log.txt에 전 과정 기록됨 (보고서 p6 방법 서술에 사용)")
