# Python 테스트

pytest 테스트는 이 디렉터리에 `test_*.py` 형태로 추가합니다.
암호문 저장·잠금·키 백엔드 거부·수량·시간·트랜잭션·중복 요청·API 인증·보고 생성을 검증합니다.

```powershell
conda run -n rpi python -m pytest
```

테스트에는 가상 데이터만 사용하고 `.private/`의 실제 운영 데이터는 읽지 않습니다.
CI에서 pytest를 자동 실행하지 않습니다. 기존 민감 경로 정책 검증은 `scripts/Test-SensitivePaths.ps1`에서 별도로 유지합니다.

테스트는 실제 OS 키 저장소 대신 가짜 백엔드를 사용합니다. 브라우저 클릭 검증과 실기기 검증을 대신하지 않습니다.

초기 구현 검증은 Python 3.12.14에서 수행했습니다. Python 3.11 문법과 함수 타입 힌트는 별도로 확인했으며 현재 환경에 `rpi` conda는 없습니다.

Node.js가 설치된 환경에서는 `node --test tests/web/attendance-time.test.cjs`로 웹의 한국 시간·오전/오후 변환과 수동 입력 안내를 검증할 수 있습니다.
이 검사는 브라우저 자동화나 실제 운영 API 연결을 사용하지 않습니다.
