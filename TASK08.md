# 과제8 인증 구현 설명서 — 2026-10-14 3D 개편

FIELD NOTES의 기존 관심 분야·실제 프로젝트·검토 기준을 유지하고 공개 화면을 3D 탐색형 자기소개로 개편했다. 사용자 승인으로 과제8 결과물을 직접 수정한다. 패스키는 기존 Sites 인증 영역으로 연결하며 인증 서버·계정·키·자료를 변경하지 않는다. 실제 발행과 제출 상태는 별도 접수 기록으로 확인한다.

결과물 URL: https://h0p2.github.io/field-notes-network-security/  
소스 URL: https://github.com/H0P2/field-notes-network-security  
기존 실제 인증 영역: https://hope-passkey-portfolio.mo990025.chatgpt.site/#private

## ① 무엇으로 붙였나

패스키 인증은 WebAuthn과 SimpleWebAuthn을 사용한다. 기존 Sites v3의 서버가 등록·로그인 검증, 서버 세션, 비공개 자료 소유권을 처리한다. 구현 설명에 따르면 challenge는5분·한 번 소비, 세션은1시간이며 브라우저 쿠키는 HttpOnly·SameSite=Strict·HTTPS Secure, 서버에는 세션값의 SHA-256 해시를 저장한다. 공개 소개 GitHub Pages와 인증 Sites는 서로 다른 origin이다. Pages 메뉴에서 Sites로 이동하는 링크이며 통합세션·쿠키 자동전달·동일origin 인증이라고 표현하지 않는다. Worker·RP ID·쿠키·CSP는 변경하지 않는다.

현재 hope_lab의 밥도둑은 사용자가 iPhone 암호 앱에서 확인해 Apple 암호/iCloud로 기록한다. 같은 계정에 추가한 검증용 패스키는 Google 비밀번호 관리자 사용자확인 후 서버에서 삭제했다. hope_review_c의 맥 검증용 키 저장소명은 사용자 요청대로 주요 작업 뒤에 확인할 상태로 보류한다. AI가 기기 저장소를 직접 조사한 결과는 아니다.

아래는 hope_lab 등록에서 실제 서버 읽기로 확인한 COSE 공개키의 base64url 값이다. 공개키는 서명 검증용 공개값이며 개인키·비밀번호·세션 토큰이 아니다. 두 키 등록은 과거 절차이고 현재 이 계정에는 밥도둑1개가 남아 있다.

```text
밥도둑 — 현재 남음:
pQECAyYgASFYIGrfFeyVTydbDm73Hux1Scvr8uaN7QevTDF-gVw9MWOcIlggYm9-pJIy-isDh9ySfWtiVvWGbKVOOxdh_XYvA13Cagw
Google 추가 검증용 키 — 이후 서버삭제:
pQECAyYgASFYIKYPKBnijaeLXh4IdK9SRT1NqqGkUXkPjGa0lFPlOcxhIlggaUmMz15q7A8VOB4CjKgrJPvqr0VMB805d9Q34LbGCbY
```

## ② 왜 그걸 골랐나

공개 소개를 누구나 읽게 하고 본인 비공개 공간은 비밀번호 없이 열도록 분리한다. 실제 T01 FIELD NOTES의 기존 본문을 유지하도록 Pages 메뉴 연결 방식을 구성했다. 서명·origin·RP ID는 검증 라이브러리가, challenge 소비·자료 소유권·로그아웃은 서버가 확인한다. 서로 다른 origin 연결이므로 동일페이지 내부 통합이나 C11 심사 통과를 미리 주장하지 않는다.

## ③ 어디를 어떻게 고쳤나

