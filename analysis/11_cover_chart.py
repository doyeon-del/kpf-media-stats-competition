"""표지용 대표 비주얼 — 권력 감시(정부·공인 감시) 이상-체감 격차의 3개년 고착.
Figma 레이아웃용: 제목/헤드라인은 비워두고(디자인에서 타이포), 그래프+주석만. 고해상도 300dpi.
입력: data/processed/ts_gap2_roles.csv
실행: ./.venv/bin/python analysis/11_cover_chart.py
"""
import pandas as pd, matplotlib.pyplot as plt, matplotlib
matplotlib.rcParams["font.family"] = "AppleGothic"
matplotlib.rcParams["axes.unicode_minus"] = False

YEARS = ["2021", "2023", "2025"]
ORDER = ["정부감시", "약자대변", "기업감시", "정확정보", "의제설정", "다양의견", "해결책"]
LABEL = {"정부감시": "정부·공인 감시", "약자대변": "사회적 약자 대변", "기업감시": "기업활동 감시",
         "정확정보": "정확한 정보제공", "의제설정": "의제 설정", "다양의견": "다양한 의견", "해결책": "해결책 제시"}
HOT = "#1a4e8a"     # 강조(권력 감시)
GREY = "#d3dae2"    # 나머지

d = pd.read_csv("data/processed/ts_gap2_roles.csv", dtype={"연도": str})
piv = d.pivot(index="역할", columns="연도", values="중요도−체감").reindex(ORDER)[YEARS]

fig, ax = plt.subplots(figsize=(10, 6.5))
x = range(len(YEARS))
for role, row in piv.iterrows():
    hot = role == "정부감시"
    ax.plot(x, row.values, marker="o", markersize=9 if hot else 6,
            lw=4 if hot else 1.5, color=HOT if hot else GREY,
            zorder=5 if hot else 1)
    if hot:
        # 강조선: 각 연도 값 라벨 + 역할명
        for xi, val in zip(x, row.values):
            ax.annotate(f"{val:.2f}", (xi, val), textcoords="offset points",
                        xytext=(0, 12), ha="center", fontsize=12, fontweight="bold", color=HOT)
        ax.text(x[-1] + 0.06, row.values[-1], f"  {LABEL[role]}", va="center",
                fontsize=13, fontweight="bold", color=HOT)
    else:
        ax.text(x[-1] + 0.06, row.values[-1], f"  {LABEL[role]}", va="center",
                fontsize=9.5, color="#8a97a6")

# 고착 강조: 권력 감시 밴드
ax.axhspan(1.25, 1.45, color=HOT, alpha=0.05, zorder=0)
ax.set_xticks(list(x)); ax.set_xticklabels(YEARS, fontsize=13)
ax.set_xlim(-0.12, len(YEARS) - 1 + 1.15)
ax.set_ylim(0.35, 1.55)
ax.set_ylabel("이상-체감 격차 (기자 중요도 - 수용자 체감, 5점)", fontsize=11, color="#5a6472")
ax.spines[["top", "right"]].set_visible(False)
ax.tick_params(colors="#5a6472")
ax.grid(axis="y", alpha=0.25)
plt.tight_layout()
plt.savefig("report/assets/cover_watchdog_gap.png", dpi=300, bbox_inches="tight")
print("저장: report/assets/cover_watchdog_gap.png (300dpi, 표지용)")
