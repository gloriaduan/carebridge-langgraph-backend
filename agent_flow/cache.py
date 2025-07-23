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

        if host and port:
            is_local = host == "localhost" or host == "127.0.0.1"

            # Base connection arguments
            connection_kwargs = {
                "host": host,
                "port": int(port),
                "decode_responses": True,
            }

            # Add production-only arguments
            if not is_local:
                connection_kwargs["password"] = password
                # connection_kwargs["ssl"] = True
                # connection_kwargs["ssl_cert_reqs"] = None

            try:
                print(
                    f"Attempting to connect to Redis ({'local' if is_local else 'cloud'}) at {host}:{port}..."
                )
                self.client = redis.Redis(**connection_kwargs)
                self.client.ping()
                print("Successfully connected to Redis.")
            except redis.exceptions.ConnectionError as e:
                print(
                    f"Could not connect to Redis. Caching will be disabled. Error: {e}"
                )
                self.client = None
        else:
            print("Redis credentials not found. Caching will be disabled.")

    def get(self, key: str) -> Optional[Any]:
        if not self.client:
            return None

        try:
            value = self.client.get(key)
            if value is not None:
                return json.loads(value)
            return None
        except Exception as e:
            print(f"Error retrieving key '{key}' from Redis: {e}")
            return None

    def set(self, key: str, value: Any, expire: Optional[int] = None):
        if not self.client:
            return

        try:
            value_str = json.dumps(value)
            self.client.setex(key, expire, value_str)
        except Exception as e:
            print(f"Error setting key '{key}' in Redis: {e}")


cache = RedisCache()
