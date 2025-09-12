from typing import Tuple


def generate_create_account_query(sonolus_id: int) -> Tuple[str, Tuple]:
    return """
        INSERT INTO accounts (sonolus_id)
        VALUES ($1);
    """, (
        sonolus_id,
    )


def generate_delete_account_query(
    sonolus_id: int, confirm_change: bool = False
) -> Tuple[str, Tuple]:
    if not confirm_change:
        raise ValueError(
            "Deletion not confirmed. Ensure you are deleting the old files from S3 to ensure there is no hanging files."
        )
    return """
        DELETE FROM accounts
        WHERE sonolus_id = $1;
    """, (
        sonolus_id,
    )


def generate_link_discord_id_query(
    sonolus_id: int, discord_id: int
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
    sonolus_id: int, patreon_id: str
) -> Tuple[str, Tuple]:
    return """
        UPDATE accounts
        SET patreon_id = $1, updated_at = CURRENT_TIMESTAMP
        WHERE sonolus_id = $2;
    """, (
        patreon_id,
        sonolus_id,
    )


def generate_set_mod_query(sonolus_id: int, mod_status: bool) -> Tuple[str, Tuple]:
    return """
        UPDATE accounts
        SET mod = $1, updated_at = CURRENT_TIMESTAMP
        WHERE sonolus_id = $2;
    """, (
        str(mod_status).lower(),
        sonolus_id,
    )


def generate_set_banned_query(
    sonolus_id: int, banned_status: bool
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
    sonolus_id: int, cooldown_timestamp: str
) -> Tuple[str, Tuple]:
    return """
        UPDATE accounts
        SET chart_upload_cooldown = $1, updated_at = CURRENT_TIMESTAMP
        WHERE sonolus_id = $2;
    """, (
        cooldown_timestamp,
        sonolus_id,
    )
