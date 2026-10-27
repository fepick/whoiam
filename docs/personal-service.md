# 사내 개인용 로컬 운영

v0.03은 본인 Windows 계정으로 본인 PC에서 사용하는 구성을 기준으로 합니다.
UI 기본 배율은 110%이며 브라우저 배율은 100%를 기준으로 합니다. 운영 데이터·키·복구 파일을 GitHub나 Sites로 보내지 않습니다.

## 실행 프로필

| 실행 | 데이터 위치 | 키 |
| --- | --- | --- |
| `--demo=True` | 메모리, 종료하면 삭제 | 메모리 임시 키 |
| 기본 `--profile=production` | `%LOCALAPPDATA%/Whoiam/.private/production/` | OS 저장소의 운영 UUID |
| `--profile=development` | checkout의 `.private/development/` | 별도 개발 UUID |
| `--profile=test --data_home=절대경로` | 지정한 임시 홈의 `.private/test/` | 별도 테스트 UUID |

운영 데이터 홈은 개발 checkout 밖이어야 합니다. 다른 위치를 쓰려면 `--data_home=절대경로`를 지정합니다.
홈 안에 `.private/프로필`이 생성됩니다. 프로필별 파일 잠금으로 같은 DB의 중복 실행을 차단합니다.
각 폴더는 Windows에서 현재 사용자와 SYSTEM만 허용하는 DACL을 설정하며 실패 시 중단합니다.
단일 사용자·루프백 전용이며 사내 다른 PC로 공개하는 서버 구성은 지원하지 않습니다.

```powershell
.\.venv\Scripts\python.exe -m apps.server
# 또는
.\scripts\Start-Whoiam.ps1
```

서버가 연 브라우저에서 잠금을 해제합니다. OS 키 접근은 해제 시에만 시작합니다.
운영·개발·테스트 프로필은 상단과 설정 화면에서 구분합니다.
서버를 켜기만 해서는 출근 처리되지 않습니다. 출근은 별도 명령으로 기록합니다.

## 키 식별자와 기존 데이터 이전

`vault.json`에는 형식 버전·프로필·무작위 UUID만 보관합니다. 암호화 키는 포함하지 않습니다.
OS 키는 경로 해시 대신 `프로필:UUID`로 찾으므로 코드나 데이터 폴더를 옮겨도 같은 OS 계정에서 찾을 수 있습니다.
OS 키나 식별 파일이 사라지면 새 키로 기존 DB를 덮어쓰지 않습니다.
폴더 이동 시에는 DB만 옮기지 말고 해당 프로필 폴더를 함께 보존합니다.

v0.02에서 실제 기록을 이미 사용했다면 **앱을 종료하고 사용자가 직접** 다음 명령을 실행합니다.
개발 도구는 기존 `.private/`를 열지 않으며 자동 이전도 하지 않습니다.

```powershell
.\.venv\Scripts\python.exe -m apps.manage migrate_legacy
```

이 명령은 현재 checkout의 `.private/database/whoiam.sqlite3`와 그 DB의 기존 OS 키만 읽어,
비어 있는 새 운영 프로필에 암호문을 복사·검증합니다. 원본 DB와 이전 OS 키는 삭제하지 않습니다.
기존 checkout을 이동하기 전에 이전하는 것이 좋습니다. 대상에 이미 데이터가 있으면 중단합니다.

## 백업과 같은 기기 복원

설정 → 개인 실사용 관리에서 다음을 사용할 수 있습니다.

- 지금 백업: 일관된 SQLite 스냅샷을 만들고 모든 레코드의 암호문을 검증합니다.
- 백업·복원: 날짜별 목록·암호화 파일 다운로드·선택 시점 복원.
- 복원 전 현재 데이터를 별도 안전 백업으로 보존하며 그 백업으로 되돌릴 수 있습니다.

변경이 있으면 최대 약 5분에 한 번 자동 백업하고 잠금·유휴 만료·정상 종료 직전에도 변경분을 백업합니다.
자동 백업은 최근 30개를 보관합니다. 수동·복원 전 안전 백업은 자동 삭제하지 않습니다.
자동 백업은 잠금 해제 유휴 시간을 연장하지 않습니다. 실패하면 설정 화면에 표시합니다.
백업 오류가 있으면 화면의 종료 명령은 앱을 유지하며 오류를 안내합니다.
강제 종료·전원 차단 직전의 최근 변경은 자동 백업에 아직 없을 수 있습니다.

