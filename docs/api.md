# 로컬 API와 모듈 명령

기본 주소는 `http://127.0.0.1:4173`이며 외부 인터페이스에 바인딩하지 않습니다.
HTTP 어댑터와 업무 모듈을 분리하여 향후 MCU·서버 전송 계층을 추가할 수 있습니다.
현재 API는 브라우저 로컬 세션용입니다. MCU에 세션·로그인 정보·카드 원문을 복사하지 않습니다.

## 접속과 보호

실제 저장 모드에서 CLI가 브라우저를 열며, 초기 접속 토큰은 fragment에서 `/api/session`으로 교환한 뒤 주소에서 제거합니다.
응답 쿠키는 HttpOnly·SameSite=Strict이고 서버 재시작 시 무효화됩니다. 세션 토큰은 로그에 출력하지 않습니다.
루트 페이지를 열기만 해서는 실제 저장 모드의 API 권한이 생기지 않습니다.
단일 OS 사용자용이며 HTTPS·원격 로그인·다중 사용자 역할은 아직 지원하지 않습니다.

POST는 같은 Origin, 세션 쿠키, `X-Whoiam-CSRF`, JSON, 요청 크기 상한을 검사합니다.
외부 호스트·교차 사이트 요청·허용하지 않은 자산 경로는 거부합니다. API 문서 자동 노출과 접근 로그는 비활성화합니다.
잠금은 모든 업무 조회·명령·증빙 다운로드를 중단합니다. 자동 목록 갱신은 유휴 만료를 연장하지 않습니다.

| 요청 | 기능 |
| --- | --- |
| `POST /api/session` | CLI가 전달한 초기 토큰을 세션으로 교환 |
| `GET /api/status` | 잠금·데모 여부·CSRF 토큰 |
| `POST /api/unlock`, `POST /api/lock` | 현재 OS 계정의 보관함 잠금 제어 |
| `GET /api/snapshot` | 각 모듈의 화면용 공개 조회 |
| `POST /api/commands` | 아래 모듈 명령 실행 |
| `GET /api/documents/{reference}` | 인증된 세션의 증빙 첨부 다운로드 |
| `GET /api/backups`, `POST /api/backups` | 프로필의 백업 목록·수동 백업 |
| `GET /api/backups/{id}` | 검증한 암호화 DB 백업 다운로드 |
| `POST /api/backups/restore` | revision·확인값 검사 후 복원, 직전 안전 백업 보존 |
| `GET /api/autostart`, `POST /api/autostart` | 현재 사용자 로그인 자동 실행 조회·설정 |
| `POST /api/shutdown` | 변경분 백업 후 정상 종료 |

## 명령 계약

```json
{
  "name": "tasks.save",
  "request_id": "00000000-0000-4000-8000-000000000001",
  "data": {"title": "가상 측정 업무", "priority": "P1", "due": "2026-10-27"}
}
```

실제 요청마다 새 UUID를 사용하고 같은 작업을 재시도할 때만 기존 UUID와 같은 입력을 사용합니다.
같은 ID로 다른 명령을 실행하면 거부합니다. 예시는 가상 데이터입니다.
응답은 `{"result": ...}`이며 오류는 원문 입력을 포함하지 않는 `{"error": "..."}`입니다.
상세 필드와 입력 검증의 기준은 각 모듈 공개 메서드이며 허용하지 않은 필드는 거부합니다.

| 모듈 | 명령 |
| --- | --- |
| tasks | `save`, `log`, `update_log` |
| inventory | `save`, `move`, `adjust`, `bom`, `preview`, `assemble` |
| purchasing | `create`, `update`, `receive`, `document` |
| attendance | `break_start`, `break_end`, `record`, `payroll` |
| reporting | `generate`, `save` |
| sensitive | `save`, `remove`, `upload` |
| core | `start`, `finish`, `settings`, `command` |

명령 이름은 `모듈.명령` 형태입니다. `core.command`는 정해진 한국어 명령만 해석하며 입력을 외부 AI에 전송하지 않습니다.
수량·원화 금액·분은 정수입니다. 시각은 ISO 8601 오프셋을 포함하고 날짜는 `YYYY-MM-DD`를 사용합니다.
보고서 ETA의 편집 값은 한국 시간의 `YYYY-MM-DDTHH:mm`입니다.

`attendance.record`는 겹친 기존 세션 전체를 이력으로 보관하고 수동 입력을 우선 적용합니다.
현재 기록의 응답에는 `source`와 `replaces`가 포함되며 `snapshot.attendance_history`에서 제외된 원본과 정정 전 이력을 조회합니다.
이력의 값을 다시 적용하려면 `id`를 빼고 새 `attendance.record` 명령으로 저장합니다.
