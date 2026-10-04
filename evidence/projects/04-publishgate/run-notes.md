# PublishGate — 실제 증거 패키지 실행 기록

## 입력과 실행

- 입력: `evidence-manifest.json`에 기록된 실제 FlowLens/CTU-13 보고서 15,313행과 AuthSentry/Cowrie 보고서 58,334 세션 집계
- 포함된 입력 출처·원본 바이트 구간 지문·분석기 입력 지문은 각 프로젝트의 `run-notes.md`와 실제 보고서를 참조합니다. manifest의 보고서 SHA-256은 실행 직전에 실제 저장 파일에서 계산했습니다.
- 실행: `python publishgate.py evidence-manifest.json --output publishgate-report.md`
- 최종 관찰: 두 보고서 모두 PASS. SHA-256, 입력 파일 크기/지문, 원본 구간 지문, 공개 출처 URL, 표본 범위, 제한 문구, 비식별화 표시가 일치했습니다.

## 실제 결함과 수정

- 첫 실제 실행: Windows 기본 콘솔 인코딩이 제목의 긴 대시 문자를 출력하지 못해 `UnicodeEncodeError`로 끝났습니다. 제목 문자를 ASCII 하이픈으로 바꾼 뒤 출력했습니다.
- 다음 실제 실행: 두 보고서의 SHA-256 검사가 실패했습니다. 해시 manifest는 디스크의 CRLF 포함 바이트를 기준으로 만들었는데, 검증기는 UTF-8 텍스트를 다시 인코딩하면서 개행을 정규화해 서로 다른 바이트열을 비교했습니다. 파일 원시 바이트의 해시와 별도 UTF-8 텍스트 해석을 사용하도록 고친 뒤 재실행해 둘 다 통과했습니다.
- 실행 근거: [최종 PublishGate 결과](publishgate-report.md)와 [실제 manifest](evidence-manifest.json)

## 판단 출처와 제한

- AI가 수행한 일: 실제 분석 보고서에서 manifest를 만들고, 검증기 구현·실행·두 결함 수정·최종 재실행을 했습니다.
- 사용자가 직접 내린 기준: 사용자 피드백은 네 실험 뒤 받을 예정이므로 아직 받지 않았습니다. 해시, URL 형식, 비식별화 확인 규칙은 도구 구현 선택이지 사용자의 정책 결정으로 기록하지 않습니다.
- 따르지 않은 초기 접근: 빈 프로필 양식과 합성 JSON 통과/실패 시나리오는 사용하지 않기로 하고, 두 실데이터 보고서의 실제 provenance와 무결성 확인으로 전환했습니다.
- PublishGate는 manifest 값과 보고서 간 연결성만 확인합니다. 원시 데이터가 공개 패키지에 없으므로 수치를 원시 레코드에서 재계산하거나 외부 출처의 서명을 검증하지는 않습니다.