T01 FIELD NOTES의 공개 내용인 네트워크·보안 관심, ASA 학습 상태, 실제 자료 우선·독립 대조·단계 진행 원칙, 실제 프로젝트 다섯 개, 공개 범위와 사용자/AI 역할을 새 화면에 연결했다. 원래 레이아웃을 보존하는 메뉴 추가 방식에서 전체 3D 개편으로 변경했다. 기존 보고서·원문·결과 이미지 링크는 계속 사용한다. 새로운 개인 경력이나 실험 결과는 만들지 않았다.

- `index.html`·`about.html`·`dashboard.html`: 공개 소개·3D 프로젝트 탐색·프로젝트 목록·자기소개·패스키 진입을 담은 새 화면. 기존 ABOUT/DASHBOARD 주소와 일부 옛 앵커도 연결된다.
- `orbit-scene.js`: Three.js의 프리즘·네트워크 노드·PC 화면·프로젝트 궤도·개인 공간 포털. PC 화면과 궤도 카드의 선·파형은 공간 연출용 그래픽이며 실제 측정 차트가 아니다. 실제 결과 차트는 프로젝트 팝업의 보존 이미지다.
- `portfolio-app.js`: 분류, 프로젝트 팝업, 실제 보고서/소스 연결, 키보드 닫기/초점 복귀, 모바일 메뉴, 움직임 줄이기와 카메라 진행. API 호출이나 인증정보 접근은 없다.
- `portfolio-data.js`: 확인된 T01 프로젝트 수치와 표본 한계·자기소개 사실. `portfolio.css`: 반응형 화면과 읽기·클릭·초점 표시. 브라우저 실행 파일 `portfolio.js`는 Three.js를 포함해 번들한 결과다.

입체 연출은 Active Theory의 공간 탐색을 참고한 별도 절차적 모델이며 해당 사이트의 코드·이미지·모델은 복제하지 않았다. 저사양 환경을 위해 DPR1.5 제한·30fps 상한·비활성 탭 정지·동작 줄이기·WebGL 실패 안내와 HTML 프로젝트 목록을 제공한다. 개인 공간으로 이동하면 기존 인증 사이트에서 등록·로그인·로그아웃·키 관리와 보호 자료 조회를 진행한다.

실제 인증 소스는 기존 Sites v3, commit `172fa1b81607c604047ad4b9fdddc39abdf89be8`의 `server/api.js`다. 등록 `/api/passkeys/register/options`·`/verify`·`/cancel`, 로그인 `/api/passkeys/authenticate/options`·`/verify`, 로그아웃 `/api/logout`, 비공개 조회 `/api/vault`·`/api/vault/:owner`가 이 서버를 지난다. 소유권 거절은 로그인 사용자와 `account_id` 조건을 확인하는 vault 분기다.

이 패키지의 인증 소스·증거 파일은 [실제 v3 인증 API 직접 읽기](task08-auth-api.js), [v3 전체 소스 ZIP](task08-source-v3.zip), [프로토콜 요청·응답 발췌](TASK08-PROTOCOL.md)다. 직접읽기 API는18,974 bytes이며 ZIP은68항목의 복원 가능한 원본 스냅샷이다. ZIP의 과거 설명서를 오늘의 최신 증거로 간주하지 않는다. 오늘의 상태와 증거 구분은 이 문서와 프로토콜 부록을 따른다. 이 파일들을 공개했다고 서버를 변경하거나 배포한 것은 아니다.

## ④ 안 열리는 것을 확인한 기록

