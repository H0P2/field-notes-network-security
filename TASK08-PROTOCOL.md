# 제출용 로컬 프로토콜 증거 발췌 — 2026-10-14

원 기록: `task08/qa/synthetic-protocol-result.json`. 실행시각 UTC 2026-10-11T22:32:28.662Z · 주소 http://localhost:5174 · 58 HTTP 요청/응답, 성공·거절 비교15개. 아래 번호는 exchanges 배열의1부터 시작하는 순서다. 이번 작업은 기존 기록 발췌·대조이며 재실행하지 않았다.

테스트용 P-256 키쌍을 생성해 실제 SHA-256 서명을 만들고 localhost 서버에서 SimpleWebAuthn 검증과 HTTP 요청을 실행한 기록이다. 합성인 것은 키/인증기 fixture이며 응답을 고정한 모의 검사가 아니다. 사용자 조작·실제 기기 패스키·현재 운영 배포의 증거로 귀속하지 않는다. localhost는 원문 개발 예외 범위이며 공개 HTTPS 결과물 제출이나 운영 통합을 대신하지 않는다.

| 요구조건 | 발췌 | 결과 |
|---|---|---|
| C23 등록본문 개인키 미포함 | #3 등록 POST 본문·200 | 등록본문=registrationRequest, 공개 attestation COSE 구조 확인 |
| C29/C30 정상·실패 서명 | #25 정상과 #28 잘못된 서명 | 200과401 authentication_rejected |
| C31 정상성공 뒤 replay | #25와 #26 같은 POST 본문 | 200 뒤400 challenge_expired_or_used, 본문 완전동일 |
| C33 로그아웃·이전세션 | #22 logout와 #23 vault | 200 뒤401 authentication_required |

Cookie는 원 기록의 `[가림]`을 그대로 유지한다. #22/#23의 같은 세션 여부는 원 테스트의 메모리 oldSession 변수 전달을 auth 재평가에서 확인한 범위다. 가린 문자열 자체가 같다는 사실만으로 세션 동일성을 증명하는 것은 아니다. 원 기록 sessionValues도 쿠키 재사용은 프로세스 메모리에서만 실행하고 저장하지 않았다고 설명한다. 사용자 쿠키를 추가 수집하지 않았다.

## C23 등록본문 공개 구조 해설

`id`/`rawId`는 테스트 credential의 공개 식별자이고 `type`은 public-key다. `clientDataJSON`은 아래 공개 요청 문맥을 base64url로 표현한다. `attestationObject`는 CBOR의 fmt/attStmt/authData 구조이며 이 기록은 fmt=none, attStmt={}다. authData에는 RP ID 해시·플래그·카운터·공개 credential 식별자와 COSE 공개키가 들어 있다. 추출한 COSE 키는 kty=2(EC2), alg=-7(ES256), crv=1(P-256), x/y 각각32bytes이며 키항목은1,3,-1,-2,-3뿐이다. 개인키 d(-4)는 없다. COSE 공개키 바이트는 원 기록 publicKey와 일치했다. 이를 실제 기기 개인키 저장소 조사로 표현하지 않는다.

```json
{
  "type": "webauthn.create",
  "challenge": "9STpH8K1fsdcBLW043RvYwRMW-MT3s43KXfk3skEq-U",
  "origin": "http://localhost:5174",
  "crossOrigin": false
}
```

인증 본문의 `authenticatorData`는 공개 인증기 데이터, `signature`는 검증에 전달하는 공개 서명 응답이며 개인키가 아니다. #28은 의도적으로 잘못된 서명이다. `userHandle`은 이 fixture에서 null이다. 인코딩값이 길다는 이유만으로 세션 토큰으로 해석하지 않는다.

## exchanges #3

