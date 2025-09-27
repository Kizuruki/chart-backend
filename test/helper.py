from typing import Callable, Optional, Any, Protocol, Generator, IO

import requests

print("NOTE: secret-key in local config.yaml should match server's secret-key")
print("do NOT use this with prod server")

from helpers.config_loader import get_config
config = get_config()

class Body:
    def __init__(
        self, 
        params: Optional[dict[str, Any]] = None, 
        data: Optional[dict[Any, Any]] = None, 
        files: Optional[dict[str, tuple[str, IO, str]]] = None, 
        format_path: Optional[dict[str, str]] = None, 
        use_private_auth: bool = False
    ):
        self.params = params
        self.data = data
        self.files = files
        self.format_path = format_path
        self.use_private_auth = use_private_auth

class _RoutedFunction(Protocol):
    id: str

    def __call__(self, *args: Any, **kwargs: Any) -> Generator[
        Optional[Body],
        requests.Response,
        Any
    ]:
        ...

class After:
    def __init__(self, after: _RoutedFunction, value: Optional[str] = None, use_for_auth: bool = False):
        self.id = after.id
        self.value = value
        self.use_for_auth = use_for_auth

class _SkipRoute(Exception): ...

class _Route:
    def __init__(self, path: str, func: _RoutedFunction, method: str, dependencies: list[After]):
        self.path = path
        self.func = func
        self.method = method
        self.dependencies = dependencies

class Test:
    def __init__(self):
        self.routes: dict[str, _Route] = {}

    def route(self, path: str, method: str, dependencies: Optional[list[After]] = None):
        if not dependencies:
            dependencies = []

        def decorator(func: Callable) -> _RoutedFunction:
            func.id = f"{method}+{path}"
            self.routes[func.id] = _Route(path, func, method, dependencies)

            return func
        
        return decorator
    
    def check(self, route: _RoutedFunction):
        return route.id in self.processed_routes and route.id not in self.failed_routes

    def start(self):
        self.processed_routes: list[str] = []
        self.failed_routes: list[str] = []
        ret_vals: dict[str, Any] = {}
        skipped_routes = 0

        self.url = input("Server URL (with scheme and no trailing slashes) (prod: https://sono_api.untitledcharts.com/api): ")
        self.sonolus_url = input("Sonoserver URL (WITHOUT scheme and no trailing slashes) (untitledcharts.com/sonolus): ")
        print(f"Running test for {len(self.routes)} routes...")

        for pos, (id, route) in enumerate(self.routes.items()):
            print(f"[{pos+1}/{len(self.routes)}] {id} |", end=" ")
            kwargs = {}
            auth = None

            try:
                for dependency in route.dependencies:
                    if dependency.id not in self.processed_routes:
                        print("\n")
                        raise Exception(f"Dependency {dependency.id} is not yet processed")
                
                    if dependency.id in self.failed_routes:
                        print(f"FAILED | Dependency {dependency.id} failed, skipping this route")
                        raise _SkipRoute()
                    
                    if dependency.value or dependency.use_for_auth:
                        if dependency.id not in ret_vals:
                            raise Exception(f"Dependency {dependency.id} returned nothing, but function requires value \"{dependency.value if dependency.value else ""}\"")
                        
                        if dependency.value:
                            kwargs[dependency.value] = ret_vals[dependency.id]
                        else:
                            auth = ret_vals[dependency.id]

                try:
                    generator = route.func(**kwargs)
                    body = next(generator)

                    if not body:
                        body = Body()

                    headers = {}
                    if body.use_private_auth:
                        headers[config["server"]["auth-header"]] = config["server"]["secret-key"]
                    elif auth:
                        headers[config["server"]["auth-header"]] = auth

                    path = route.path
                    if body.format_path:
                        for key, val in body.format_path.items():
                            path = path.replace("{" + key + "}", val)

                    response = requests.request(route.method, self.url + path, params=body.params, data=body.data, headers=headers, files=body.files)

                    if not response.ok:
                        print(f"FAILED | Request status {response.status_code}")
                        self.failed_routes.append(id)
                        self.processed_routes.append(id)
                        continue

                    generator.send(response)

                    try:
                        ret_vals[id] = next(generator)
                    except StopIteration:
                        pass

                    print("OK")
                    self.processed_routes.append(id)

                except Exception as e:
                    if isinstance(e, _SkipRoute):
                        raise

                    print(f"FAILED | Exception: {type(e).__name__}: {e}")
                    self.failed_routes.append(id)
                    self.processed_routes.append(id)
                    continue

            except _SkipRoute:
                skipped_routes += 1
                self.failed_routes.append(id)
                self.processed_routes.append(id)
                continue

        print(f"{len(self.failed_routes)}/{len(self.routes)} ({round(len(self.failed_routes) / len(self.routes) * 100, 2)}%) failed, {skipped_routes} of them were skipped")