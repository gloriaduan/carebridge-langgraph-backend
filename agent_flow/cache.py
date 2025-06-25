import redis
import os
import json
from typing import Optional, Any
from dotenv import load_dotenv

load_dotenv()


class RedisCache:
    def __init__(self):
        self.client = None
        host = os.getenv("REDIS_HOST")
        port = os.getenv("REDIS_PORT")
        password = os.getenv("REDIS_PASSWORD")

        if host and port and password:
            self.client = redis.Redis(
                host=host,
                port=int(port),
                password=password,
                decode_responses=True,
                ssl=True,
            )
