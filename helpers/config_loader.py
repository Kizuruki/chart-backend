from typing import TypedDict
import yaml

ConfigTypeServer = TypedDict(
    "ConfigTypeServer",
    {
        "port": int,
        "secret-key": str,
        "base-url": str,
        "force-https": bool,
        "auth": str,
        "auth-header": str,
        "token-secret-key": str,
        "debug": bool
    }
)

ConfigTypeS3 = TypedDict(
    "ConfigTypeS3",
    {
        "base-url": str,
        "endpoint": str,
        "bucket-name": str,
        "access-key-id": str,
        "secret-access-key": str,
        "location": str
    }
)

ConfigTypePsql = TypedDict(
    "ConfigTypePsql",
    {
        "host": str,
        "user": str,
        "database": str,
        "port": int,
        "password": str,
        "pool-min-size": int,
        "pool-max-size": int
    }
)

ConfigType = TypedDict(
    "ConfigType",
    {
        "server": ConfigTypeServer,
        "s3": ConfigTypeS3,
        "psql": ConfigTypePsql,
    }
)

def get_config() -> ConfigType:
    with open("config.yml", "r") as f:
        config = yaml.load(f, yaml.Loader) # NOTE: would be better to use pydantic-config
    return config