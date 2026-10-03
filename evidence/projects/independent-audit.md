# 독립 재계산 기록

FlowLens/AuthSentry 분석기 코드를 import하지 않고 Python 표준 라이브러리로 입력 표본을 다시 읽었습니다.

## FlowLens

- 흐름 15,313건 / 잘못된 행 0건 / 전송량 157,353,488 bytes
- 라벨 계열: `{"Background": 15098, "From-Botnet": 128, "From-Normal": 86, "To-Normal": 1}`
- 미상 목적지 포트: 27건. 포트 `-`는 원본에 존재하며 FlowLens 규칙상 허용된 미상 값입니다.
- 상위 출발지 별칭: net-01 / 6,148 flows / 58,696,409 bytes
- 입력 SHA-256: `5cd759d17034728958dda09bc44a203f78e94832f8e18f80f32593509d83c57a`

## AuthSentry

- 세션 집계 58,334건 / 잘못된 행 0건
- 실패 53,602 / 성공 4,645 / source 6,511
- first_seen: 2025-06-27 - 2025-08-14 / 서로 다른 날짜 13개
- username/password 키가 포함된 레코드: 0건
- 입력 SHA-256: `6621c0f4c095fbd558c2366915d82fe15fb4888eebe33f854666a9e95ffc0df9`

## 교차 확인

PASS - FlowLens: 유효 흐름 수 15,313
PASS - FlowLens: 잘못된 행 0
PASS - FlowLens: 미상 목적지 포트 27개를 유효 행으로 보존
PASS - FlowLens: 전송량 합계 157,353,488 bytes
PASS - FlowLens: 제공자 라벨 계열 수 일치
PASS - FlowLens: 상위 출발지 별칭·흐름·bytes 일치
PASS - FlowLens: 입력 SHA-256이 보고서와 일치
PASS - FlowLens: 원본 구간 SHA-256 재계산 일치
PASS - AuthSentry: 세션 집계 레코드 58,334
PASS - AuthSentry: 잘못된 JSONL 행 0
PASS - AuthSentry: 실패/성공 로그인 합계 일치
PASS - AuthSentry: source 식별자 6,511개
PASS - AuthSentry: first_seen 날짜 범위/고유 날짜 수 일치
PASS - AuthSentry: username/password 키가 모든 표본 레코드에서 부재
PASS - AuthSentry: 분석 입력 SHA-256이 보고서와 일치
PASS - AuthSentry: 압축 원본 구간 SHA-256 재계산 일치
PASS - PublishGate manifest/report 지문 일치: flowlens-ctu13-mid-slice
PASS - PublishGate manifest/report 지문 일치: authsentry-cowrie-prefix

초기 빠른 대조는 `Dport`의 `-`를 잘못된 값으로 처리해 27행을 제외했습니다. 실제 parser 계약을 확인해 미상 포트를 유효하게 보존한 독립 재계산에서는 전체 수치가 보고서와 일치했습니다. 분석 결과 파일은 이 교차 확인 과정에서 바꾸지 않았습니다.

최종 판정: PASS - 보고서 수치와 SHA-256이 독립 재계산과 일치

제한: 두 분석 자료는 선택된 부분 구간입니다. 일치 검사는 입력/보고서 간 재현성과 값 확인이지 원본 데이터셋 전체에 대한 통계적 대표성을 뜻하지 않습니다.