```json
{
  "request": {
    "method": "POST",
    "path": "/api/passkeys/register/verify",
    "headers": {
      "Origin": "http://localhost:5174",
      "Cookie": "[가림]"
    },
    "body": {
      "id": "6r41s0byY9HHA9q68jbQePvc72nz7IqVYX8E1EoHj5k",
      "rawId": "6r41s0byY9HHA9q68jbQePvc72nz7IqVYX8E1EoHj5k",
      "type": "public-key",
      "authenticatorAttachment": "platform",
      "clientExtensionResults": {},
      "response": {
        "clientDataJSON": "eyJ0eXBlIjoid2ViYXV0aG4uY3JlYXRlIiwiY2hhbGxlbmdlIjoiOVNUcEg4SzFmc2RjQkxXMDQzUnZZd1JNVy1NVDNzNDNLWGZrM3NrRXEtVSIsIm9yaWdpbiI6Imh0dHA6Ly9sb2NhbGhvc3Q6NTE3NCIsImNyb3NzT3JpZ2luIjpmYWxzZX0",
        "attestationObject": "o2NmbXRkbm9uZWdhdHRTdG10oGhhdXRoRGF0YVikSZYN5YgOjGh0NBcPZHZgW4_krrmihjLHmVzzuoMdl2NFAAAAAAAAAAAAAAAAAAAAAAAAAAAAIOq-NbNG8mPRxwPauvI20Hj73O9p8-yKlWF_BNRKB4-ZpQECAyYgASFYII36hEwjqFwxYTylJM70ynUYlivPFZ2pkPfYc6dCOzvSIlggXAn0hs2E49TTIdWLWCSQPld9D5DAHMfmfKW41jx3Jk4",
        "transports": [
          "internal"
        ]
      }
    }
  },
  "response": {
    "status": 200,
    "data": {
      "ok": true,
      "user": {
        "id": "4423502c-8f92-40e5-a578-ca717f6b3d68",
        "username": "fixture_a_mv4ef3ox"
      }
    }
  }
}
```

## exchanges #22

```json
{
  "request": {
    "method": "POST",
    "path": "/api/logout",
    "headers": {
      "Origin": "http://localhost:5174",
      "Cookie": "[가림]"
    },
    "body": {}
  },
  "response": {
    "status": 200,
    "data": {
      "ok": true
    }
  }
}
```

## exchanges #23

```json
{
  "request": {
    "method": "GET",
    "path": "/api/vault",
    "headers": {
      "Origin": "http://localhost:5174",
      "Cookie": "[가림]"
    }
  },
  "response": {
    "status": 401,
    "data": {
      "error": "authentication_required",
      "message": "패스키로 로그인해주세요. 세션이 만료되었을 수 있습니다."
    }
  }
}
```

## exchanges #25

```json
{
  "request": {
    "method": "POST",
    "path": "/api/passkeys/authenticate/verify",
    "headers": {
      "Origin": "http://localhost:5174",
      "Cookie": "[가림]"
    },
    "body": {
      "id": "6r41s0byY9HHA9q68jbQePvc72nz7IqVYX8E1EoHj5k",
      "rawId": "6r41s0byY9HHA9q68jbQePvc72nz7IqVYX8E1EoHj5k",
      "type": "public-key",
      "authenticatorAttachment": "platform",
      "clientExtensionResults": {},
      "response": {
        "clientDataJSON": "eyJ0eXBlIjoid2ViYXV0aG4uZ2V0IiwiY2hhbGxlbmdlIjoiNFJVbGg2Slp3WlM4WlJEVTZUUEFLLUhhMWlmaTVNUGp4OUE4TlR1WjBnQSIsIm9yaWdpbiI6Imh0dHA6Ly9sb2NhbGhvc3Q6NTE3NCIsImNyb3NzT3JpZ2luIjpmYWxzZX0",
        "authenticatorData": "SZYN5YgOjGh0NBcPZHZgW4_krrmihjLHmVzzuoMdl2MFAAAAAQ",
        "signature": "MEYCIQD95d_WLTQMAaXQdZa3BkEGUgoF89ON6-YE9hglHg5yEwIhAI5GCBaK7e59cOFX33dhq5i8tpbUYrydKotHg_3MvRVg",
        "userHandle": null
      }
    }
  },
  "response": {
    "status": 200,
    "data": {
      "ok": true,
      "user": {
        "id": "4423502c-8f92-40e5-a578-ca717f6b3d68",
        "username": "fixture_a_mv4ef3ox"
      }
    }
  }
}
```

