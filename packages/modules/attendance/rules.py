"""근무 산정 규칙과 중복 없는 제외 구간 계산."""

from datetime import datetime, time, timedelta

from packages.platform.domain import SEOUL, DomainError, Json, fields, text

#: 기존 기록의 산정 방식을 유지하다가 사용자가 명시적으로 규칙을 켠다.
DEFAULT_RULES = {
    "enabled": False,
    "early_enabled": True,
    "earliest_start": "08:00",
    "lunch_enabled": True,
    "lunch_start": "12:00",
    "lunch_end": "13:00",
    "preparation_enabled": True,
    "preparation_start": "17:00",
    "preparation_end": "17:30",
}


def validate_rules(data: Json) -> Json:
    fields(data, set(DEFAULT_RULES))
    result = {**DEFAULT_RULES, **data}
    for key, default in DEFAULT_RULES.items():
        if isinstance(default, bool):
            if type(result[key]) is not bool:
                raise DomainError("근무 산정 규칙의 적용 여부를 확인해주세요.")
        else:
            value = text(result, key, 5)
            try:
                parsed = time.fromisoformat(value)
            except ValueError:
                raise DomainError(
                    "규칙 시각은 24시간제 HH:MM으로 입력해주세요."
                ) from None
            if len(value) != 5 or parsed.strftime("%H:%M") != value:
                raise DomainError("규칙 시각은 24시간제 HH:MM으로 입력해주세요.")
    for prefix in ("lunch", "preparation"):
        if result[f"{prefix}_start"] >= result[f"{prefix}_end"]:
            raise DomainError("제외 구간의 종료는 시작보다 늦어야 합니다.")
    return result


def excluded_intervals(
    rules: Json, left: datetime, right: datetime, overtime: bool
) -> list[tuple[datetime, datetime]]:
    if not rules["enabled"]:
        return []
    intervals = []
    current = left.astimezone(SEOUL).date()
    last = right.astimezone(SEOUL).date()
    while current <= last:
        if rules["early_enabled"]:
            intervals.append(
                (
                    datetime.combine(current, time.min, SEOUL),
                    datetime.combine(
                        current, time.fromisoformat(rules["earliest_start"]), SEOUL
                    ),
                )
            )
        for prefix in ("lunch", "preparation"):
            if rules[f"{prefix}_enabled"] and not (
                prefix == "preparation" and overtime
            ):
                intervals.append(
                    tuple(
                        datetime.combine(
                            current,
                            time.fromisoformat(rules[f"{prefix}_{edge}"]),
                            SEOUL,
                        )
                        for edge in ("start", "end")
                    )
                )
        current += timedelta(days=1)
    return intervals


def working_seconds(
    left: datetime, right: datetime, excluded: list[tuple[datetime, datetime]]
) -> int:
    cursor = left
    deducted = 0.0
    for start, end in sorted(excluded):
        start, end = max(start, cursor), min(end, right)
        if end > start:
            deducted += (end - start).total_seconds()
            cursor = end
    return max(0, int((right - left).total_seconds() - deducted))
