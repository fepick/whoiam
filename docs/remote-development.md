# Tactic Remote로 원격 개발하기

Tactic Remote의 Windows companion과 iPhone·iPad 앱으로 PC의 코딩 에이전트를 조작한다.
VS Code에서 연 `whoiam` 폴더를 Tactic Remote에서도 프로젝트로 선택한다.
같은 폴더의 파일 변경은 VS Code에 반영되지만 현재 IDE 대화의 실시간 공유·인계는 검증하지 않았다.
동일 브랜치의 파일을 PC와 휴대폰 에이전트에서 동시에 수정하지 않는다.

## PC 준비

1. [공식 다운로드](https://tacticremote.com/download/)에서 Windows companion을 설치한다.
   2026-10-28 확인한 배포본은 1.12.0 Preview이며 디지털 서명이 없다.
2. [공식 Codex CLI](https://learn.chatgpt.com/docs/codex/cli)를 현재 Windows 사용자에게 설치한다.
   VS Code 확장 내부 실행 파일은 일반 앱의 PATH에 등록되지 않을 수 있으므로 독립 CLI 설치를 권장한다.
   에이전트 로그인은 PC에서 직접 완료한다.
3. 프로젝트의 Python 개발 환경을 `CONTRIBUTING.md`에 따라 준비한다.
4. PowerShell 7(`pwsh`)을 사용해 VS Code 터미널에서 다음 명령으로 companion을 실행한다.

```powershell
pwsh -NoProfile -File scripts/Start-TacticRemote.ps1 -Preview
pwsh -NoProfile -File scripts/Start-TacticRemote.ps1
```

실행 스크립트는 공식 Windows 독립 설치본의 `%LOCALAPPDATA%\Programs\OpenAI\Codex\bin\codex.exe`를 우선한다.
없으면 PATH의 `codex.exe`, 설치된 VS Code Codex 확장 순서로 찾는다.
프로젝트 `.venv/Scripts`가 있으면 companion의 실행 환경에 추가한다.
Claude Code가 `%USERPROFILE%\.local\bin\claude.exe`에 설치되어 있으면 이 경로도 추가한다.
CLI 설치 전부터 켜져 있던 IDE에서도 새 경로를 사용할 수 있도록 현재 등록된 사용자 PATH를 읽어 실행 환경에 반영한다.
Codex 런타임에 포함된 PowerShell이 있고 `pwsh` 명령이 없으면 그 경로도 추가한다.
전역 PATH·로그인 정보·방화벽·자동 시작 설정은 수정하지 않는다.
IDE나 개발 도구가 설정한 `ELECTRON_RUN_AS_NODE`는 companion을 실행하는 동안만 제거하고 호출한 셸에서는 복구한다.
이 값이 `1`이면 Electron 실행 파일이 일반 앱 대신 Node 모드로 시작해 창 없이 종료될 수 있다.
이 설명은 저장소의 실행 스크립트에 해당한다. 공식 Codex CLI 설치 프로그램은 사용자 PATH에 CLI 경로를 등록한다.
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
3. PC 앱의 설정에서 `Allowed Base Path` 옆 `Browse`로 이 checkout 폴더를 선택하고 저장한다.
   예를 들어 checkout이 `C:\code\whoiam`이면 이 경로를 지정한다. 허용 범위를 드라이브 전체로 넓히지 않는다.
4. iPhone·iPad에서 같은 Tactic 계정으로 로그인한다.
5. `Your Computers`에서 이 PC를 선택한다.
6. 프로젝트 폴더를 선택하고 에이전트를 Codex로 지정한다.
7. 첫 요청은 `AGENTS.md만 읽고 프로젝트 개발 규칙을 요약해 줘. 파일은 수정하지 마.`로 연결을 확인한다.

연결은 되지만 휴대폰의 폴더 목록에서 checkout이 보이지 않으면 PC의 `Allowed Base Path`를 확인한다.
이 설정은 앱 실행 시의 작업 디렉터리와 별개다. 실행 스크립트는 허용 경로 설정을 변경하지 않는다.
저장 후 휴대폰에서 연결을 다시 열고 폴더 목록을 새로고침한다. 앱이 재시작을 요구하면 companion을 재시작한다.

Tactic 계정 로그인과 Codex 로그인은 별개다. PC companion이 실행 중이어야 하며,
PC가 절전 중이거나 꺼져 있으면 연결할 수 없다.
로컬 QR 연결은 같은 네트워크에서 사용하며 외부 Relay 연결을 대신하지 않는다.
이 문서와 실행 스크립트는 설치·실행 준비만 다룬다. 휴대폰의 실제 연결 성공은 앱에서 확인해야 한다.

## Codex를 찾을 수 없다는 오류

Relay 연결 성공과 Codex 실행 파일 검색은 별개다.
독립 CLI 설치 후에도 이미 켜진 companion은 이전 PATH를 사용하거나 기존 검색 결과를 유지할 수 있다.

1. Tactic Remote의 종료 기능으로 앱을 완전히 종료한다. 창 닫기가 트레이 최소화라면 트레이에서도 종료한다.
2. `Start-TacticRemote.ps1 -Preview`에서 독립 CLI 경로가 표시되는지 확인한다.
3. `Start-TacticRemote.ps1`로 다시 실행하고 휴대폰을 재연결한다.
4. Codex 에이전트를 다시 선택해 시작한다.

실행 파일의 위치는 다음 명령으로 인증·세션 내용을 읽지 않고 확인할 수 있다.

```powershell
& "$env:LOCALAPPDATA\Programs\OpenAI\Codex\bin\codex.exe" --version
```

이후 로그인 요청이 표시되면 PC에서 직접 로그인한다. 로그인 파일을 복사하거나 토큰을 원격 대화에 붙이지 않는다.

## Claude Code CLI를 함께 사용하기

[Claude Code 공식 Windows 설치 안내](https://code.claude.com/docs/en/setup#install-on-native-windows)에 따라
네이티브 CLI를 설치하고 `%USERPROFILE%\.local\bin`을 사용자 PATH에 등록한다.
설치와 로그인은 별개이며 에이전트 사용 전 PC에서 직접 로그인해야 한다.

```powershell
where.exe claude
claude --version
```

Tactic Remote의 서버 진단은 여러 도구를 한 번에 검사한다. Claude·Codex 중 사용할 에이전트가 검색되는지 확인한다.
Amp는 해당 에이전트를 사용할 때, Cloudflare는 해당 터널 방식을 사용할 때만 필요하다.
PATH를 바꾼 뒤에는 Tactic Remote를 트레이의 종료 기능까지 사용해 완전히 종료하고 재실행한 다음 서버 진단을 다시 실행한다.

## 프로젝트 데이터 경계

작업 브랜치·검증·커밋 규칙은 원격에서도 `AGENTS.md`를 그대로 따른다.
이 연결은 개발용이며 운영 웹 서버를 공개하는 설정이 아니다.
운영 데이터 홈을 프로젝트로 선택하거나 `.private/`·복구 파일·키를 업로드하지 않는다.
계정 토큰·페어링 QR·세션 출력은 Git이나 문서에 저장하지 않는다.
