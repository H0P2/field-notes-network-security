# AuthSentry — 실제 데이터 실행 기록

## 입력과 출처

- 원본: [Zenodo Cowrie honeypot session aggregation](https://zenodo.org/records/21260400) (`session_aggregation.jsonl.gz`)
- 압축 원본의 실제 prefix bytes `0-2097151`: 2,097,152 bytes, SHA-256 `eadeb1736a3e36cd2547d2576a0e27f2acda14dd67fd5d946ac476bc45a3cf5a`.
- gzip 해제 후 끝의 불완전한 JSONL 행을 제외한 실제 입력: 35,410,664 bytes, SHA-256 `6621c0f4c095fbd558c2366915d82fe15fb4888eebe33f854666a9e95ffc0df9`.
- 다운로드는 데이터셋 전체가 아닌 첫 2MiB 압축 구간만 요청했습니다. 이 prefix의 세션 `first_seen`은 2025-06-27부터 2025-08-14까지 나타나며 중간 날짜가 모두 포함된 연속 관측 기간은 아닙니다.

## 실행 관찰

- 유효 세션 집계 58,334건, 제외 0건
- 실패 로그인 합계 53,602건, 성공 로그인 합계 4,645건, source 식별자 6,511개
- 세션 집계 JSONL에서 `username`·`password` 키는 이 prefix의 58,334개 레코드 어디에도 없었습니다. 프로그램은 `first_seen`, `src_ip`, `cnt_login_failed`, `cnt_login_success`만 결과에 사용하며 source 원문은 보고서 별칭으로 바꿉니다.
- 보고서 날짜 합계는 세션 집계 횟수를 `first_seen` 날짜에 귀속합니다. 4,645는 Cowrie honeypot에서 세션 집계된 successful login event 수이지 실제 서비스의 침해 건수라는 뜻이 아닙니다.

## 실제 결함과 수정

- 첫 실행 보고서에는 입력 파일 지문과 공개 출처·선택 표본 설명이 없었습니다. 수정 후 AuthSentry가 입력 바이트 수와 SHA-256, 출처 URL, 표본 범위를 내보내도록 했고 같은 실제 JSONL prefix를 재실행했습니다.
- 실행 결과가 전체 Zenodo 자료를 다룬 듯 보일 위험을 확인했습니다. README와 보고서에 표본 범위와 honeypot 관측 한계를 명시했습니다.
- 후속 독립 대조: 분석기 코드를 import하지 않고 JSONL 레코드 수·로그인 합계·고유 source 수·날짜 범위·credential key 부재·입력 SHA-256을 다시 계산했습니다. 보고서와 manifest 값이 모두 일치했습니다. 상세 판정은 [독립 대조 기록](../independent-audit.md)에 있습니다.

## 판단 출처와 제한

- AI가 수행한 일: 공식 공개 데이터의 실제 일부를 받고 AuthSentry를 구현·실행해 집계·해시를 기록했습니다.
- 사용자가 직접 내린 기준: 사용자 피드백은 네 실험 후 받을 예정이므로 아직 받지 않았습니다. 보고서 상위 표시 기본값 20은 도구 옵션일 뿐 사용자의 판단이 아닙니다.
- 따르지 않은 초기 접근: 합성 로그인 이벤트 초안은 실제 증거에서 제외하고 공개 honeypot 자료의 실제 JSONL로 대체했습니다.
- 2MiB 압축 prefix만 처리했으며 전체 1.3GB 파일을 받지 않았습니다. 보고서는 원본 IP·계정·비밀번호 원문을 공개하지 않습니다.
