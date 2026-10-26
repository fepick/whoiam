# 로컬 실행 기반

Python 3.11+, FastAPI와 SQLite를 사용합니다. 업무 레코드 전체 JSON은 cryptography의 Fernet으로 인증 암호화합니다.
SQLite에 모듈 이름·불투명 ID·레코드 수와 암호문 길이·Fernet 시각 등 메타데이터가 보일 수 있습니다.
각 모듈은 자신의 Repository만 사용하며 코어는 하나의 트랜잭션으로 여러 모듈의 공개 기능을 조합합니다.

키는 keyring의 Windows Credential Locker·macOS Keychain·Secret Service·KWallet 중 지원 백엔드에만 저장합니다.
평문·파일·자동 선택 체인 백엔드는 거부합니다. 기존 DB의 키가 없으면 새 키를 만들지 않습니다.
키 참조는 유휴 15분 후 또는 명시적 잠금 시 해제됩니다. Python 메모리를 완전히 지운다는 보장은 하지 않습니다.

실행 데이터의 기본 위치는 `.private/database/whoiam.sqlite3`이며 실행한 사용자만 OS 키에 접근할 수 있어야 합니다.
같은 OS 계정에서 실행되는 악성 프로세스·관리자·메모리 덤프는 이 경계로 방어하지 못합니다.
웹 서버는 루프백으로만 실행하며 원격 배포·공유 OS 계정·다중 사용자 운영에는 별도의 인증 설계가 필요합니다.

키 백업·교체·다른 PC로의 복원은 아직 제공하지 않습니다. OS 키를 잃으면 데이터 복구가 불가능할 수 있습니다.
검증은 가상 데이터와 임시 DB로만 수행하며 개발 과정에서 `.private/` 및 실제 OS 자격증명을 읽지 않습니다.

참고: [Fernet](https://cryptography.io/en/latest/fernet/), [keyring](https://keyring.readthedocs.io/en/latest/).
