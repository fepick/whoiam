# 다른 PC에서 설치하기

Windows 10/11 · Python 3.11 이상을 기준으로 합니다. 현재 사용자 권한으로 실행합니다.
운영은 Windows의 OS 보안 저장소를 사용하며, 인터넷 공개 서버나 다중 사용자 공유 배포는 지원하지 않습니다.

## 파일 준비

검증된 `whoiam-0.04.zip`을 받았다면 원하는 폴더에 압축을 풉니다. 기존 `.venv`나 운영 데이터는 복사하지 않습니다.
Git으로 설치할 때는 접근 권한이 있는 계정으로 다음을 실행합니다. GitHub 로그인은 직접 진행하고 비밀번호·토큰을 AI에게 보내지 않습니다.

```powershell
git clone --branch release/v0.04 https://github.com/fepick/whoiam.git
cd whoiam
```

검토 대상 버전은 `release/v0.04`입니다. `main` 검토·통합 후에는 승인된 릴리스 태그를 사용합니다.
저장소 접근 권한이 없는 사용자에게는 Git 이력이 없는 검증된 소스 ZIP을 전달합니다.

## 설치와 실행

프로젝트 폴더에서 PowerShell로 실행합니다. 스크립트는 프로젝트의 `.venv`만 만들고 의존성을 설치합니다.
운영 데이터·OS 키·로그인 자동 실행·방화벽·실행 정책은 설정하지 않으며 서버를 자동 실행하지 않습니다.

```powershell
powershell -NoProfile -File scripts/Setup-Whoiam.ps1 -CheckOnly
powershell -NoProfile -File scripts/Setup-Whoiam.ps1
.\.venv\Scripts\python.exe -m apps.server --demo=True
```

데모는 가상 데이터를 메모리에서만 유지합니다. 브라우저에서 업무·근무·보고 화면을 확인한 뒤 설정의 앱 종료 또는 터미널의 Ctrl+C로 종료합니다.
다른 Python을 지정하려면 `-PythonExecutable 'C:\Tools\Python\python.exe'`처럼 실행 파일 경로를 넘깁니다.
PowerShell 실행 정책이 스크립트를 차단하면 정책을 우회하지 말고 다음 명령을 직접 실행합니다.

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m apps.server --demo=True
```

실제 사용은 데모를 종료한 후 다음으로 실행합니다.

```powershell
.\.venv\Scripts\python.exe -m apps.server
```

서버가 **자동으로 연 브라우저**에서 직접 잠금을 해제합니다. 주소만 입력했을 때 접속 권한 오류가 나오면 서버를 다시 실행해 열린 창을 사용합니다.
기본 주소는 `http://127.0.0.1:4173`입니다. 이미 다른 서버가 실행 중이면 먼저 정상 종료합니다.
암호문은 `%LOCALAPPDATA%\Whoiam\.private\production\`, 키는 해당 Windows 계정의 OS 보안 저장소에 각각 생성됩니다.
다른 PC에 새로 설치하면 빈 보관함으로 시작합니다. 기존 기록 이전은 [백업·복구 절차](personal-service.md#os-키-유실새-pc-복구)를 사용자가 직접 수행합니다.
코드 업데이트 후에는 서버를 종료하고 다시 실행해야 새 API가 반영됩니다.

## CLI 코딩 AI에게 붙여 넣을 설치 요청

AI CLI의 설치와 계정 로그인은 미리 완료합니다. 아래 요청은 특정 AI 제품에 종속되지 않습니다.
ZIP을 풀거나 저장소를 clone한 다음, **프로젝트 폴더에서** AI CLI를 열고 이 블록을 붙여 넣습니다.

```text
이 폴더의 whoiam을 다른 Windows PC에서 실행할 수 있도록 설치해 줘.

1. AGENTS.md와 docs/setup.md를 읽고 기존 변경을 보존해라.
2. Git checkout이면 release/v0.04인지 확인하고 다르면 그 상태를 먼저 알려라.
3. Python 3.11 이상을 확인하고 scripts/Setup-Whoiam.ps1로 .venv와 requirements.txt를 설치해라.
   정책이 스크립트를 차단하면 문서의 직접 명령을 사용해라. 실행 정책·방화벽을 변경하지 마라.
   Python이 없으면 설치해야 할 항목을 알려라. 기존 Python이나 가상환경을 삭제하지 마라.
4. pip check를 통과시키고 --demo=True --open_browser=False --port=4174로 메모리 데모를 검증해라.
   4174가 사용 중이면 다른 프로그램을 종료하지 말고 비어 있는 포트를 선택해라.
5. 데모를 정상 종료하고 실제 실행 명령을 알려라.

실제 .private, 운영 DB, OS 자격증명, 로그인 정보, 복구 파일은 읽지 마라.
실제 모드 잠금 해제·기존 데이터 복구·AI/GitHub 로그인은 내가 직접 한다.
Git push, 외부 배포, 로그인 자동 실행 등록은 하지 마라.
성공한 점검과 설치가 막힌 항목을 구분해서 보고해라.
```

## 개발자 설치

Git clone에서 `scripts/Setup-Whoiam.ps1 -Dev`로 개발 의존성까지 설치합니다.
Git·PowerShell이 준비된 환경에서 `scripts/Install-GitHooks.ps1`로 훅을 설치하고 [개발 안내](../CONTRIBUTING.md)의 검증을 따릅니다.
배포 ZIP은 실행용 파일만 포함하므로 개발·전체 테스트에는 Git checkout을 사용합니다.
