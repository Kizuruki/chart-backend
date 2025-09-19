from . import accounts
from . import charts
from . import comments
from . import external
from . import leaderboards

from .query import SelectQuery, ExecutableQuery

from asyncpg import Connection
from typing import TypeVar

T = TypeVar("T")
class DBConnWrapper:
    def __init__(self, conn: Connection):
        self.conn = conn

    async def execute(self, query: ExecutableQuery):
        return await self.conn.execute(query.sql, *query.args)

    async def fetch(self, query: SelectQuery[T]) -> list[T]:
        return map(lambda x: query.model.model_validate(dict(x)), await self.conn.fetch(query.sql, *query.args))
    
    async def fetchrow(self, query: SelectQuery[T]) -> T:
        return query.model.model_validate(dict(await self.conn.fetch(query.sql, *query.args)))