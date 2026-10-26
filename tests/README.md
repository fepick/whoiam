# Python 테스트

pytest 테스트는 이 디렉터리에 `test_*.py` 형태로 추가합니다.
아직 Python 실행 코드와 테스트는 없습니다. 빈 테스트를 성공한 검증으로 보고하지 않습니다.

```powershell
conda run -n rpi python -m pytest
```

테스트에는 가상 데이터만 사용하고 `.private/`의 실제 운영 데이터는 읽지 않습니다.
CI에서 pytest를 자동 실행하지 않습니다. 기존 민감 경로 정책 검증은 `scripts/Test-SensitivePaths.ps1`에서 별도로 유지합니다.
