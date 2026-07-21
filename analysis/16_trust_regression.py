# -*- coding: utf-8 -*-
"""언론 신뢰의 결정 요인 — 가중 회귀 (수용자 2025 단일 자료).

DV : Q87_1 뉴스·시사정보 전반 신뢰도 (5점)   [대안 DV: Q85_1~5 언론 5속성 평균]
IV : Q86_1~7 역할별 수행 체감 (5점)
W  : WT (설계가중) · 표준화 β · HC1 robust SE
관심: 감시 3역할(Q86_5·6·7)의 β가 상위권인가.
"""
import sys, glob, os
import numpy as np
import pandas as pd
import pyreadstat
import statsmodels.api as sm
from statsmodels.stats.outliers_influence import variance_inflation_factor

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_HERE = os.path.dirname(os.path.abspath(__file__))
SAV = glob.glob(os.path.join(os.path.dirname(_HERE), "data", "raw", "audience_2025", "*.SAV"))[0]

ROLES = {"Q86_1": "정확한 정보 제공", "Q86_2": "다양한 의견 제시", "Q86_3": "해결책 제시",
         "Q86_4": "의제 설정", "Q86_5": "정부·공인 감시", "Q86_6": "기업 감시", "Q86_7": "약자 대변"}
WATCH = {"Q86_5", "Q86_6", "Q86_7"}

df, meta = pyreadstat.read_sav(SAV)
w = df["WT"].to_numpy()

def wz(s, w):
    """가중 표준화."""
    m = np.average(s, weights=w)
    sd = np.sqrt(np.average((s - m) ** 2, weights=w))
    return (s - m) / sd

def run(dv_name, y_raw, tag):
    X = pd.DataFrame({c: wz(df[c].to_numpy(), w) for c in ROLES})
    y = wz(y_raw, w)
    model = sm.WLS(y, sm.add_constant(X), weights=w).fit(cov_type="HC1")
    out = pd.DataFrame({
        "역할": [ROLES[c] for c in ROLES],
        "β(표준화)": [model.params[c] for c in ROLES],
        "p": [model.pvalues[c] for c in ROLES],
    }).sort_values("β(표준화)", ascending=False).reset_index(drop=True)
    out["감시군"] = ["★" if c in WATCH else "" for c in
                   sorted(ROLES, key=lambda c: -model.params[c])]
    print(f"\n{'='*62}\n[{tag}] DV = {dv_name}  (n={len(df):,}, 가중 WLS, HC1)\n{'='*62}")
    for _, r in out.iterrows():
        sig = "***" if r["p"] < .001 else "**" if r["p"] < .01 else "*" if r["p"] < .05 else ""
        print(f"  {r['감시군']:2}{r['역할']:12} β = {r['β(표준화)']:+.3f} {sig:3} (p={r['p']:.3g})")
    print(f"  R² = {model.rsquared:.3f}")
    return out

# 주 분석
main = run("Q87_1 뉴스·시사정보 전반 신뢰도", df["Q87_1"].to_numpy(), "주 분석")

# 대안 DV (강건성)
alt_y = df[[f"Q85_{i}" for i in range(1, 6)]].mean(axis=1).to_numpy()
alt = run("언론 5속성 평균(Q85_1~5)", alt_y, "대안 DV")

# 다중공선성
X = pd.DataFrame({c: wz(df[c].to_numpy(), w) for c in ROLES})
Xc = sm.add_constant(X)
print("\nVIF (10 미만이면 통상 허용):")
for i, c in enumerate(ROLES):
    print(f"  {ROLES[c]:12} {variance_inflation_factor(Xc.to_numpy(), i+1):.2f}")

# 가중 단순상관 (참고)
print("\n가중 단순상관 r (DV=Q87_1):")
y = wz(df["Q87_1"].to_numpy(), w)
for c in ROLES:
    x = wz(df[c].to_numpy(), w)
    print(f"  {ROLES[c]:12} r = {np.average(x*y, weights=w):+.3f}")

# ── 보고서 3.5절 주 지표: 극단집단 t검정 + Cohen's d ──────────────────
# 감시군 3역할 평균 체감 상(≥4) vs 하(≤2) 집단의 전반 신뢰도(Q87_1) 차이.
from scipy import stats
yv = df["Q87_1"]
watch3 = df[["Q86_5", "Q86_6", "Q86_7"]].mean(axis=1)
print("\n극단집단 비교 (보고서 3.5절 주 지표 — d는 상·하 극단집단 기준임을 명시할 것):")
for name, g in [("감시군 체감", watch3), ("정보 제공 체감", df["Q86_1"])]:
    a, b = yv[g >= 4], yv[g <= 2]
    t, p = stats.ttest_ind(a, b, equal_var=False)
    sp = np.sqrt(((len(a)-1)*a.std(ddof=1)**2 + (len(b)-1)*b.std(ddof=1)**2) / (len(a)+len(b)-2))
    print(f"  {name:9} 상(n={len(a):,}) {a.mean():.2f} vs 하(n={len(b):,}) {b.mean():.2f} "
          f"| t={t:.1f}, p={p:.2g}, d={(a.mean()-b.mean())/sp:.2f}")
