# SAP Clean Core Advisor

[![CI](https://github.com/marcellokim/sap-clean-core-advisor/actions/workflows/ci.yml/badge.svg)](https://github.com/marcellokim/sap-clean-core-advisor/actions/workflows/ci.yml)

Portfolio project for **SAP STAR Program (Enterprise Architect Support)**.

This tool helps create customer-facing EA outputs quickly, with deterministic KPI calculation and AI-assisted narrative generation.

---

## 1) Why this project (STAR role fit)

| STAR EA Support responsibility | Project evidence |
|---|---|
| 1. EA cookbook / customer documentation | PDF output + EA cookbook templates (`docs/ea-cookbook/*`) |
| 2. Translation / interpretation support in meetings | KO/EN workshop agenda, script, glossary (`docs/workshop-kit/*`) |
| 3. AI adoption support (e.g., Joule activation) | Joule readiness checklist + troubleshooting playbook (`docs/joule-playbook/*`) |
| 4. Team ad-hoc operations support | Weekly status / precheck / QA checklist (`docs/ops-toolkit/*`) |

---

## 2) What the app does

### A. Clean Core Assessment
- Deterministic calculation of:
  - Clean Core score
  - Current vs target TCO
  - 3-year savings estimate
  - Risk level and factors
- Recommendation list + evidence ledger
- Executive summary + detailed report
- PDF export (soft-fail safe)

### B. Joule Readiness Gap Analysis
- Readiness checks for S/4HANA Private Cloud + Joule adoption
- Gap-based actions and risk guidance

### C. EA Support Pack
- Downloadable practical docs (KO/EN) for real customer workshops

---

## 3) Architecture (summary)

```text
Input Form
 -> Ruleset Resolution (generated > industry > base)
 -> Deterministic Calculator (Score/TCO/Risk)
 -> RAG Context (optional, soft-fail)
 -> LLM Report (optional, fallback)
 -> Evidence Ledger
 -> PDF Render (soft-fail)
 -> Streamlit UI
```

**Design principles**
- Deterministic-first KPI engine
- Soft-fail reliability (service still works even when AI/PDF steps fail)
- Traceability via evidence ledger

---

## 4) Quick start

### Prerequisites
- Python 3.13+
- [uv](https://docs.astral.sh/uv/)

### Install
```bash
uv sync
```

### Run
```bash
make run
# or
uv run streamlit run app.py
```

---

## 5) Quality gates

```bash
make test
make verify-sources
```

- `make test`: unit tests
- `make verify-sources`: source catalog schema + staleness checks

---

## 6) Demo flow (2-3 minutes, no video needed)

1. Enter customer profile (industry / ERP / DB / users / custom code)
2. Show KPI outputs (Score / TCO / Risk)
3. Show recommendations + evidence ledger
4. Export PDF report
5. Download EA support pack docs from sidebar

---

## 7) Repository guide

### App
- `app.py` - Streamlit entry
- `services/application/analysis_runner.py` - policy-driven orchestration
- `services/cost_calculator.py` - deterministic KPI logic
- `services/domain/*` - recommendations, evidence, validation

### Documents (portfolio evidence)
- `docs/ea-cookbook/*`
- `docs/workshop-kit/*`
- `docs/joule-playbook/*`
- `docs/ops-toolkit/*`

### Engineering appendix
- `docs/engineering/ARCHITECTURE_APPENDIX.md`

---

## 8) Interview talking points (recommended)

- Why deterministic-first is critical for enterprise trust
- How fallback design protects customer experience
- How evidence ledger improves explainability for EA decisions
- How the project supports both technical and customer-facing EA tasks

---

## 9) Korean summary (간단 요약)

이 프로젝트는 SAP STAR Program의 Enterprise Architect Support 역할에 맞춰,
- 고객 문서화(쿠크북/PDF),
- 워크샵 운영 보조(한/영 아젠다·스크립트·용어집),
- Joule 도입 지원 체크리스트,
- 팀 운영 템플릿
을 실제 산출물 중심으로 제공합니다.

핵심은 **정량 지표의 결정론적 계산 + AI 소프트페일 설계 + 근거 추적(Evidence Ledger)** 입니다.

---

## 10) References

### Official
- https://support.sap.com/en/offerings-programs/strategy.html
- https://www.sap.com/products/erp/rise/methodology/clean-core.html
- https://help.sap.com/doc/bb0e7ba5158c424ab7ce010228bf1de1

### SAP Community
- https://community.sap.com/t5/enterprise-resource-planning-blog-posts-by-sap/setup-and-activation-guide-joule-in-sap-s-4hana-private-cloud/ba-p/14325221
- https://community.sap.com/t5/enterprise-resource-planning-blog-posts-by-sap/clean-core-extensibility-balancing-standardization-and-differentiation/ba-p/14260149
