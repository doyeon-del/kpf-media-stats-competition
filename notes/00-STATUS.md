# 프로젝트 상태 (이어서 작업할 때 여기부터 읽기)

**공모전**: 한국언론진흥재단 언론통계 분석·활용 경진대회 / 단독 / 마감 **2026-07-23 10:00** / daker.ai
**주제 B**: 생산자(언론인)–수용자 인식 격차 → 정책+서비스 제안.

## 현재 위치: W2(분석) — 시계열 확장 **완료**. 다음은 **차트 + 보고서 서사 초안**

### 완료
- 데이터 적재: `data/raw/{audience_2021~2025, journalist_2021·2023·2025, socialmedia_2021·2024}` (git 미추적)
- 분석환경: `.venv` (pandas / pyreadstat==1.2.7 / openpyxl / matplotlib 한글폰트 AppleGothic / pypdf)
- 문항 매핑: `notes/03-question-mapping.md` — **F절에 시계열 결합 확정 크로스워크 + 착수전검증 전항목 완료**
- 발견 3종(2025 단면): `notes/04-finding-triangle-2025.md`, `notes/05-finding-gap13.md`
  - ① 7역할 3각비교 / ② 5속성 자기평가 / ③ 문제점 심각성(2023)
- **발견 ④ 시계열(2021·2023·2025): `notes/06-finding-timeseries.md`** — 스크립트 `analysis/07_verify_timeseries.py`(검증)·`08_timeseries_gap.py`(집계)
  - ④-A 5속성 격차 3개년 항상 음수(자만론 추세로도 반증) / ④-B 감시견 이상-체감 격차 매년 최대(구조적 고착) / 2023 변곡점·비대칭 회복
- 차트: `report/assets/{triangle_2025, gap1_5attr_2025, gap3_problems_2023}.png`
- CSV: `data/processed/ts_gap1_5attr.csv, ts_gap2_roles.csv, ts_gap{1,2}_yearmean.csv`
- 통합 논지: "격차=자만vs불신 아님. 부족의 '내용' 불일치" → 시계열로 확증(감시견 격차 구조적 고착). `notes/06` 하단.

### 확정된 시계열 범위 (재작업 방지)
- GAP-1 5속성: 2021·2023·2025 깨끗(양쪽 '언론 전반'). GAP-2 역할: 기자 중요도↔수용자 체감 깨끗.
- **GAP-3 문제점 = 시계열 불가**(기자 q16 2023만 존재) → 2023 단면 고정.
- 기자 실행바 2025 대상단절(자사→전반) → 시계열로 읽지 말 것. 언론인 2021·2023 SAV는 라벨 비어있음(변수명 매핑).

### 완료 추가 (2026-07-07)
- 시계열 차트: `report/assets/{ts_gap1_5attr, ts_gap2_roles}.png` (`analysis/09_ts_charts.py`)
- 정책 근거 집계: `analysis/10_policy_basis.py` → 문84 대응방안·문85 책임주체·문86. CSV `data/processed/policy_q8{4,5}_*.csv`
  - 핵심: 책임주체 **언론사 4.14 최고**(이용자 3.29 최하) / 대응방안 **미디어리터러시 교육 3.85 최하위**(피해구제 4.07·처벌 4.06·팩트체크 4.01 상위)
- **보고서 서사 초안(B안) 완성: `notes/07-report-narrative.md`** — 발견①~④ + 정책근거를 "진단 격차의 구조적 고착" 논지로 통합. 정책 P1~P3 + 서비스 S1~S2 + 한계.

### 다음 할 일 (NEXT): 보고서 시각화·레이아웃(W3) + 레포/옵시디언 정리
1. 표지급 비주얼 선정(발견① 3각 계단 or ④-B 감시견 추세) + 서론 외부통계 인용 보강
2. 서사 → PDF 레이아웃 디자인
3. GitHub **private** 레포 생성(이름 언론재단 통계 경진대회 취지 반영, 예: `kpf-media-stats-competition`) — 대회 후 public 전환. 원자료 커밋 금지
4. 옵시디언 작업기록 갱신(20_Projects에 폴더 신설 완료)

## 재개 방법
새 세션에서 "언론재단 공모전 이어서 하자 — notes/00-STATUS.md 봐" 라고 하면 됨.
스크립트는 `analysis/01~06` 순번. 실행: `./.venv/bin/python analysis/<파일>`.
