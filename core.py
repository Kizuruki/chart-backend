import asyncio, json, hashlib, base64, hmac
from fastapi import FastAPI, Request
from fastapi import status, HTTPException
from fastapi.responses import JSONResponse
from helpers.config_loader import ConfigType
from concurrent.futures import ThreadPoolExecutor
import aioboto3
import asyncpg


class ChartFastAPI(FastAPI):
    def __init__(self, config: ConfigType, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.config = config
        self.debug = config.get("debug", False)

        self.executor = ThreadPoolExecutor(max_workers=16)

        self.s3_session_getter = lambda: aioboto3.Session(
            aws_access_key_id=config["s3"]["access-key-id"],
            aws_secret_access_key=config["s3"]["secret-access-key"],
            region_name=config["s3"]["location"],
        ).client(
            service_name="s3",
            endpoint_url=self.config["s3"]["endpoint"],
        )

        self.s3_bucket = self.config["s3"]["bucket-name"]
        self.s3_asset_base_url = self.config["s3"]["base-url"]

        self.auth = self.config["server"]["auth"]
        self.auth_header = self.config["server"]["auth-header"]

        self.token_secret_key: str = self.config["server"]["token-secret-key"]

        self.db: asyncpg.Pool | None = None

        self.exception_handlers.setdefault(HTTPException, self.http_exception_handler)

    def decode_key(self, session_key: str) -> dict:
        try:
            encoded_data, signature = session_key.rsplit(".", 1)
            recalculated_signature = hmac.new(
                self.token_secret_key.encode(), encoded_data.encode(), hashlib.sha256
            ).hexdigest()
            if recalculated_signature == signature:
                decoded_data = base64.urlsafe_b64decode(encoded_data).decode()
                return json.loads(decoded_data)
        except:
            pass
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Invalid session token."
        )

    async def initdb(self):
        psql_config = self.config["psql"]

        self.db = await asyncpg.create_pool(
            host=psql_config["host"],
            user=psql_config["user"],
            database=psql_config["database"],
            password=psql_config["password"],
            port=psql_config["port"],
            min_size=psql_config["pool-min-size"],
            max_size=psql_config["pool-max-size"],
            ssl="disable",  # XXX: todo, im lazy :(
        )

    async def run_blocking(self, func, *args, **kwargs):
        return await asyncio.get_event_loop().run_in_executor(
            self.executor, lambda: func(*args, **kwargs)
        )

    async def http_exception_handler(self, request: Request, exc: HTTPException):
        if exc.status_code < 500 and exc.status_code != 422:
            return JSONResponse(
                content={"message": exc.detail}, status_code=exc.status_code
            )
        elif exc.status_code == 422 and not self.debug:
            # return actual error for debug lol
            return JSONResponse(
                content={"message": "Bad request. This is probably not your fault."},
                status_code=400,
            )
        else:
            if self.debug:
                raise exc
            return JSONResponse(content={}, status_code=exc.status_code)
