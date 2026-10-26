"""입력 검증과 시간 표현. 오류에 입력 원문을 포함하지 않는다."""

from datetime import date, datetime, timezone
from typing import Any
from uuid import uuid4
from zoneinfo import ZoneInfo

#: 업무 날짜와 주간 경계를 계산하는 기본 시간대.
SEOUL = ZoneInfo("Asia/Seoul")
#: 모듈 명령 및 조회의 JSON 표현.
Json = dict[str, Any]


class DomainError(Exception):
    def __init__(self, message: str, status: int = 400) -> None:
        super().__init__(message)
        self.status = status


def uid() -> str:
    return uuid4().hex


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def text(data: Json, key: str, maximum: int = 240, required: bool = True) -> str:
    value = data.get(key, "")
    if not isinstance(value, str) or len(value) > maximum:
        raise DomainError("문자열 입력의 형식과 길이를 확인해주세요.")
    value = value.strip()
    if required and not value:
        raise DomainError("필수 항목을 입력해주세요.")
    return value


def integer(data: Json, key: str, low: int = 0, high: int = 10**9) -> int:
    value = data.get(key)
    if type(value) is not int or not low <= value <= high:
        raise DomainError("수량·시간·금액은 허용 범위의 정수로 입력해주세요.")
    return value


def choice(data: Json, key: str, values: tuple[str, ...]) -> str:
    value = text(data, key, 64)
    if value not in values:
        raise DomainError("허용된 선택값을 사용해주세요.")
    return value


def day(value: str) -> date:
    try:
        parsed = date.fromisoformat(value)
        if parsed.isoformat() != value:
            raise ValueError
        return parsed
    except (ValueError, TypeError):
        raise DomainError("날짜를 YYYY-MM-DD 형식으로 입력해주세요.") from None


def moment(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value)
        if parsed.tzinfo is None:
            raise ValueError
        return parsed.astimezone(timezone.utc)
    except (ValueError, TypeError):
        raise DomainError("시간대가 포함된 날짜와 시각을 입력해주세요.") from None


def fields(data: Json, allowed: set[str]) -> None:
    if not isinstance(data, dict) or set(data) - allowed:
        raise DomainError("지원하지 않는 입력 항목이 있습니다.")
