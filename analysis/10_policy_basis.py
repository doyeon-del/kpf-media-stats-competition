"""정책 제안 근거 — 수용자 2023 허위조작정보(가짜뉴스) 대응 인식.
문84 대응방안 중요도 / 문85 책임 주체 / 문86 신뢰 하락 영향. 수용자 가중(HMWT). 유효 1~5.
실행: ./.venv/bin/python analysis/10_policy_basis.py
"""
import pyreadstat, pandas as pd, numpy as np
def valid(s): s=pd.to_numeric(s,errors="coerce"); return s.where(s.between(1,5))
def wmean(df,c,w="HMWT"):
    v=valid(df[c]); ww=pd.to_numeric(df[w],errors="coerce")
    m=v.notna()&ww.notna(); return np.average(v[m],weights=ww[m])
a,_=pyreadstat.read_sav("data/raw/audience_2023/2023 언론수용자 조사 DATA_통계표 등/2. 2023 언론수용자 조사_최종데이터(공개용).sav")

Q84={"팩트체크 기관 확보":"Q84_1","플랫폼 자율규제 강화":"Q84_2","미디어 리터러시 교육 확대":"Q84_3",
     "공적기구 설치·제도화":"Q84_4","피해자 구제제도 강화":"Q84_5","처벌 법규제 강화":"Q84_6"}
Q85={"정부":"Q85_1","정치인":"Q85_2","언론사":"Q85_3","플랫폼":"Q85_4","이용자":"Q85_5"}

d84=pd.DataFrame([{"대응방안":k,"중요도":round(wmean(a,v),3)} for k,v in Q84.items()]).sort_values("중요도",ascending=False)
d85=pd.DataFrame([{"책임주체":k,"책임도":round(wmean(a,v),3)} for k,v in Q85.items()]).sort_values("책임도",ascending=False)
m86=round(wmean(a,"Q86"),3)

pd.set_option("display.unicode.east_asian_width",True)
print("### 문84 · 허위조작정보 대응방안 중요도 (수용자 2023, 5점)")
print(d84.to_string(index=False))
print("\n### 문85 · 허위조작정보 책임 주체 (5점)")
print(d85.to_string(index=False))
print(f"\n### 문86 · 가짜뉴스가 언론 신뢰 하락에 미친 영향 = {m86}  (5점, 높을수록 영향 큼)")

d84.to_csv("data/processed/policy_q84_measures.csv",index=False,encoding="utf-8-sig")
d85.to_csv("data/processed/policy_q85_responsibility.csv",index=False,encoding="utf-8-sig")
print("\n저장: data/processed/policy_q84_measures.csv, policy_q85_responsibility.csv")
