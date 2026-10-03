# 실제 프로젝트 경험 기록

이 기록은 현재 대화에서 AI가 수행한 실제 실험의 입력·도구 동작·측정 결과를 정리합니다. 사용자가 직접 실행하거나 판단한 경험으로 바꾸어 쓰지 않았습니다. 사용자 피드백은 네 실험을 모두 마친 뒤 요청합니다.

## FlowLens

- 실제 입력: 공개 CTU-13 Capture 42의 비연속 바이트 구간에서 추린 완전한 CSV 행
- 관찰: 15,313 흐름, 잘못된 행 0건, 157,353,488 bytes
- 실제 수정: 대역 별칭을 흐름량 순으로 정렬, 보고서에 입력/원본 구간 SHA-256 및 선택 표본 제한 추가
- 자세한 기록: [run-notes.md](01-flowlens/run-notes.md)

## AuthSentry

- 실제 입력: 공개 Cowrie 세션 집계 gzip 파일의 2MiB prefix를 풀고 불완전한 JSONL 마지막 행을 제외한 자료
- 관찰: 세션 집계 58,334건, 실패 이벤트 53,602, 성공 이벤트 4,645, 잘못된 행 0건
- 실제 수정: 보고서에 입력 지문·원본 지문·출처·표본 범위 추가, honeypot/first_seen 한계 표시
- 자세한 기록: [run-notes.md](02-authsentry/run-notes.md)

## 독립 재검토

- 별도 Python 스크립트에서 분석기 코드를 불러오지 않고 실제 두 입력 표본을 다시 집계했습니다.
- 핵심 레코드 수·합계·라벨·입력 해시·manifest 일치: 모두 통과
- FlowLens의 목적지 포트 `-` 27개는 도구가 허용하는 미상 값으로 처리했습니다.
- 코드: [independent-audit.py](independent-audit.py) · 결과: [independent-audit.md](independent-audit.md)

## SecretFence

- 실제 입력: 이 결과물 폴더의 코드·문서·실제 분석 보고서
- 최종 관찰: [실제 스캔 보고서](03-secretfence/secretfence-release-scan.md)에 21개 파일 검사, 패턴 0건, 제외/오류 0건으로 기록
- 자세한 기록: [run-notes.md](03-secretfence/run-notes.md)

## PublishGate

- 실제 입력: FlowLens/AuthSentry 실제 보고서, 각 입력 해시 및 manifest
- 최종 관찰: 실제 보고서 2개 검증 통과
- 실제 수정: Windows 콘솔 출력 문자와 CRLF 원시 바이트 SHA-256 비교 결함
- 자세한 기록: [run-notes.md](04-publishgate/run-notes.md)

## 독립 대조

- FlowLens와 AuthSentry 분석기 코드를 불러오지 않은 별도 집계로 원본 표본을 다시 계산했습니다.
- 핵심 레코드 수·합계·라벨·해시·manifest 값이 모두 일치했습니다. FlowLens 미상 포트 27건은 유효 행으로 처리했습니다.
- 코드: [independent-audit.py](independent-audit.py) · 결과: [independent-audit.md](independent-audit.md)

## 사용자 판단

사용자는 실험이 모두 끝난 뒤 결과의 신빙성과 공개 적절성에 피드백을 주기로 했습니다. 개인 소개 페이지의 대상·공개 정보·근거 선택은 아직 작성하지 않았습니다.
