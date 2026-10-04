# AuthSentry — Cowrie 인증 세션 집계기

AuthSentry는 Cowrie `session_aggregation.jsonl`의 세션별 `first_seen`, 익명 source 식별자, 실패·성공 로그인 횟수만 집계합니다. 비밀번호나 사용자명을 탐색·출력하지 않고 source는 보고서별 별칭으로 바꿉니다. 입력 크기와 SHA-256, 공개 원본, 표본 구간을 보고서에 남깁니다.

## 실행

Python 3.10 이상:

```powershell
python .\authsentry.py .\session_aggregation.jsonl.gz --source-url "https://zenodo.org/records/21260400" --sample-note "실제 입력 표본 범위"
```

압축을 푼 JSONL도 입력할 수 있습니다. `--output`으로 보고서 위치를 지정합니다.

## 실제 실행 결과와 한계

공개 Zenodo 자료의 실제 prefix에서 실행한 수치, 다운로드/입력 지문, 날짜 집계의 해석 제한은 [run-notes.md](run-notes.md)에 적었습니다. 익명 source를 쓴 결과는 [authsentry-cowrie-report.md](authsentry-cowrie-report.md)입니다.

실제 honeypot 관측 세션을 처리한 것이며 인터넷 전체 공격률이나 특정 네트워크의 위험도를 추정하지 않습니다. 로그인 시도 집계는 각 세션의 `first_seen` 날짜에 묶었으므로 사건 발생 시각별 변화로 해석하면 안 됩니다. 공개 prefix 표본은 전체 데이터셋을 대표하지 않습니다.