| 필수 확인 | 성공 쪽 | 거절 쪽 | 증거 범위 |
|---|---|---|---|
| 로그인 없이 열기 | 인증 뒤 실제 본인자료3개 UI | 기존 공개 익명 자료 요청401 기록 | 실제 운영 관찰. 이번 문서 작업에서 재요청하지 않음 |
| 남의 패스키로 열기 | 사용자 A/C 두 브라우저 본인 UUID자료 각3개·AI 읽기 관찰 | 실제 상대 UUID는 양방향 owner_denied, 타인본문 미노출 | 운영로그 UUID/REDACTED 403 두 건 보강. 개별UUID가 가려져 해당요청 상태와 일대일 대응 확정 안 됨 |
| 이미 쓴 질문 재사용 | localhost 실제 정상 P-256 서명 #25·200 | 같은 POST본문 #26 replay400 | 테스트용 키·실제 암호·서버·HTTP 실행. 실사용자 기기 결과가 아님 |
| 패스키 삭제 뒤 로그인 | 승인된 Google 검증용 키 서버삭제 후 남은 밥도둑 로그인 사용자보고·UI | 삭제키 로그인 불가 사용자보고 | AI 독립 거절화면·서명 요청·HTTP 관찰 없음. 로컬 별도 검사는 남은키200/삭제키401 |

A/C의 원래 사용자 본인응답과 거절 이후 관리자 현재 저장값을 비교해 각3개 자료의 id·title·content가 모두 같았다. A 재조회도3개·내용동일이다. C 새로고침은 ERR_BLOCKED_BY_CLIENT여서 양쪽 최신 API 응답 대조는 부족하다. 이는 브라우저 차단이며 앱401/403으로 계산하지 않는다. A 이름 owner query에도 본인자료3개를 관찰했고 C방향 query·요청본문 위조 응답은 별도 미확인이다.

동일 hope_lab에서 두 키·두 공개키 등록, 새 Google 키 로그인 사용자/UI, 실행직전 사용자승인 후 AI 서버삭제, 당시9자료 불변, 남은 밥도둑 로그인 사용자/UI를 확인했다. C등록 후 전체상태는4계정·12자료다. 이전 B와 키0개인 yeah_um12의 계정·자료 잔존은 참고사항이며 계정전체삭제를 과제의 새 필수조건으로 추가하지 않는다.

운영 등록·로그인 options 각2회200, 각 취소200이며 질문 두 쌍은 서로 다르다. 아래 challenge는 공개 검증용 질문으로 비밀값이 아니다. 미등록 식별자401 뒤 같은 실패흐름 재요청400은 정상성공후 replay와 구분한다.

```text
등록1: m3pVlLSyq_NA0isua5ektfLXSNVMzuI1EngAsZDRZWs
등록2: jHOUQN1BjDtHf4NBqp08CzOTFA0CNPz2YpvdHImaJEU
로그인1: E6lk8gw90egyk9XQU_3gAzi9G-yZQSq9C8QIjoFLGIk
로그인2: 9TRoT2ew4hmeJQj_PcnXxhq2qslqErzq0MCUJm3MXS4
```

2026-10-11 UTC localhost 기록은15개 비교·58 HTTP 요청/응답의 실제 실행이다. [프로토콜 부록](TASK08-PROTOCOL.md)에 등록본문 #3, 정상/오류서명 #25/#28·200/401, 정상성공/replay #25/#26·200/400, logout/메모리 oldSession #22/#23·200/401을 발췌했다. Cookie는 `[가림]` 그대로다. 공개 attestation COSE에는 x/y가 있고 개인키 d가 없으며 실제 서명은 P-256 테스트키로 만들었다. 원문 개발 localhost 예외에 따라 이 증거들을 기기·운영 재실행이 없다는 이유만으로 일괄 미충족으로 처리하지 않는다. 당시 실행과 현재배포 동일성은 별도다.

C25는 별도 localhost에서 명시적 NotAllowedError shim으로 취소를 모의하고 기존 앱 취소분기 DOM 안내를 실제 렌더링해 확인했다. 안내는 “패스키 요청을 취소했거나 시간이 지났습니다. 저장하지 않았으니 다시 시도해 주세요.”다. 실제 로컬 API options200→cancel200, accounts/credentials/vault_items/sessions 각각0→0이고 임시 challenge는 used0→1이다. DB전체에 아무 행도 저장되지 않았다고 주장하지 않는다. AI의 로컬검사이며 native 사용자 취소가 아니다.

## ⑤ AI와 나

