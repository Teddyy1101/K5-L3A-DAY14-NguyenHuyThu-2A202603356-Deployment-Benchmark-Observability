from datetime import datetime, timedelta, timezone
from decimal import Decimal

from fastapi import HTTPException

from app.config import settings
from app.redis_client import r


PRICE_INPUT_PER_1K = Decimal("0.00015")
PRICE_OUTPUT_PER_1K = Decimal("0.0006")
NANO_USD_PER_USD = 1_000_000_000


def daily_key(now: datetime) -> str:
    return f"day14:cost:{now.date().isoformat()}"


def check_budget() -> None:
    key = daily_key(datetime.now(timezone.utc))
    spent = int(r.get(key) or 0)
    if spent >= settings.daily_budget_usd * NANO_USD_PER_USD:
        raise HTTPException(status_code=402, detail="Daily budget exceeded")


def record_cost(input_tokens: int, output_tokens: int) -> float:
    cost = (input_tokens * PRICE_INPUT_PER_1K + output_tokens * PRICE_OUTPUT_PER_1K) / 1000
    cost_nanos = int(cost * NANO_USD_PER_USD)
    now = datetime.now(timezone.utc)
    key = daily_key(now)
    midnight = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    with r.pipeline() as pipe:
        pipe.incrby(key, cost_nanos)
        pipe.expireat(key, midnight)
        pipe.execute()
    return float(cost)
