# Architecture Exceptions

리팩터링/정리 작업 중 아키텍처 불변조건 예외가 불가피할 때만 이 문서에 승인 항목을 기록합니다.
기본 원칙은 **예외 없음**이며, 이 문서에 유효한 항목이 없는 경우 예외는 승인되지 않은 것으로 간주합니다.

## Rules

- 적용 대상: 현재 리포지토리의 추적 코드/문서 변경. 로컬 에이전트 런타임 산출물은 예외 승인 근거로 사용하지 않습니다.
- 모든 항목은 아래 필드를 **모두** 포함해야 합니다.
- `Expiry Date`가 지난 항목은 즉시 정리하거나 연장 승인을 다시 받아야 합니다.
- `Alternative Path`는 예외 제거 후 복귀할 목표 경로를 명시합니다.

## Required Fields

- `Reason`
- `Owner`
- `Expiry Date`
- `Alternative Path`

## Approved Exceptions

현재 승인된 예외 없음.

| Exception ID | Invariant | Scope / File | Reason | Owner | Expiry Date | Alternative Path | Approved By | Tracking |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |

## Entry Template

```md
### EXC-YYYYMMDD-01
- Invariant: INV-01 | INV-02 | INV-03
- Scope / File: `path/to/file.py`
- Reason: <required>
- Owner: <required>
- Expiry Date: YYYY-MM-DD
- Alternative Path: <required>
- Approved By: <name or role>
- Tracking: <issue / PR / note>
```
