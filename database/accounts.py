def generate_create_account_query(sonolus_id: int) -> str:
    # The 'created_at' and 'updated_at' fields are automatically set to CURRENT_TIMESTAMP by default
    return f"""
        INSERT INTO accounts (sonolus_id)
        VALUES (
            {sonolus_id}
        );
    """


def generate_delete_account_query(sonolus_id: int) -> str:
    return f"""
        DELETE FROM accounts
        WHERE sonolus_id = {sonolus_id};
    """


def generate_link_discord_id_query(sonolus_id: int, discord_id: int) -> str:
    return f"""
        UPDATE accounts
        SET discord_id = {discord_id}, updated_at = CURRENT_TIMESTAMP
        WHERE sonolus_id = {sonolus_id};
    """


def generate_link_patreon_id_query(sonolus_id: int, patreon_id: str) -> str:
    return f"""
        UPDATE accounts
        SET patreon_id = '{patreon_id}', updated_at = CURRENT_TIMESTAMP
        WHERE sonolus_id = {sonolus_id};
    """


def generate_set_mod_query(sonolus_id: int, mod_status: bool) -> str:
    return f"""
        UPDATE accounts
        SET mod = {str(mod_status).lower()}, updated_at = CURRENT_TIMESTAMP
        WHERE sonolus_id = {sonolus_id};
    """


def generate_set_banned_query(sonolus_id: int, banned_status: bool) -> str:
    return f"""
        UPDATE accounts
        SET banned = {str(banned_status).lower()}, updated_at = CURRENT_TIMESTAMP
        WHERE sonolus_id = {sonolus_id};
    """


def generate_update_chart_upload_cooldown_query(
    sonolus_id: int, cooldown_timestamp: str
) -> str:
    return f"""
        UPDATE accounts
        SET chart_upload_cooldown = '{cooldown_timestamp}', updated_at = CURRENT_TIMESTAMP
        WHERE sonolus_id = {sonolus_id};
    """
