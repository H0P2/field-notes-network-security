# SecretFence — 공개 전 비밀값·연락처 패턴 점검기

SecretFence는 지정 폴더의 작은 텍스트 파일을 오프라인에서 검사해 자격 증명처럼 보이는 패턴과 일부 연락처 형식을 탐지합니다. 출력에는 원문 값 대신 파일 상대 경로·행·패턴 종류만 표시합니다. 검사 파일 수와 2MB 초과·바이너리·인코딩·심볼릭 링크·읽기 오류로 빠진 항목 수도 남깁니다.

## 실행

Python 3.10 이상:

```powershell
python .\secretfence.py C:\path\to\publish-folder --output .\scan-report.md
```

저장소가 Git으로 관리되고 `git` 명령을 쓸 수 있다면 커밋 이력도 선택적으로 검사할 수 있습니다:

```powershell
python .\secretfence.py C:\path\to\repository --git-history
```

현재 결과물 패키지의 실제 실행에서는 텍스트 패턴 검사와 Git 이력 접근 가능 여부를 각각 시도했습니다. 결과와 검사 범위는 [run-notes.md](run-notes.md), 최종 worktree 검사 기록은 [secretfence-release-scan.md](secretfence-release-scan.md)에 있습니다.

## 한계

정규식 패턴은 모든 자격 증명·개인정보 형식을 포괄하지 않습니다. 이미지·PDF·압축·난독화 파일, 무시 목록의 폴더, 2MB 초과 파일은 검사하지 않습니다. 0건은 비밀정보 부재의 증명이 아닙니다. Git 이력을 검사하지 못했으면 통과로 보지 않습니다.
