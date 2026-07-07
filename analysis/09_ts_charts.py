"""발견④ 시계열 차트 — 격차의 3개년 추세(2021·2023·2025).
① 5속성 기자-수용자 격차 추세  ② 역할 이상-체감 격차 추세(권력 감시 강조).
입력: data/processed/ts_gap1_5attr.csv, ts_gap2_roles.csv
실행: ./.venv/bin/python analysis/09_ts_charts.py
"""
import pandas as pd, matplotlib.pyplot as plt, matplotlib
matplotlib.rcParams["font.family"] = "AppleGothic"
matplotlib.rcParams["axes.unicode_minus"] = False

YEARS = ["2021", "2023", "2025"]
GREY = "#cbd5e0"

def trendlines(df, cat, valcol, order, highlight, title, ylabel, fname, zero=False):
    piv = df.pivot(index=cat, columns="연도", values=valcol).reindex(order)[[*map(str, YEARS)]]
    fig, ax = plt.subplots(figsize=(8, 5.5))
    x = range(len(YEARS))
    for name, row in piv.iterrows():
        hot = name in highlight
        ax.plot(x, row.values, marker="o", lw=3 if hot else 1.6,
                color=None if hot else GREY, zorder=3 if hot else 1,
                alpha=1 if hot else 0.8, label=name if hot else None)
        # 끝점 라벨(강조 항목만)
        if hot:
            ax.text(x[-1] + 0.05, row.values[-1], f" {name} {row.values[-1]:+.2f}",
                    va="center", fontsize=9, fontweight="bold")
        else:
            ax.text(x[-1] + 0.05, row.values[-1], f" {name}", va="center",
                    fontsize=8, color="#718096")
    if zero:
        ax.axhline(0, color="#a0aec0", lw=1, ls="--")
    ax.set_xticks(list(x)); ax.set_xticklabels(YEARS)
    ax.set_xlim(-0.15, len(YEARS) - 0.15 + 0.9)
    ax.set_ylabel(ylabel); ax.set_title(title, fontsize=12, pad=10)
    ax.grid(axis="y", alpha=0.3)
    plt.tight_layout(); plt.savefig(fname, dpi=150); print("저장:", fname)

# ① 5속성 격차 추세 (음수 = 기자가 더 박함)
d1 = pd.read_csv("data/processed/ts_gap1_5attr.csv", dtype={"연도": str})
trendlines(d1, "속성", "격차(기자−수용자)",
           ["전문", "공정", "정확", "자유", "영향력"], {"전문", "공정"},
           "5속성 격차의 3개년 추세 (기자 자기평가 - 수용자 평가)\n— 값이 계속 음수: 기자가 매년 더 박하다",
           "격차 (기자-수용자, 5점)", "report/assets/ts_gap1_5attr.png", zero=True)

# ② 역할 이상-체감 격차 추세 (양수 = 수용자가 덜 체감)
d2 = pd.read_csv("data/processed/ts_gap2_roles.csv", dtype={"연도": str})
trendlines(d2, "역할", "중요도−체감",
           ["정부감시", "약자대변", "기업감시", "정확정보", "의제설정", "다양의견", "해결책"],
           {"정부감시"},
           "역할별 이상-체감 격차의 3개년 추세 (기자 중요도 - 수용자 체감)\n— 권력 감시 격차가 매년 최대로 고착",
           "격차 (중요도-체감, 5점)", "report/assets/ts_gap2_roles.png")
