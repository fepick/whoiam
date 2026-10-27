# Tactic Remote로 원격 개발하기

Tactic Remote의 Windows companion과 iPhone·iPad 앱으로 PC의 코딩 에이전트를 조작한다.
VS Code에서 연 `whoiam` 폴더를 Tactic Remote에서도 프로젝트로 선택한다.
같은 폴더의 파일 변경은 VS Code에 반영되지만 현재 IDE 대화의 실시간 공유·인계는 검증하지 않았다.
동일 브랜치의 파일을 PC와 휴대폰 에이전트에서 동시에 수정하지 않는다.

## PC 준비

1. [공식 다운로드](https://tacticremote.com/download/)에서 Windows companion을 설치한다.
   2026-10-28 확인한 배포본은 1.12.0 Preview이며 디지털 서명이 없다.
2. Codex CLI 또는 VS Code의 Codex 확장을 설치한다. 에이전트 로그인은 PC에서 직접 완료한다.
3. 프로젝트의 Python 개발 환경을 `CONTRIBUTING.md`에 따라 준비한다.
4. PowerShell 7(`pwsh`)을 사용해 VS Code 터미널에서 다음 명령으로 companion을 실행한다.

```powershell
pwsh -NoProfile -File scripts/Start-TacticRemote.ps1 -Preview
pwsh -NoProfile -File scripts/Start-TacticRemote.ps1
```

실행 스크립트는 PATH의 `codex.exe`를 먼저 찾고, 없으면 설치된 VS Code Codex 확장에서 찾는다.
프로젝트 `.venv/Scripts`가 있으면 companion의 실행 환경에 추가한다.
Codex 런타임에 포함된 PowerShell이 있고 `pwsh` 명령이 없으면 그 경로도 추가한다.
전역 PATH·로그인 정보·방화벽·자동 시작 설정은 수정하지 않는다.
앱이 이미 실행 중이면 앱의 종료 기능으로 완전히 종료한 뒤 스크립트로 다시 실행해야 새 환경이 적용된다.
Tactic Remote에서 작업 디렉터리는 별도로 선택해야 한다.

기본 사용자 설치 경로가 아닌 경우에는 실행 파일 경로를 지정한다.

```powershell
pwsh -NoProfile -File scripts/Start-TacticRemote.ps1 -TacticExecutable 'C:\Tools\Tactic Remote\Tactic Remote.exe' -CodexExecutable 'C:\Tools\Codex\codex.exe'
```

## 계정 연결과 확인

[공식 Windows 연결 안내](https://tacticremote.com/docs/setup/windows-account-relay/)를 따른다.

1. PC 앱의 Account 화면에서 Tactic 계정으로 로그인하고 `Bind this PC`를 선택한다.
2. 외부 접속용 `Tactic Relay`를 켜고 연결 상태를 확인한다.
3. iPhone·iPad에서 같은 Tactic 계정으로 로그인한다.
4. `Your Computers`에서 이 PC를 선택한다.
5. 프로젝트 폴더를 선택하고 에이전트를 Codex로 지정한다.
6. 첫 요청은 `AGENTS.md만 읽고 프로젝트 개발 규칙을 요약해 줘. 파일은 수정하지 마.`로 연결을 확인한다.

Tactic 계정 로그인과 Codex 로그인은 별개다. PC companion이 실행 중이어야 하며,
PC가 절전 중이거나 꺼져 있으면 연결할 수 없다.
로컬 QR 연결은 같은 네트워크에서 사용하며 외부 Relay 연결을 대신하지 않는다.
이 문서와 실행 스크립트는 설치·실행 준비만 다룬다. 휴대폰의 실제 연결 성공은 앱에서 확인해야 한다.

## 프로젝트 데이터 경계

작업 브랜치·검증·커밋 규칙은 원격에서도 `AGENTS.md`를 그대로 따른다.
이 연결은 개발용이며 운영 웹 서버를 공개하는 설정이 아니다.
운영 데이터 홈을 프로젝트로 선택하거나 `.private/`·복구 파일·키를 업로드하지 않는다.
계정 토큰·페어링 QR·세션 출력은 Git이나 문서에 저장하지 않는다.
