# Whoiam

구매, 재고, 근무, 업무 및 일일 보고를 연결하는 개인 업무 자동화 프로젝트입니다.
웹을 첫 인터페이스로 사용하며, 이후 MCU·CLI·별도 서버도 같은 명령 규격을 사용합니다.

현재 단계는 설계와 저장소 보호 규칙 작성입니다. 실행 가능한 업무 앱이나 암호화 저장소는 아직 없습니다.

메뉴와 화면 흐름을 검토할 수 있는 [웹 목업](apps/web/README.md)을 추가했습니다.
`node apps/web/serve.mjs` 실행 후 `http://127.0.0.1:4173`에서 확인할 수 있습니다.

## 구조

- `apps/web/`: 업무 콘솔의 정적 웹 목업. API·백그라운드 작업은 이후 구현합니다.
- `packages/core/`: 출근·퇴근 등 여러 모듈을 연결하는 흐름.
- `packages/modules/`: 구매·재고·근무·업무·보고·민감정보 모듈.
- `docs/`: 설계, 데이터 정책, 구현 순서.
- `scripts/`, `.githooks/`: 민감 경로 검사와 Git 훅.
- `.private/`: 실제 운영 데이터의 로컬 전용 디렉터리. Git·Docker·소스 아카이브에서 제외합니다.

실제 로그인·카드·개인정보는 소스, 문서, Issue, PR, 로그, 테스트 데이터에 입력하지 않습니다.
암호화 저장과 로컬 접근 통제가 구현되기 전에는 `.private/`에도 실제 민감정보를 넣지 않습니다.

## 문서

- [프로젝트 구조](docs/architecture.md)
- [출근·퇴근 흐름](docs/workflows.md)
- [민감정보 정책](docs/security.md)
- [구현 순서](docs/roadmap.md)
- [민감정보 모듈](packages/modules/sensitive/README.md)

## GitHub 사용 준비

로컬 Git 저장소는 `main` 브랜치로 초기화했으며, `origin`은 GitHub 비공개 저장소에 연결했습니다.
새로 clone한 환경에서는 다음 명령으로 로컬 훅을 설치하고 검사합니다.

```powershell
pwsh -NoProfile -File scripts/Install-GitHooks.ps1
pwsh -NoProfile -File scripts/Test-SensitivePaths.ps1
pwsh -NoProfile -File scripts/Check-SensitivePaths.ps1 -IncludeHistory
```

훅 설치는 해당 저장소의 `core.hooksPath`를 `.githooks`로 설정합니다.
Windows 실행 정책이 스크립트를 차단하면 훅도 작업을 중단합니다. 시스템 정책을 자동 변경하지 않습니다.
검사는 금지 경로를 대상으로 하며 임의의 소스 코드에 직접 입력된 비밀값까지 판별하지는 않습니다.
GitHub CI는 업로드 이후 실행되므로 유출 예방의 유일한 수단으로 사용하지 않습니다.
