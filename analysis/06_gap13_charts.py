"""GAP①·③ 덤벨 차트 — 기자 vs 수용자 인식 격차."""
import pandas as pd, matplotlib.pyplot as plt, numpy as np, matplotlib
matplotlib.rcParams["font.family"] = "AppleGothic"
matplotlib.rcParams["axes.unicode_minus"] = False

def dumbbell(df, lcol, rcol, label_l, label_r, cat, title, sortby, fname, xlim, xlabel):
    df = df.sort_values(sortby).reset_index(drop=True)
    y = np.arange(len(df))
    fig, ax = plt.subplots(figsize=(9, 0.7*len(df)+2))
    for i, r in df.iterrows():
        ax.plot([r[lcol], r[rcol]], [i, i], color="#cbd5e0", lw=2, zorder=1)
    ax.scatter(df[lcol], y, s=120, color="#2b6cb0", label=label_l, zorder=2)
    ax.scatter(df[rcol], y, s=120, color="#f6ad55", label=label_r, zorder=2)
    for i, r in df.iterrows():
        ax.text(r[lcol], i+0.18, f'{r[lcol]:.2f}', ha="center", fontsize=8, color="#2b6cb0")
        ax.text(r[rcol], i+0.18, f'{r[rcol]:.2f}', ha="center", fontsize=8, color="#c05621")
    ax.set_yticks(y); ax.set_yticklabels(df[cat]); ax.set_xlim(*xlim)
    ax.set_xlabel(xlabel); ax.set_title(title, fontsize=12, pad=10)
    ax.legend(loc="lower right", framealpha=0.9); ax.grid(axis="x", alpha=0.3)
    plt.tight_layout(); plt.savefig(fname, dpi=150); print("저장:", fname)

d1 = pd.read_csv("data/processed/gap1_5attr_2025.csv")
dumbbell(d1, "기자_자기평가", "수용자_평가", "기자(자기평가)", "수용자(평가)", "속성",
         "언론의 5속성: 기자 자기평가 vs 수용자 평가 (2025)\n— 기자가 더 박하다",
         "수용자_평가", "report/assets/gap1_5attr_2025.png", (2.3, 4.0),
         "5점 동의 (1 전혀~5 매우 그렇다)")

d3 = pd.read_csv("data/processed/gap3_problems_2023.csv")
dumbbell(d3, "수용자_심각성", "기자_심각성", "수용자(심각성)", "기자(심각성)", "문제점",
         "뉴스 문제점 심각성: 기자 vs 수용자 (2023)\n— 기자가 더 심각하게 본다",
         "기자_심각성", "report/assets/gap3_problems_2023.png", (3.3, 4.6),
         "5점 심각성 (1 전혀~5 매우 심각)")
