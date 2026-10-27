# 개발 규칙과 작업 방법

에이전트와 개발자는 [AGENTS.md](AGENTS.md)의 구조·민감정보 정책을 함께 따릅니다.
현재 로컬 서버·업무 모듈·웹 콘솔을 구현했으며 아래 Python 규칙을 적용합니다.

## 브랜치와 커밋

- 항상 작업 브랜치에서 작업합니다. 예: `feat/attendance`, `fix/report-layout`, `docs/project-conventions`.
- `main`에 직접 커밋하거나 push하지 않습니다. 변경은 작업 브랜치에서 검토합니다.
- `main` 커밋의 예외는 프로젝트 담당자가 함께 있으면서 내용을 직접 확인한 경우에만 허용합니다. 에이전트는 이 조건을 임의로 판단해 실행하지 않습니다.
- 작업 브랜치에서는 검토 가능한 단계마다 커밋하고 push합니다. 사용자가 중지한 작업은 실행하지 않습니다.
- 커밋 메시지는 짧은 제목 한 줄이며 본문은 없습니다. 기본 관례는 `feat(scope): …`, `fix(scope): …`, `docs(scope): …`입니다.
- 위 접두사는 기본 관례이며 커밋 메시지 검사 도구로 강제하지 않습니다. 과거 이력을 변경하지 않습니다.
- 기존 미커밋 작업은 보존하고, 현재 작업과 관련 있는 파일·변경만 커밋합니다.

```powershell
git switch -c feat/example
pre-commit run --all-files
git add <검토한-파일>
git commit -m "feat(example): 기능 추가"
git push -u origin feat/example
```

## Python 컨벤션

| 항목 | 규칙 |
| --- | --- |
| 기준 버전 | Python 3.11 |
| 포맷 | black, 줄 길이 88 |
| import | isort, `profile=black`, 줄 길이 88 |
| 포맷 제외 | `gas_detector/dev/` |
| 타입 힌트 | 모든 함수·메서드의 매개변수와 반환값. `self`·`cls`는 생략 가능 |
| 주석 | 한국어, 자명하지 않은 로직에만 작성 |
| 상수 | 모듈 위쪽, 설명은 `#:` 주석 |
| 로깅 | `from loguru import logger` |
| CLI | `fire` |
| 테스트 | pytest, `tests/`, 로컬에서 실행 |
| 도입하지 않는 도구 | flake8, 정적 타입 검사, CI 자동 pytest |

로그에는 실제 로그인·카드·개인정보·세션을 출력하지 않습니다.
loguru·fire는 Python 실행 모듈이 생길 때 해당 모듈의 실행 의존성에 선언합니다.
현재 Python 규칙이 웹·MCU의 전체 기술 스택을 정하지는 않습니다. JavaScript·PowerShell 등 다른 언어의 포맷 도구는 별도 결정합니다.

```python
#: 한 주의 근무시간 상한을 분 단위로 표현한다.
WEEKLY_LIMIT_MINUTES = 52 * 60


def remaining_minutes(worked_minutes: int) -> int:
    return max(0, WEEKLY_LIMIT_MINUTES - worked_minutes)
```

## 개발 환경과 커밋 전 검사

Python 3.11 기반 `rpi` conda 환경을 사용합니다. 기존 환경이 있으면 다시 만들지 않습니다.

```powershell
conda create -n rpi python=3.11
conda activate rpi
python -m pip install -r requirements-dev.txt
pwsh -NoProfile -File scripts/Install-GitHooks.ps1
pre-commit run --all-files
```

`pyproject.toml`이 black·isort 설정의 기준이며 `.pre-commit-config.yaml`에서 같은 도구 버전을 고정합니다.
isort 다음 black 순서로 실행합니다. `gas_detector/dev/`는 현재 저장소에 없지만 요청한 제외 경로를 설정에 유지합니다.
`.private/`와 임시 디렉터리는 포맷 대상에도 포함하지 않습니다.

이 저장소는 `core.hooksPath=.githooks`를 사용합니다. **`pre-commit install`로 별도 훅을 설치하거나 기존 훅을 덮어쓰지 않습니다.**
기존 `pre-commit` Git 훅이 민감 경로 검사 후 `pre-commit run --all-files`를 실행합니다.
도구가 없거나 검사가 실패하면 커밋을 중단합니다. 처음 실행할 때 포맷 도구의 격리 환경을 다운로드하므로 네트워크 연결이 필요합니다.
Python 파일이 없으면 포맷 검사는 정상적으로 건너뜁니다. 이는 Python 코드의 검증을 완료했다는 뜻이 아닙니다.
포맷 도구는 타입 힌트·주석 언어·로깅 선택을 검사하지 않으므로 코드 검토에서 확인합니다.

```powershell
pre-commit run --all-files
conda run -n rpi python -m pytest
pwsh -NoProfile -File scripts/Check-SensitivePaths.ps1 -IncludeHistory
```

pytest는 Python 코드와 테스트가 생기면 관련 변경을 로컬에서 검증할 때 실행합니다.
`pyproject.toml`의 테스트 수집 경로는 `tests/`로 제한하며 `.private/`를 검색하지 않습니다.
현재 저장소의 Python 테스트는 암호화·접근 경계·업무 계산·트랜잭션·API 흐름을 가상 데이터로 검증합니다.
OS 보안 저장소는 가짜 백엔드로 검증하며 실제 자격증명에 접근하지 않습니다. CI 자동 pytest는 추가하지 않습니다.
기존 민감 경로 검사는 로컬 훅과 GitHub CI에 유지합니다. 보호 규칙을 변경하면 `scripts/Test-SensitivePaths.ps1`도 실행합니다.

도구 설정 참고: [black의 pre-commit 연동](https://black.readthedocs.io/en/stable/integrations/source_version_control.html),
[isort의 black 호환 설정](https://isort.readthedocs.io/en/latest/configuration/black_compatibility.html),
[pre-commit 사용법](https://pre-commit.com/#usage).
