# 로컬 서버

Python 3.11+에서 `python -m apps.server`로 실행합니다.
`--demo=True`는 가상 데이터와 메모리 DB를 사용하며 `--port=4173`으로 포트를 지정합니다.
브라우저를 자동으로 엽니다. 자동 열기가 지원되지 않는 환경에서는 브라우저 연결을 지원하는 사용자 세션에서 실행합니다.
테스트용 데모에서는 `--open_browser=False`로 브라우저 실행을 끌 수 있습니다.

실제 모드의 첫 접속 권한은 자동으로 연 창에 fragment로 전달하고 세션 쿠키로 교환합니다.
운영 기본 홈은 `%LOCALAPPDATA%/Whoiam/.private/production/`이며 개발 checkout 밖입니다.
`--profile=development`는 별도 개발 저장소를 사용하고 `--profile=test`는 임시 `--data_home`을 명시해야 합니다.
프로필별 단일 실행 잠금·UUID 키 식별·자동 백업을 사용합니다. 백업·복구·기존 데이터 이전은 [운영 안내](../../docs/personal-service.md)를 따릅니다.
루트 페이지는 허용 목록의 정적 자산만 제공하며 실제 저장 모드에서는 접속만으로 인증되지 않습니다.
잠금 해제 전에는 OS 키나 업무 레코드를 읽지 않습니다. 프로필 폴더의 권한 설정과 단일 실행 잠금 파일은 서버 시작 시 준비합니다.
개발 과정에서는 실제 보관함을 열지 않고 가상 저장소로만 검증합니다.

[API 계약](../../docs/api.md), [민감정보 정책](../../docs/security.md), [실행 기반](../../packages/platform/README.md)을 참고합니다.
