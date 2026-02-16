# Joule Troubleshooting (KO)

## 공통 이슈
1. 인증 실패
- 점검: API 키/권한/역할 매핑
- 조치: 권한 재부여, 키 재발급

2. 응답 지연
- 점검: 재시도 설정, 네트워크, 쿼터
- 조치: timeout/retry 조정, fallback 강제

3. 근거 미표시
- 점검: rule_reference_map, source catalog
- 조치: 규칙-출처 매핑 누락 보완
