"""W2-3: 2025 7역할 3각비교 가로 막대 차트."""
import pandas as pd, matplotlib.pyplot as plt, numpy as np
import matplotlib

matplotlib.rcParams["font.family"] = "AppleGothic"
matplotlib.rcParams["axes.unicode_minus"] = False

df = pd.read_csv("data/processed/triangle_2025.csv")
df = df.sort_values("격차_중요도−체감", ascending=True).reset_index(drop=True)

y = np.arange(len(df)); h = 0.26
fig, ax = plt.subplots(figsize=(10, 6.2))
ax.barh(y + h, df["기자_중요도"],    h, label="기자: 중요하다",       color="#2b6cb0")
ax.barh(y,      df["기자_실천인식"], h, label="기자: 실제 수행한다", color="#63b3ed")
ax.barh(y - h, df["수용자_수행체감"], h, label="수용자: 잘한다고 체감", color="#f6ad55")

ax.set_yticks(y); ax.set_yticklabels(df["역할"])
ax.set_xlim(2.5, 4.8); ax.set_xlabel("5점 평균 (1 전혀~5 매우)")
ax.set_title("언론의 7개 역할: 기자가 중시하는 것 vs 실제 수행 vs 수용자 체감 (2025)",
             fontsize=13, pad=12)
ax.legend(loc="lower right", framealpha=0.9)
ax.grid(axis="x", alpha=0.3)
for i, r in df.iterrows():
    ax.text(r["기자_중요도"] + 0.02, i + h, f'{r["기자_중요도"]:.2f}', va="center", fontsize=8)
    ax.text(r["수용자_수행체감"] + 0.02, i - h, f'{r["수용자_수행체감"]:.2f}', va="center", fontsize=8)
plt.tight_layout()
plt.savefig("report/assets/triangle_2025.png", dpi=150)
print("저장: report/assets/triangle_2025.png")
