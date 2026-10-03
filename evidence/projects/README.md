# 네트워크·보안·개발 실험 결과

개인 소개 사이트에 앞서 요청한 중급 이상 프로젝트 네 가지를 공개 실데이터나 현재 결과물 패키지로 실행하고, 독립 재계산까지 마쳤습니다. 합성 입력·시연용 숫자를 결과 근거로 사용하지 않았습니다. 프로필 문안은 사용자가 확인할 수 있도록 별도 초안으로 만들고, 사용자 선택으로 확인되지 않은 개인 사실은 채우지 않았습니다.

## 프로젝트

1. [FlowLens — 네트워크 흐름 분석기](01-flowlens/README.md): CTU-13 Botnet Capture 42 실제 일부 구간 15,313개 흐름을 처리했습니다. 표본 선택 때문에 전체 공격률을 추정하지 않습니다.
2. [AuthSentry — Cowrie 세션 집계기](02-authsentry/README.md): Zenodo의 실제 `session_aggregation.jsonl.gz` prefix에서 세션 집계 58,334건을 처리했습니다. honeypot 관측이며 전체 인터넷을 대표하지 않습니다.
3. [SecretFence — 공개 전 비밀값 점검기](03-secretfence/README.md): 이 결과물 폴더를 스캔해 지정 텍스트 패턴과 검사 범위를 기록했습니다. Git 이력 상태는 별도 결과에 분명히 표시합니다.
4. [PublishGate — 증거 패키지 검증기](04-publishgate/README.md): FlowLens/AuthSentry의 실제 보고서와 출처·SHA-256 manifest를 교차 확인했습니다.

## 진행 경계

네 프로젝트는 코드 작성뿐 아니라 입력 출처·범위, 실제 실행 결과, 한계, 발견한 실제 결함과 수정 기록을 포함합니다. 정적 사이트 초안은 `../portfolio-site/index.html`에 있습니다. 공개 배포 전에는 사용자가 소개 문안·공개 범위·대상을 검토하고 공개 호스팅/소스 위치를 정해야 합니다.

## 독립 대조

분석기 코드를 import하지 않은 별도 집계로 실제 입력 표본을 다시 계산했습니다. FlowLens·AuthSentry의 핵심 수치, 입력 해시, 보고서 manifest가 일치했습니다. FlowLens의 `Dport`가 `-`인 27행은 허용된 미상 포트였고 유효 행으로 포함했습니다. [독립 대조 코드](independent-audit.py) · [결과](independent-audit.md)

## 2026-10-02 추가 실험과 재검토

5. [SampleScope — 세 구간 비교](05-samplescope/samplescope-report.md): 같은 원본의 비무작위 구간 46,023행을 비교하고 표본 선택의 영향을 기록했습니다.

[재검토 결과와 수정 내역](review-2026-10-02.md)
