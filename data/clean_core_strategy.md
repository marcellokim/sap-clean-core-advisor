# SAP Clean Core Strategy Guide

## Clean Core란?

Clean Core는 SAP의 핵심 전략으로, ERP 시스템의 코어(Core)를 표준 상태로 유지하면서 확장(Extension)은 SAP Business Technology Platform(BTP)을 통해 수행하는 아키텍처 원칙이다.

## Clean Core의 3대 원칙

### 1. 표준 프로세스 우선 (Standard First)
- SAP Best Practice를 최대한 활용
- 커스텀 개발(Z-code) 최소화
- Fit-to-Standard 워크숍을 통해 표준 프로세스와의 갭(Gap) 분석 수행
- 표준으로 커버 가능한 영역은 반드시 표준 활용

### 2. 확장은 BTP에서 (Extend on BTP)
- Side-by-Side Extension 패턴 적용
- SAP Build, SAP Integration Suite 활용
- 코어 시스템에 직접 코드를 넣지 않고 BTP 위에서 확장
- Key User Extensibility로 비개발자도 확장 가능

### 3. 지속적 업데이트 (Continuous Update)
- Clean Core를 유지하면 SAP의 분기별/반기별 업데이트를 자동 적용 가능
- 커스텀 코드가 있으면 업데이트 시 충돌 발생 → 테스트/수정 비용 급증
- 클라우드 전환의 핵심 이점인 "상시 혁신(Evergreen)"을 실현

## Clean Core 도입 시 기대효과

| 항목 | 효과 |
|------|------|
| IT 운영 비용 | 평균 20-30% 절감 |
| 업그레이드 비용 | 최대 70% 절감 |
| 혁신 도입 속도 | 기존 대비 3-5배 빠름 |
| 기술 부채 | 점진적으로 0에 수렴 |

## 커스텀 코드 분류 체계

SAP는 커스텀 코드를 다음과 같이 분류하여 처리 방안을 제시한다:

### Retire (폐기)
- 더 이상 사용하지 않는 Z-code
- 실행 빈도 분석을 통해 식별
- 평균적으로 전체 커스텀 코드의 30-40%가 해당

### Replace (대체)
- SAP 표준 기능으로 대체 가능한 커스텀 코드
- SAP Fiori 앱, Standard API로 전환
- 약 20-30% 해당

### Retain & Refactor (유지 및 리팩토링)
- 비즈니스 필수이나 표준으로 대체 불가능한 코드
- ABAP Cloud로 리팩토링 또는 BTP로 이전
- 약 20-30% 해당

### Replatform (플랫폼 전환)
- BTP 상의 Side-by-Side Extension으로 재구축
- SAP CAP(Cloud Application Programming) 모델 활용

## Clean Core Compliance 체크리스트

1. **ABAP Custom Code 분석:** SAP Custom Code Migration Worklist 활용
2. **Simplification Item Check:** S/4HANA 전환 시 호환성 확인
3. **Business Function 활성화 현황:** 불필요한 기능 비활성화
4. **Interface 표준화:** RFC/BAPI에서 SAP API로 전환
5. **Output Management:** SAPscript/Smart Forms → Adobe Forms 또는 BTP Document Management