1. AI에게 맡긴 일: 화면·인증 구현, 테스트키 실제 암호·HTTP검사, C25 로컬 취소검사, 관리자읽기·증거대조, 승인된 서버키 삭제, 공개연결 패키지와 설명서 정리.
2. 내가 직접 판단·수행한 일: 공개소스·영상 선택, 실제기기 등록·인증, Apple/Google 저장소 확인, 키삭제 승인, 로그인·삭제키 로그인불가 확인보고, A/C 두브라우저 UUID 요청.
3. AI 제안을 따르지 않은 일: 기존계정에 새키를 먼저 추가하자는 제안 대신 새 hope_lab 계정을 만들어 유지하기로 선택했다. 동기는 확인하지 않아 추정하지 않는다.

## ⑥ 아직 못 막은 것·미완료

공개 Pages 메뉴·파일 접근·소스 링크의 발행 검증과 제출 receipt는 별도 기록으로 확인한다. Pages→Sites 외부연결을 T01 계승 조건의 최종 심사 통과로 확정하지 않는다. 기존 Sites 인증 서버·RP ID·쿠키·CSP와 계정·자료를 유지한다. 이 개편은 GitHub Pages 공개 화면 변경이며 Sites 서버 재배포를 주장하지 않는다.

개별UUID 요청 HTTP상태 직접대조, C 새 API 재조회, C query·요청본문 위조, 선택credential·삭제키거절 독립증거는 부족하다. C저장소명은 사용자선호대로 뒤에 확인한다. 운영 실기기 등록본문·정상replay·oldSession은 미관찰이지만 로컬 원문 기록은 부록에 있다. 사용자/기기 증거로 바꾸지 않는다. 모든 패스키·저장소 접근을 잃으면 비공개자료에 다시 접근할 수 없고 비밀번호 복구는 제공하지 않는다. 잠금해제된 기기·유효세션 탈취위험을 완전히 없앨 수 없다.

## 짧은 확인 방법 4줄

1. 어디로 가나요: 결과물 https://h0p2.github.io/field-notes-network-security/ 와 소스 https://github.com/H0P2/field-notes-network-security 를 연다.
2. 세 단계 안에 무엇을 하나요: 공개 FIELD NOTES 확인 → 패스키 메뉴로 별도 Sites 이동 → 본인 패스키 로그인 후 가상자료3개·키목록 확인.
3. 무엇이 보이면 통과인가요: 기존 소개의 확인된 내용과 실제 프로젝트가 새 화면에 남고 인증 뒤 본인자료만 열린다. 양방향 owner_denied·자료보존·두키 삭제절차는 기록의 범위로 확인하며 C11 심사와 전체조건 충족은 확정하지 않는다.
4. 안 될 때는 무엇이 보이나요: 취소안내 또는401/owner_denied 등 거절을 확인한다. ERR_BLOCKED_BY_CLIENT는 앱거절과 구분하고 로컬replay400·삭제키 사용자보고도 범위를 따른다.

## AI와 나 3줄

AI에게 맡긴 일: 구현, 로컬 암호·HTTP·취소검사, 관리자읽기·승인된 삭제·증거대조·연결패키지·문서정리.
내가 직접 판단·수행한 일: 소스·영상선택, 기기등록·인증·저장소확인, 삭제승인과 로그인결과보고, A/C 직접 UUID조회.
AI 제안을 따르지 않은 일: 기존계정 키추가 우선제안 대신 hope_lab 신규계정을 유지하기로 선택했다. 선택동기는 추정하지 않는다.

비밀번호·개인키·쿠키·세션·토큰·비밀키 원문은 제출하지 않는다. 공개키·challenge·표준 공개 검증응답은 프로토콜 범위를 설명해 제공한다. 실제 발행·공개접근 검증·최종제출 receipt는 별도 기록하며, 이 문서가 그 실행 기록을 대신하지 않는다.