백업은 해당 프로필의 `backups/` 안에 저장합니다. 같은 디스크의 백업만으로 PC 고장에 대비할 수는 없습니다.
회사에서 허용한 별도 보관 위치로 암호화 백업 파일을 정기적으로 저장합니다.
복원은 현재 OS 키를 사용하므로 **다른 PC로 복구하려면 아래 복구 파일도 필요합니다.**

## OS 키 유실·새 PC 복구

앱을 종료하고 별도 보관 경로를 준비한 뒤 실행합니다. 예시 경로는 사용자 환경에 맞게 변경합니다.

```powershell
.\.venv\Scripts\python.exe -m apps.manage export_recovery E:\WhoiamRecovery\office.whoiam-recovery
```

복구 암호를 터미널에서 두 번 입력합니다. 명령 인자·로그·브라우저로 전달하지 않습니다.
Scrypt와 Fernet으로 OS 키 사본을 암호화하며 평문 키는 파일로 저장하지 않습니다.
복구 파일은 checkout 및 `.private/` 밖에만 생성하며 기존 파일을 덮어쓰지 않습니다.
복구 파일과 복구 암호는 서로 분리해 보관합니다. DB 백업·복구 파일·복구 암호가 모두 있어야 합니다.

```powershell
.\.venv\Scripts\python.exe -m apps.manage recover --backup=E:\WhoiamRecovery\백업파일.sqlite3 --recovery_file=E:\WhoiamRecovery\office.whoiam-recovery --data_home=C:\WhoiamRecovered
.\.venv\Scripts\python.exe -m apps.server --data_home=C:\WhoiamRecovered
```

복구는 비어 있는 데이터 홈에만 허용합니다. 복구 암호와 백업을 검증한 후 현재 OS 키 저장소에 키를 등록합니다.
프로필이 다르거나 기존 키가 다른 경우 덮어쓰지 않습니다. 키 교체·다중 사용자 공유는 아직 제공하지 않습니다.

## 로그인 자동 실행과 종료

앱의 설정 → 로그인 자동 실행에서 켜거나 끌 수 있습니다. 초기값은 등록되지 않은 상태입니다.
현재 사용자 로그인 시 일반 권한으로 실행하며 Windows 암호·관리자 권한을 저장하지 않습니다.
도우미 콘솔은 숨기고 브라우저를 엽니다. 실제 키 저장소는 사용자가 잠금을 해제할 때 엽니다.
자동 실행을 끄더라도 현재 앱을 강제 종료하지 않습니다. 종료는 앱 종료 버튼을 사용합니다.

```powershell
.\scripts\Install-Autostart.ps1 -Preview
.\scripts\Install-Autostart.ps1
.\scripts\Install-Autostart.ps1 -Remove
```

개발자가 수행한 검증은 Preview와 가짜 작업 등록 어댑터이며 PC에 실제 작업은 등록하지 않았습니다.
사내 정책이 작업 등록을 제한하면 실패를 안내하며 정책·실행 정책을 우회하지 않습니다.
자동 실행은 현재 checkout과 `.venv`를 사용하므로 코드 경로를 옮긴 뒤에는 다시 등록해야 합니다.

## 검증과 남은 범위

업데이트할 때에는 앱을 정상 종료하고 백업·복구 수단을 확인한 뒤, 검토한 커밋으로 코드를 변경하고 `requirements.txt`를 설치합니다.
검증을 마친 코드로 기존 운영 데이터 홈을 사용해 재실행합니다. 코드 경로를 바꾸면 로그인 자동 실행을 다시 등록합니다.
개발 checkout의 변경·가상 테스트가 운영 홈을 직접 수정하지 않도록 프로필을 명시합니다.

가상 DB·가짜 OS 키 백엔드로 폴더 이동·프로필 분리·키 유실·백업 변조·복원·복구 암호·기존 DB 이전을 검증합니다.
Windows 전용 폴더 권한과 단일 실행 잠금은 임시 디렉터리에서 확인합니다.
실제 운영 저장소·OS 자격증명은 개발 도구로 열지 않습니다. 브라우저 클릭 검증과 재부팅 후 자동 실행은 별도 실환경 확인이 필요합니다.
판매처 자동 구매·실시간 배송 조회·회사 급여 규정 계산은 후속 연동 범위입니다.

기술 참고: [SQLite 백업](https://docs.python.org/3.11/library/sqlite3.html#sqlite3.Connection.backup),
[Fernet과 암호 기반 키](https://cryptography.io/en/stable/fernet/),
[Windows DACL](https://learn.microsoft.com/en-us/windows/win32/api/aclapi/nf-aclapi-setnamedsecurityinfow),
[로그인 작업 주체](https://learn.microsoft.com/en-us/powershell/module/scheduledtasks/new-scheduledtaskprincipal).
