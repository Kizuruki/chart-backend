from datetime import datetime, timedelta

from typing import Tuple, Optional, Literal

"""
sonolus_sessions JSONB

{
    "game": {
        "1": {"session_key": "same as key", "expires": epoch in ms},
        "2": ...,
        "3": ...
    },
    "external": {
        same as above
    }
}
"""

"""
oauth_details JSONB

{
    "service_name": {
        "access_token": "",
        "refresh_token": "",
        "expires_at": 0
    }
}
"""


def generate_add_oauth_query(
    sonolus_id: str,
    access_token: str,
    refresh_token: str,
    expires_at: int,
    service: Literal["discord"],
) -> Tuple[str, Tuple]:
    assert service in ["discord"]
    return f"""
        UPDATE accounts
        SET oauth_details = jsonb_set(
            COALESCE(oauth_details, '{{}}'::jsonb),
            '{{{service}}}',
            to_jsonb($2::jsonb)
        )
        WHERE sonolus_id = $1;
    """, (
        sonolus_id,
        {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "expires_at": expires_at,
        },
    )


def generate_delete_oauth_query(
    sonolus_id: str, service: Literal["discord"]
) -> Tuple[str, Tuple]:
    assert service in ["discord"]
    return f"""
        UPDATE accounts
        SET oauth_details = oauth_details - '{service}'
        WHERE sonolus_id = $1;
    """, (
        sonolus_id,
    )


def generate_get_oauth_query(
    sonolus_id: str, service: Literal["discord"]
) -> Tuple[str, Tuple]:
    assert service in ["discord"]
    return f"""
        SELECT oauth_details->'{service}'
        FROM accounts
        WHERE sonolus_id = $1;
    """, (
        sonolus_id,
    )


def generate_create_account_query(
    sonolus_id: str, sonolus_handle: int
) -> Tuple[str, Tuple]:
    return """
        INSERT INTO accounts (sonolus_id, sonolus_handle)
        VALUES ($1, $2);
    """, (
        sonolus_id,
        sonolus_handle,
    )


def generate_create_account_if_not_exists_and_new_session_query(
    session_key: str,
    sonolus_id: str,
    sonolus_handle: int,
    session_type: str,
    expiry_ms: Optional[int] = 30 * 60 * 1000,
) -> Tuple[str, Tuple]:
    if session_type not in ("game", "external"):
        raise ValueError("invalid session type. must be 'game' or 'external'.")

    expiry_time = int(
        (datetime.now() + timedelta(milliseconds=expiry_ms)).timestamp() * 1000
    )

    query = f"""
    WITH account_creation AS (
        INSERT INTO accounts (sonolus_id, sonolus_handle, sonolus_sessions)
        VALUES (
            $1,
            $2,
            jsonb_build_object('game', '{{}}'::jsonb, 'external', '{{}}'::jsonb)
        )
        ON CONFLICT (sonolus_id) DO NOTHING
    ),
    session_data AS (
        SELECT sonolus_id, sonolus_sessions
        FROM accounts
        WHERE sonolus_id = $1
    ),
    slot_to_use AS (
        SELECT
            sonolus_id,
            CASE
                WHEN sonolus_sessions->'{session_type}'->'1' IS NULL OR
                     (sonolus_sessions->'{session_type}'->'1'->>'expires')::bigint < extract(epoch from now()) * 1000
                THEN '1'
                WHEN sonolus_sessions->'{session_type}'->'2' IS NULL OR
                     (sonolus_sessions->'{session_type}'->'2'->>'expires')::bigint < extract(epoch from now()) * 1000
                THEN '2'
                WHEN sonolus_sessions->'{session_type}'->'3' IS NULL OR
                     (sonolus_sessions->'{session_type}'->'3'->>'expires')::bigint < extract(epoch from now()) * 1000
                THEN '3'
                ELSE (
                    SELECT key
                    FROM jsonb_each(sonolus_sessions->'{session_type}') AS t(key, val)
                    ORDER BY (val->>'expires')::bigint ASC
                    LIMIT 1
                )
            END AS slot
        FROM session_data
    )
    UPDATE accounts a
    SET sonolus_sessions = jsonb_set(
        a.sonolus_sessions,
        array[$3::text, s.slot],
        jsonb_build_object(
            'session_key', $4::text,
            'expires', $5::bigint
        ),
        true
    )
    FROM slot_to_use s
    WHERE a.sonolus_id = s.sonolus_id
    RETURNING $4 AS session_key, $5 AS expires;
    """

    return query, (
        sonolus_id,
        sonolus_handle,
        session_type,
        session_key,
        str(expiry_time),
    )


def generate_get_account_from_session_query(
    sonolus_id: str, session_key: str, session_type: str
) -> Tuple[str, Tuple]:
    assert session_type in ["game", "external"]
    return f"""
        SELECT *
        FROM accounts
        WHERE sonolus_id = $1
          AND EXISTS (
              SELECT 1
              FROM jsonb_each(COALESCE(sonolus_sessions->'{session_type}', '{{}}'::jsonb)) AS sessions(slot, data)
              WHERE data->>'session_key' = $2::text
                AND (data->>'expires')::bigint > EXTRACT(EPOCH FROM NOW()) * 1000
          )
        LIMIT 1;
    """, (
        sonolus_id,
        session_key,
    )


def generate_delete_account_query(
    sonolus_id: str, confirm_change: bool = False
) -> Tuple[str, Tuple]:
    if not confirm_change:
        raise ValueError(
            "Deletion not confirmed. Ensure you are deleting the old chart files from S3 to ensure there is no hanging files."
        )
    return """
        DELETE FROM accounts
        WHERE sonolus_id = $1;
    """, (
        sonolus_id,
    )


def generate_link_discord_id_query(
    sonolus_id: str, discord_id: int
) -> Tuple[str, Tuple]:
    return """
        UPDATE accounts
        SET discord_id = $1, updated_at = CURRENT_TIMESTAMP
        WHERE sonolus_id = $2;
    """, (
        discord_id,
        sonolus_id,
    )


def generate_link_patreon_id_query(
    sonolus_id: str, patreon_id: str
) -> Tuple[str, Tuple]:
    return """
        UPDATE accounts
        SET patreon_id = $1, updated_at = CURRENT_TIMESTAMP
        WHERE sonolus_id = $2;
    """, (
        patreon_id,
        sonolus_id,
    )


def generate_set_mod_query(sonolus_id: str, mod_status: bool) -> Tuple[str, Tuple]:
    return """
        UPDATE accounts
        SET mod = $1, updated_at = CURRENT_TIMESTAMP
        WHERE sonolus_id = $2;
    """, (
        str(mod_status).lower(),
        sonolus_id,
    )


def generate_set_banned_query(
    sonolus_id: str, banned_status: bool
) -> Tuple[str, Tuple]:
    return """
        UPDATE accounts
        SET banned = $1, updated_at = CURRENT_TIMESTAMP
        WHERE sonolus_id = $2;
    """, (
        str(banned_status).lower(),
        sonolus_id,
    )


def generate_update_chart_upload_cooldown_query(
    sonolus_id: str, cooldown_timestamp: str
) -> Tuple[str, Tuple]:
    return """
        UPDATE accounts
        SET chart_upload_cooldown = $1, updated_at = CURRENT_TIMESTAMP
        WHERE sonolus_id = $2;
    """, (
        cooldown_timestamp,
        sonolus_id,
    )
