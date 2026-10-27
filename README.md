# Whoiam

구매, 재고, 근무, 업무 및 일일 보고를 연결하는 개인 업무 자동화 프로젝트입니다.
웹을 첫 인터페이스로 사용하며, 이후 MCU·CLI·별도 서버도 같은 명령 규격을 사용합니다.

목업의 메뉴를 실제 로컬 업무 기능으로 구현한 v0.02입니다. Python 모듈형 모놀리스와 웹 인터페이스를 사용합니다.

## 실행

Python 3.11 이상에서 프로젝트 루트 기준으로 실행합니다. 기존 `rpi` conda 환경은 [개발 안내](CONTRIBUTING.md)를 참고합니다.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m apps.server --demo=True
```

브라우저가 자동으로 열립니다. 데모는 가상 데이터와 메모리 DB만 사용하며 서버를 종료하면 모두 삭제됩니다.
이미 준비된 `.venv` 또는 `rpi` 환경에서는 `./scripts/Start-Whoiam.ps1 -Demo`로도 실행할 수 있습니다.

실제 로컬 저장 모드는 `python -m apps.server`로 실행하고, **서버가 자동으로 연 창**에서 잠금을 해제합니다.
초기 접속 토큰은 브라우저 URL fragment로만 전달하고 접속 직후 제거합니다. 터미널·요청 로그에는 출력하지 않습니다.
지원하는 OS 키 저장소가 없거나 기존 키를 잃은 경우 저장소를 열지 않습니다. DB는 `.private/database/`에 인증 암호화해 보관합니다.
OS 계정·기기 분리와 복구상의 한계는 [민감정보 정책](docs/security.md)을 먼저 확인해주세요.

## 구현된 기능

- 업무: 추가·수정·우선순위·예정일·ETA·진행 상태·날짜별 소요시간·정정·보관.
- 구매: 여러 품목의 주문 등록·도착 예정·메모·분할 수령·단위 환산 입고·암호화 증빙 첨부.
- 재고: 품목·보관 위치·최소 수량·입출고 원장·실사 조정·BOM 버전·조립 수량 및 추가 손실 차감.
- 근무: 출퇴근·휴게·수동 기록·정정 사유·주간 합계·설정 기준 초과 알림·월별 급여 입금 대조.
- 보고: 실제 업무 로그로 초안 생성·수정·암호화 저장·우선순위와 ETA·한 장 PNG 다운로드.
- 코어: 명령 라우팅·재시도 중복 방지·출근 시 할 일 안내·퇴근 시 확인 항목과 보고 생성.
- 민감정보: OS 키 저장소 연동·암호화 저장·마스킹 목록·잠금·유휴 만료·허용 목적 외 원문 접근 거부.

판매처 자동 구매·실시간 배송 조회·급여 세금/수당 계산·키 교체 및 기기 간 복원·MCU 펌웨어는 후속 범위입니다.
원격 Sites 주소는 가상 데이터 목업으로 유지합니다. 실제 기능은 로컬 서버에서 사용하며 운영 데이터를 원격으로 배포하지 않습니다.

## 구조

- `apps/web/`: 5개 메뉴의 웹 콘솔과 Canvas 보고 이미지 렌더러.
- `apps/server/`: 루프백 전용 API·세션 인증·CLI·메모리 데모.
- `packages/core/`: 출근·퇴근 등 여러 모듈을 연결하는 흐름.
- `packages/modules/`: 구매·재고·근무·업무·보고·민감정보 모듈.
- `packages/platform/`: 입력 검증·인증 암호화 저장소·OS 키 연결.
- `tests/`: 가상 데이터로 실행하는 pytest 검증.
- `docs/`: 설계, 데이터 정책, 구현 순서.
- `scripts/`, `.githooks/`: 민감 경로 검사와 Git 훅.
- `.private/`: 실제 운영 데이터의 로컬 전용 디렉터리. Git·Docker·소스 아카이브에서 제외합니다.

실제 로그인·카드·개인정보는 소스, 문서, Issue, PR, 로그, 테스트 데이터에 입력하지 않습니다.
개발·검증에는 가상 데이터만 사용합니다. `.private/`의 실제 내용은 개발 도구로 읽지 않습니다.

## 문서

- [프로젝트 구조](docs/architecture.md)
- [출근·퇴근 흐름](docs/workflows.md)
- [민감정보 정책](docs/security.md)
- [구현 순서](docs/roadmap.md)
- [민감정보 모듈](packages/modules/sensitive/README.md)
- [개발 규칙](CONTRIBUTING.md)
- [로컬 API](docs/api.md)

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
