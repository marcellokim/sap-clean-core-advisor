import os
from dotenv import load_dotenv
from services.domain.joule_readiness_engine import generate_joule_gap_analysis

load_dotenv()

checked = ["BTP Global Account 인타이틀먼트 확인"]
unchecked = ["대상 시스템 버전 호환", "Joule 권한 분리", "SSO 연동"]

print("Calling AI...")
res = generate_joule_gap_analysis(checked, unchecked)
print(f"Risk: {res.risk_level}")
print(f"Summary: {res.executive_summary}")
print(f"Gaps: {res.identified_gaps}")
print(f"Actions: {res.recommended_actions}")
