# -*- coding: utf-8 -*-
"""그림: 분석 파이프라인 — 데이터 → 네 갈래 분석 → 핵심 결과 → 서비스(온글).
보고서 ③ 도입부. 수치: 본조사 1,469건 · 신뢰 연관 d=1.66 (2026-07-21 확정)."""
import sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
plt.rcParams["font.family"] = "Malgun Gothic"
plt.rcParams["axes.unicode_minus"] = False

NAVY = "#1A4E8A"; NAVY_SOFT = "#EAF2FD"
RED = "#C0392B"; RED_SOFT = "#FBE9E9"
GRAY = "#5B6068"; LINE = "#D9DCE1"

fig, ax = plt.subplots(figsize=(14, 6.1), dpi=200)
ax.set_xlim(0, 14); ax.set_ylim(0, 6.1); ax.axis("off")

def box(x0, y0, x1, y1, fc, ec, lw=1.4, ls="-"):
    ax.add_patch(FancyBboxPatch((x0, y0), x1 - x0, y1 - y0,
                 boxstyle="round,pad=0.02,rounding_size=0.1",
                 fc=fc, ec=ec, lw=lw, linestyle=ls, zorder=2))

def arrow(x0, y0, x1, y1, color, lw=1.5):
    ax.add_patch(FancyArrowPatch((x0, y0), (x1, y1),
                 arrowstyle="-|>", mutation_scale=12, lw=lw, color=color,
                 shrinkA=0, shrinkB=0, zorder=1))

def T(x, y, s, size=9, weight="normal", color="#111317", ha="center", va="center"):
    ax.text(x, y, s, fontsize=size, fontweight=weight, color=color,
            ha=ha, va=va, zorder=3, linespacing=1.4)

# 열 헤더
for x, s in [(1.55, "활용 데이터"), (5.8, "분석"), (10.05, "핵심 결과"), (12.98, "서비스 제안")]:
    T(x, 5.85, s, size=11, weight="bold", color=GRAY)
ax.plot([0.25, 13.85], [5.62, 5.62], color=LINE, lw=1, zorder=1)

# 트랙 y 좌표 (제목행, 본문행 공용 중심)
Y1, Y2, Y4, Y3 = (4.70, 5.38), (3.76, 4.44), (2.82, 3.50), (1.60, 2.28)

# 데이터 박스
box(0.25, 2.82, 2.85, 5.38, NAVY_SOFT, NAVY)
T(1.55, 4.85, "한국언론진흥재단\n조사 데이터", size=10.2, weight="bold", color=NAVY)
T(1.55, 3.70, "언론인 2021·23·25\n(2025 n=2,020)\n수용자 2021·23·25\n(2025 n=6,000)", size=8.2, color="#333")

box(0.25, 1.30, 2.85, 2.58, RED_SOFT, RED)
T(1.55, 2.16, "빅카인즈 뉴스 빅데이터", size=10.2, weight="bold", color=RED)
T(1.55, 1.68, "2025년 중앙지 12개 · 정치·경제·사회", size=8.2, color="#333")

def track(yy, title, body, ec):
    y0, y1 = yy
    box(3.6, y0, 8.0, y1, "white", ec, lw=1.3)
    T(3.78, (y0 + y1) / 2 + 0.17, title, size=9.2, weight="bold", color=ec, ha="left")
    T(3.78, (y0 + y1) / 2 - 0.15, body, size=8.3, color="#333", ha="left")

track(Y1, "결과① 인식 격차", "공통 조사연도 결합 → 7역할을 3기능군으로 → 격차 = 중요도 - 체감", NAVY)
track(Y2, "결과② AI 활용", "생성형 AI 문항 집계 (2023 ↔ 2025 비교)", NAVY)
track(Y4, "결과④ 신뢰 연관", "역할 체감 ↔ 전반 신뢰(문87) · t검정 + 가중 회귀", NAVY)
track(Y3, "결과③ 지면 실측", "층화 2,448건 → 의견장르 제외 2,377건 → LLM 채점 1,469건", RED)

# 검증 배지
box(3.6, 0.30, 8.0, 0.98, "white", RED, lw=1.0, ls=(0, (4, 2)))
T(5.8, 0.64, "검증 | 골든셋 150건(2인 독립 라벨링 → 협의) → 정확도 93.0% · 정밀도 1.000", size=8.1, color=RED)
arrow(5.8, 0.98, 5.8, 1.60, RED, lw=1.1)

def pill(yy, big, small, ec):
    y0, y1 = yy
    box(8.7, y0, 11.4, y1, "white", ec, lw=1.7)
    T(10.05, (y0 + y1) / 2 + 0.16, big, size=10.2, weight="bold", color=ec)
    T(10.05, (y0 + y1) / 2 - 0.18, small, size=8.2, color="#333")

pill(Y1, "감시 격차 1.24", "3개년 내내 최대 · 고착", NAVY)
pill(Y2, "AI 활용률 58.1%", "사실 검증 활용은 23.0%", NAVY)
pill(Y4, "감시 체감 상·하 신뢰차 1.0점", "d=1.66 · 회귀에서도 모두 유의", NAVY)
pill(Y3, "감시 점수 중앙값 5점", "91.6%가 20점 미만", RED)

# 서비스
box(12.1, 1.85, 13.85, 4.85, NAVY, NAVY)
T(12.98, 3.85, "온글", size=14, weight="bold", color="white")
T(12.98, 3.25, "감시 보도\n코파일럿", size=10, weight="bold", color="white")
T(12.98, 2.45, "분석과 동일한\n기준 · 엔진", size=8.2, color="#CFE0F5")

# 화살표
mid = lambda yy: (yy[0] + yy[1]) / 2
for yy in [Y1, Y2, Y4]:
    arrow(2.85, mid(yy), 3.6, mid(yy), NAVY)
arrow(2.85, mid(Y3), 3.6, mid(Y3), RED)
for yy, c in [(Y1, NAVY), (Y2, NAVY), (Y4, NAVY), (Y3, RED)]:
    arrow(8.0, mid(yy), 8.7, mid(yy), c)
for yy, c, ty in [(Y1, NAVY, 4.3), (Y2, NAVY, 3.8), (Y4, NAVY, 3.2), (Y3, RED, 2.5)]:
    arrow(11.4, mid(yy), 12.1, ty, c)

plt.tight_layout(pad=0.4)
OUT = r"C:\Users\SSAFY\kpf-media-stats-competition\report\assets\fig_pipeline.png"
plt.savefig(OUT, bbox_inches="tight", facecolor="white")
print("저장 →", OUT)
