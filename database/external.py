from typing import Tuple

from query import ExecutableQuery, SelectQuery
from helpers.models import ExternalLogin, DBID


def create_external_login(id_key: str) -> SelectQuery[DBID]:
    return SelectQuery(
        DBID,
        """
            INSERT INTO external_login_ids (id_key, expires_at)
            VALUES ($1, CURRENT_TIMESTAMP + INTERVAL '6 minutes')
            RETURNING id_key;
        """,
        id_key
    )


def get_external_login(
    id_key: str, must_be_verified: bool = False
) -> SelectQuery[ExternalLogin]:
    if not must_be_verified:
        return SelectQuery(
            ExternalLogin,
            """
                SELECT * FROM external_login_ids
                WHERE id_key = $1
                AND expires_at >= CURRENT_TIMESTAMP;
            """,
            id_key
        )
    else:
        # NOTE: this doesn't check if the session gets deleted
        # However we do check sessions on any api requests
        # So if it somehow got deleted api will error anyways
        return SelectQuery(
            ExternalLogin,
            """
                SELECT * FROM external_login_ids
                WHERE id_key = $1
                AND expires_at >= CURRENT_TIMESTAMP
                AND session_key IS NOT NULL;
            """,
            id_key
        )


def update_session_key(
    id_key: str, session_key: str
) -> SelectQuery[ExternalLogin]:
    return SelectQuery(
        ExternalLogin,
        """
            UPDATE external_login_ids
            SET 
                session_key = $2,
                expires_at = CURRENT_TIMESTAMP + INTERVAL '30 minutes'
            WHERE id_key = $1
            RETURNING id_key, session_key, expires_at;
        """,
        id_key,
        session_key
    )


def delete_external_login(id_key: str) -> ExecutableQuery:
    return ExecutableQuery(
        """
            DELETE FROM external_login_ids
            WHERE id_key = $1
            AND expires_at >= CURRENT_TIMESTAMP;
        """,
        id_key
    )
