import uuid


def generate_create_chart_query(
    author: int,
    title: str,
    artists: str,
    tags: list = [],
    jacket_hash: str = "",
    music_hash: str = "",
    chart_hash: str = "",
    preview_hash: str = None,
    background_hash: str = None,
) -> str:
    chart_id = str(uuid.uuid4()).replace("-", "")
    tags_str = "{" + ",".join([f"'{tag}'" for tag in tags]) + "}" if tags else "{}"
    return f"""
        INSERT INTO charts (id, author, title, artists, tags, jacket_file_hash, music_file_hash, chart_file_hash, preview_file_hash, background_file_hash, status, created_at, updated_at)
        VALUES (
            '{chart_id}',
            {author},
            '{title}',
            '{artists}',
            {tags_str},
            '{jacket_hash}',
            '{music_hash}',
            '{chart_hash}',
            {f"'{preview_hash}'" if preview_hash else 'NULL'},
            {f"'{background_hash}'" if background_hash else 'NULL'},
            'PRIVATE',
            CURRENT_TIMESTAMP,
            CURRENT_TIMESTAMP
        );
    """


def generate_delete_chart_query(chart_id: str) -> str:
    return f"""
        DELETE FROM charts
        WHERE id = '{chart_id}';
    """


def generate_update_metadata_query(
    chart_id: str,
    rating: int = None,
    description: str = None,
    title: str = None,
    artists: str = None,
    tags: list = None,
    update_none_description: bool = False,
) -> str:
    if not any([rating, description, title, artists, tags]):
        raise ValueError("At least one field must be updated.")

    set_fields = []

    if rating is not None:
        set_fields.append(f"rating = {rating}")

    if description is not None:
        if update_none_description:
            set_fields.append(
                "description = NULL"
            )  # Set to NULL if `update_none_description` is True
        else:
            set_fields.append(f"description = '{description}'")

    if title is not None:
        set_fields.append(f"title = '{title}'")

    if artists is not None:
        set_fields.append(f"artists = '{artists}'")

    if tags is not None:
        tags_str = "{" + ",".join([f"'{tag}'" for tag in tags]) + "}"
        set_fields.append(f"tags = {tags_str}")

    set_fields.append("updated_at = CURRENT_TIMESTAMP")

    set_clause = ", ".join(set_fields)

    return f"""
        UPDATE charts
        SET {set_clause}
        WHERE id = '{chart_id}';
    """


def generate_update_file_hash_query(
    chart_id: str,
    jacket_hash: str = None,
    music_hash: str = None,
    chart_hash: str = None,
    preview_hash: str = None,
    background_hash: str = None,
    confirm_change: bool = False,
    update_none_preview: bool = False,
    update_none_background: bool = False,
) -> str:
    if not confirm_change:
        raise ValueError("File hash change is not confirmed.")

    # If no hash is provided, we need to decide whether to set it to NULL or do nothing
    set_fields = []

    if jacket_hash is not None:
        set_fields.append(f"jacket_file_hash = '{jacket_hash}'")

    if music_hash is not None:
        set_fields.append(f"music_file_hash = '{music_hash}'")

    if chart_hash is not None:
        set_fields.append(f"chart_file_hash = '{chart_hash}'")

    if preview_hash is not None:
        if update_none_preview:
            set_fields.append("preview_file_hash = NULL")
        else:
            set_fields.append(f"preview_file_hash = '{preview_hash}'")

    if background_hash is not None:
        if update_none_background:
            set_fields.append("background_file_hash = NULL")
        else:
            set_fields.append(f"background_file_hash = '{background_hash}'")

    set_fields.append("updated_at = CURRENT_TIMESTAMP")

    if not set_fields:
        raise ValueError("At least one file hash must be updated.")

    set_clause = ", ".join(set_fields)

    return f"""
        UPDATE charts
        SET {set_clause}
        WHERE id = '{chart_id}';
    """


def generate_add_like_query(chart_id: str, sonolus_id: int) -> str:
    return f"""
        UPDATE charts
        SET likes = array_append(likes, {sonolus_id}), updated_at = CURRENT_TIMESTAMP
        WHERE id = '{chart_id}';
    """


def generate_remove_like_query(chart_id: str, sonolus_id: int) -> str:
    return f"""
        UPDATE charts
        SET likes = array_remove(likes, {sonolus_id}), updated_at = CURRENT_TIMESTAMP
        WHERE id = '{chart_id}';
    """


def generate_update_status_query(chart_id: str, status: str) -> str:
    return f"""
        UPDATE charts
        SET status = '{status}', updated_at = CURRENT_TIMESTAMP
        WHERE id = '{chart_id}';
    """
