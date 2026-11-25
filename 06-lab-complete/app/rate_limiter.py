from hashlib import sha256
from uuid import uuid4

from fastapi import HTTPException

from app.config import settings
from app.redis_client import r


# Check and reserve a slot in one operation, using Redis time for all workers.
reserve_request = r.register_script("""
local key = KEYS[1]
local limit = tonumber(ARGV[1])
local window_ms = 60000
local clock = redis.call('TIME')
local now_ms = clock[1] * 1000 + math.floor(clock[2] / 1000)

redis.call('ZREMRANGEBYSCORE', key, '-inf', now_ms - window_ms)
if redis.call('ZCARD', key) >= limit then
    local oldest = redis.call('ZRANGE', key, 0, 0, 'WITHSCORES')
    return math.ceil((tonumber(oldest[2]) + window_ms - now_ms) / 1000)
end

redis.call('ZADD', key, now_ms, ARGV[2])
redis.call('PEXPIRE', key, window_ms)
return 0
""")


def check_rate_limit(key: str) -> None:
    key_hash = sha256(key.encode()).hexdigest()
    retry_after = reserve_request(
        keys=[f"day14:rate:{key_hash}"],
        args=[settings.rate_limit_per_minute, uuid4().hex],
    )
    if retry_after:
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded",
            headers={"Retry-After": str(retry_after)},
        )
