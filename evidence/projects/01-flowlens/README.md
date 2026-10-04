# FlowLens — 네트워크 흐름 분석기

FlowLens는 Argus 형식의 네트워크 흐름 CSV를 로컬에서 분석합니다. 실제 공개 CTU-13 capture의 `StartTime`, 주소, 포트, 프로토콜, 바이트 수, 제공자 라벨을 읽고 프로토콜·목적지 포트·흐름량을 집계합니다. 보고서는 네트워크 주소 대신 흐름량 순 별칭을 출력하고 입력 SHA-256과 출처·표본 범위를 기록합니다.

## 실행

Python 3.10 이상:

```powershell
python .\flowlens.py .\capture-slice.binetflow --source-url "https://mcfp.felk.cvut.cz/publicDatasets/CTU-Malware-Capture-Botnet-42/detailed-bidirectional-flow-labels/capture20110810.binetflow" --sample-note "실제 입력 표본 범위 설명"
```

`--output`으로 보고서 경로를 지정할 수 있습니다. `--show-addresses`는 입력 주소를 공개하므로 공개 자료에는 사용하지 마세요.

## 실제 실행 결과와 한계

실제 데이터 구간으로 실행한 수치, 출처 해시, 표본 선택 과정, 발견한 결함과 수정 내역은 [run-notes.md](run-notes.md)에 기록했습니다. 재현 가능한 익명화 보고서는 [flowlens-ctu13-report.md](flowlens-ctu13-report.md)입니다.

이 실행은 원본 파일 전체가 아니라 선별된 바이트 구간에서 완전한 행을 추린 표본을 사용했습니다. 그러므로 전체 capture의 트래픽 비율·공격 비율을 추정하지 않습니다. 데이터 제공자의 라벨은 판정 근거가 아니라 원본 분류이며, `To-Botnet`/`To-Normal`은 해당 호스트를 향한 흐름입니다. 이 데이터에는 방화벽 action 열이 없으므로 차단 집중 분석을 하지 않았습니다.

## 검사 범위

이 도구는 파일만 읽으며 패킷 수집이나 네트워크 연결을 하지 않습니다. 값 검증에 실패한 행은 원문 대신 행 번호만 기록합니다. 기본 보고서는 IP 주소를 내보내지 않지만 별칭도 동일 대역의 흐름을 묶어 보여줄 뿐 완전한 익명성을 보장하지 않습니다.
