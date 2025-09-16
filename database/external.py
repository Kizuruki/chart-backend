from typing import Tuple


def generate_create_external_login_query(id_key: str) -> Tuple[str, Tuple]:
    return """
        INSERT INTO external_login_ids (id_key, expires_at)
        VALUES ($1, CURRENT_TIMESTAMP + INTERVAL '6 minutes')
        RETURNING id_key;
    """, (
        id_key,
    )


def generate_get_external_login_query(
    id_key: str, must_be_verified: bool = False
) -> Tuple[str, Tuple]:
    if not must_be_verified:
        return """
            SELECT * FROM external_login_ids
            WHERE id_key = $1
            AND expires_at >= CURRENT_TIMESTAMP;
        """, (
            id_key,
        )
    else:
        # NOTE: this doesn't check if the session gets deleted
        # However we do check sessions on any api requests
        # So if it somehow got deleted api will error anyways
        return """
            SELECT * FROM external_login_ids
            WHERE id_key = $1
            AND expires_at >= CURRENT_TIMESTAMP
            AND session_key IS NOT NULL;
        """, (
            id_key,
        )


def generate_update_session_key_query(
    id_key: str, session_key: str
) -> Tuple[str, Tuple]:
    return """
        UPDATE external_login_ids
        SET 
            session_key = $2,
            expires_at = CURRENT_TIMESTAMP + INTERVAL '30 minutes'
        WHERE id_key = $1
        RETURNING id_key, session_key, expires_at;
    """, (
        id_key,
        session_key,
    )


def generate_delete_external_login_query(id_key: str) -> Tuple[str, Tuple]:
    return """
        DELETE FROM external_login_ids
        WHERE id_key = $1
        AND expires_at >= CURRENT_TIMESTAMP;
    """, (
        id_key,
    )
