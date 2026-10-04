# PublishGate — 공개 증거 패키지 검증기

PublishGate는 실제 데이터 분석 보고서와 `evidence-manifest.json`의 출처·입력 범위·해시·기록 수·해석 한계가 서로 연결되는지 오프라인에서 확인합니다. 보고서가 패키지 내부에 있는지, 내려받은 원본 범위의 SHA-256과 분석기 입력 SHA-256을 보고서에 기록했는지, 보고서 파일 자체의 SHA-256이 manifest와 일치하는지 확인합니다. HTTPS 출처에 자격 증명·query·fragment가 들어가면 거부합니다.

## 실행

Python 3.10 이상:

```powershell
python .\publishgate.py .\evidence-manifest.json --output .\publishgate-report.md
```

`evidence-manifest.json`은 [FlowLens 실제 실행 보고서](../01-flowlens/flowlens-ctu13-report.md)와 [AuthSentry 실제 실행 보고서](../02-authsentry/authsentry-cowrie-report.md)의 관찰값과 파일 지문으로 작성했습니다.

## 검사 범위와 한계

실제 manifest에 적힌 두 보고서의 무결성과 provenance 필드가 일치하는지 검사합니다. 원본 데이터 다운로드를 다시 하거나 보고서 수치를 원시 데이터에서 독립 재계산하지 않습니다. manifest와 해시는 변경 여부·연결성 확인이지 외부기관의 서명이나 분석의 진실성 증명은 아닙니다. 브라우저에서 공개 주소·접근성·키보드 동작을 확인하지 않습니다.

## 실제 실행 기록

실제 보고서 두 개로 수행한 실행, 처음 발견한 인코딩·개행 해시 오류와 수정 후 결과는 [run-notes.md](run-notes.md)에 남겼습니다. 통과 결과는 [publishgate-report.md](publishgate-report.md)입니다.