## exchanges #26

```json
{
  "request": {
    "method": "POST",
    "path": "/api/passkeys/authenticate/verify",
    "headers": {
      "Origin": "http://localhost:5174",
      "Cookie": "[가림]"
    },
    "body": {
      "id": "6r41s0byY9HHA9q68jbQePvc72nz7IqVYX8E1EoHj5k",
      "rawId": "6r41s0byY9HHA9q68jbQePvc72nz7IqVYX8E1EoHj5k",
      "type": "public-key",
      "authenticatorAttachment": "platform",
      "clientExtensionResults": {},
      "response": {
        "clientDataJSON": "eyJ0eXBlIjoid2ViYXV0aG4uZ2V0IiwiY2hhbGxlbmdlIjoiNFJVbGg2Slp3WlM4WlJEVTZUUEFLLUhhMWlmaTVNUGp4OUE4TlR1WjBnQSIsIm9yaWdpbiI6Imh0dHA6Ly9sb2NhbGhvc3Q6NTE3NCIsImNyb3NzT3JpZ2luIjpmYWxzZX0",
        "authenticatorData": "SZYN5YgOjGh0NBcPZHZgW4_krrmihjLHmVzzuoMdl2MFAAAAAQ",
        "signature": "MEYCIQD95d_WLTQMAaXQdZa3BkEGUgoF89ON6-YE9hglHg5yEwIhAI5GCBaK7e59cOFX33dhq5i8tpbUYrydKotHg_3MvRVg",
        "userHandle": null
      }
    }
  },
  "response": {
    "status": 400,
    "data": {
      "error": "challenge_expired_or_used",
      "message": "이미 사용했거나 만료된 인증 요청입니다. 다시 시작해주세요."
    }
  }
}
```

## exchanges #28

```json
{
  "request": {
    "method": "POST",
    "path": "/api/passkeys/authenticate/verify",
    "headers": {
      "Origin": "http://localhost:5174",
      "Cookie": "[가림]"
    },
    "body": {
      "id": "6r41s0byY9HHA9q68jbQePvc72nz7IqVYX8E1EoHj5k",
      "rawId": "6r41s0byY9HHA9q68jbQePvc72nz7IqVYX8E1EoHj5k",
      "type": "public-key",
      "authenticatorAttachment": "platform",
      "clientExtensionResults": {},
      "response": {
        "clientDataJSON": "eyJ0eXBlIjoid2ViYXV0aG4uZ2V0IiwiY2hhbGxlbmdlIjoiZXdzTnl1Mk9DYy1Ob0FPR0VOWEJuMFgtQXpGLVYxd2RaSV84VGpxMGFOQSIsIm9yaWdpbiI6Imh0dHA6Ly9sb2NhbGhvc3Q6NTE3NCIsImNyb3NzT3JpZ2luIjpmYWxzZX0",
        "authenticatorData": "SZYN5YgOjGh0NBcPZHZgW4_krrmihjLHmVzzuoMdl2MFAAAAAg",
        "signature": "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA",
        "userHandle": null
      }
    }
  },
  "response": {
    "status": 401,
    "data": {
      "error": "authentication_rejected",
      "message": "패스키 서명을 확인할 수 없습니다. 다시 로그인해주세요."
    }
  }
}
```

## 검토 결과와 한계

선정한 요청/응답과 전체 구조에서 privateKey/privateToken·access_token/refresh_token·Authorization 필드를 발견하지 않았고 Cookie는 모두 가림 상태다. 공개 등록 CBOR에서 개인키 성분이 없음을 확인했다. C19/C27 질문 생성·보관은 기존 options/verify·재사용 거절과 auth 코드 대조 범위로 뒷받침되며 별도 DB snapshot은 없다. C25 취소 안내와 계정/키/자료 전후 집계는 별도 보완 범위다. localhost 실행을 운영/실기기 재검증이 없다는 이유만으로 C23/C30/C31/C33의 일괄 미충족으로 표시하지 않는다. 현재 배포 동일성·원본계승·publisher 제한은 이 부록으로 해소되지 않는다.
