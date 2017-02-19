import redis

from piggy_store.config import config

conn = redis.StrictRedis(
    host = config['redis']['host'],
    port = config['redis']['port'],
    db = config['redis']['database'],
    decode_responses = True
)

