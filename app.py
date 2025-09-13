import os, importlib, asyncio
from urllib.parse import urlparse

from concurrent.futures import ThreadPoolExecutor

import yaml

with open("config.yml", "r") as f:
    config = yaml.load(f, yaml.Loader)

from fastapi import FastAPI, Request
from fastapi import status, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
from pydantic import ValidationError
import uvicorn
import aioboto3
import asyncpg

debug = True


class ChartFastAPI(FastAPI):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.debug = kwargs["debug"]

        self.executor = ThreadPoolExecutor(max_workers=16)

        self.config = kwargs["config"]
        self.s3_session = aioboto3.Session(
            aws_access_key_id=config["s3"]["access-key-id"],
            aws_secret_access_key=config["s3"]["secret-access-key"],
            region_name=config["s3"]["location"],
        )
        self.s3_client_options = {
            "service_name": "s3",
            "endpoint_url": config["s3"]["endpoint"],
        }
        self.s3_bucket = config["s3"]["bucket-name"]

        self.auth = config["server"]["auth"]
        self.auth_header = config["server"]["auth-header"]

        self.db: asyncpg.Pool | None = None

        self.exception_handlers.setdefault(HTTPException, self.http_exception_handler)

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
        elif exc.status_code == 422 and not debug:
            # return actual error for debug lol
            return JSONResponse(
                content={"message": "Bad request. This is probably not your fault."},
                status_code=400,
            )
        else:
            if debug:
                raise exc
            return JSONResponse(content={}, status_code=exc.status_code)


VERSION_REGEX = r"^\d+\.\d+\.\d+$"


app = ChartFastAPI(debug=debug, config=config)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(SessionMiddleware, secret_key=config["server"]["secret-key"])
if not debug:
    domain = urlparse(config["server"]["base-url"]).netloc
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=[domain])


@app.middleware("http")
async def force_https_redirect(request, call_next):
    response = await call_next(request)

    if config["server"]["force-https"] and not debug:
        if response.headers.get("Location"):
            response.headers["Location"] = response.headers.get("Location").replace(
                "http://", "https://", 1
            )

    return response


# app.mount("/static", StaticFiles(directory="static"), name="static")
# templates = Jinja2Templates(directory="templates")


import os
import importlib


def loadRoutes(folder, cleanup: bool = True):
    global app
    """Load Routes from the specified directory."""

    routes = []

    def traverse_directory(directory):
        for root, dirs, files in os.walk(directory, topdown=False):
            for file in files:
                if not "__pycache__" in root and os.path.join(root, file).endswith(
                    ".py"
                ):
                    route_name: str = (
                        os.path.join(root, file)
                        .removesuffix(".py")
                        .replace("\\", "/")
                        .replace("/", ".")
                    )

                    # Check if the route is dynamic or static
                    if "{" in route_name and "}" in route_name:
                        routes.append(
                            (route_name, False)
                        )  # Dynamic route (priority lower)
                    else:
                        routes.append(
                            (route_name, True)
                        )  # Static route (priority higher)

    traverse_directory(folder)

    # Sort the routes: static first, dynamic last. Deeper routes (subdirectories) have higher priority.
    # We are sorting by two factors:
    # 1. Whether the route is static (True first) or dynamic (False second).
    # 2. Depth of the route (deeper subdirectory routes come first).
    routes.sort(key=lambda x: (not x[1], x[0]))  # Static first, dynamic second

    for route_name, is_static in routes:
        route = importlib.import_module(route_name)
        if hasattr(route, "donotload") and route.donotload:
            continue

        route_version = route_name.split(".")[0]
        route_name_parts = route_name.split(".")

        # it's the index for the route
        if route_name.endswith(".index"):
            del route_name_parts[-1]

        route_name = ".".join(route_name_parts)

        route.router.prefix = "/" + route_name.replace(".", "/")
        route.router.tags = (
            route.router.tags + [route_version]
            if isinstance(route.router.tags, list)
            else [route_version]
        )

        route.setup()
        app.include_router(route.router)

        print(f"[API] Loaded Route {route_name}")


async def startup_event():
    await app.initdb()
    folder = "api"
    if len(os.listdir(folder)) == 0:
        print("[WARN] No routes loaded.")
    else:
        loadRoutes(folder)
        print("Routes loaded!")


app.add_event_handler("startup", startup_event)

# uvicorn.run("app:app", port=port, host="0.0.0.0")


async def start_fastapi():
    config_server = uvicorn.Config(
        "app:app",
        host="0.0.0.0",
        port=config["server"]["port"],
        workers=9,
        # log_level="critical",
    )
    server = uvicorn.Server(config_server)
    await server.serve()


if __name__ == "__main__":
    raise SystemExit("Please run main.py")
