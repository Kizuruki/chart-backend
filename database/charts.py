from typing import List, Optional, Tuple
import uuid


def generate_create_chart_query(
    author: int,
    title: str,
    artists: str,
    tags: List[str] = [],
    jacket_hash: str = "",
    music_hash: str = "",
    chart_hash: str = "",
    preview_hash: Optional[str] = None,
    background_hash: Optional[str] = None,
) -> Tuple[str, Tuple]:
    chart_id = str(uuid.uuid4()).replace("-", "")
    tags_str = tags if tags else []

    query = """
        INSERT INTO charts (id, author, title, artists, tags, jacket_file_hash, music_file_hash, chart_file_hash, preview_file_hash, background_file_hash, status, created_at, updated_at)
        VALUES (
            $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, 'PRIVATE', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
        );
    """

    return query, (
        chart_id,
        author,
        title,
        artists,
        tags_str,
        jacket_hash,
        music_hash,
        chart_hash,
        preview_hash if preview_hash else None,
        background_hash if background_hash else None,
    )


def generate_delete_chart_query(
    chart_id: str, confirm_change: bool = False
) -> Tuple[str, Tuple[str]]:
    if not confirm_change:
        raise ValueError(
            "Deletion not confirmed. Ensure you are deleting the old files from S3 to ensure there is no hanging files."
        )
    return """
        DELETE FROM charts
        WHERE id = $1;
    """, (
        chart_id,
    )


def generate_update_metadata_query(
    chart_id: str,
    rating: Optional[int] = None,
    description: Optional[str] = None,
    title: Optional[str] = None,
    artists: Optional[str] = None,
    tags: Optional[List[str]] = None,
    update_none_description: bool = False,
) -> Tuple[str, Tuple]:
    if not any([rating, description, title, artists, tags]):
        raise ValueError("At least one field must be updated.")

    set_fields = []
    args = []

    if rating is not None:
        set_fields.append("rating = $1")
        args.append(rating)

    if description is not None:
        set_fields.append("description = $2")
        args.append(description)
    elif update_none_description:
        set_fields.append("description = NULL")

    if title is not None:
        set_fields.append("title = $3")
        args.append(title)

    if artists is not None:
        set_fields.append("artists = $4")
        args.append(artists)

    if tags is not None:
        set_fields.append("tags = $5")
        args.append(tags)

    set_fields.append("updated_at = CURRENT_TIMESTAMP")

    set_clause = ", ".join(set_fields)

    return f"""
        UPDATE charts
        SET {set_clause}
        WHERE id = $6;
    """, tuple(
        args + [chart_id]
    )


def generate_update_file_hash_query(
    chart_id: str,
    jacket_hash: Optional[str] = None,
    music_hash: Optional[str] = None,
    chart_hash: Optional[str] = None,
    preview_hash: Optional[str] = None,
    background_hash: Optional[str] = None,
    confirm_change: bool = False,
    update_none_preview: bool = False,
    update_none_background: bool = False,
) -> Tuple[str, Tuple]:
    if not confirm_change:
        raise ValueError(
            "File hash change is not confirmed. Ensure you are deleting the old files from S3 to ensure there is no hanging files."
        )

    set_fields = []
    args = []

    if jacket_hash is not None:
        set_fields.append("jacket_file_hash = $1")
        args.append(jacket_hash)

    if music_hash is not None:
        set_fields.append("music_file_hash = $2")
        args.append(music_hash)

    if chart_hash is not None:
        set_fields.append("chart_file_hash = $3")
        args.append(chart_hash)

    if preview_hash is not None:
        set_fields.append("preview_file_hash = $4")
        args.append(preview_hash)
    elif update_none_preview:
        set_fields.append("preview_file_hash = NULL")

    if background_hash is not None:
        set_fields.append("background_file_hash = $5")
        args.append(background_hash)
    elif update_none_background:
        set_fields.append("background_file_hash = NULL")

    set_fields.append("updated_at = CURRENT_TIMESTAMP")

    if not set_fields:
        raise ValueError("At least one file hash must be updated.")

    set_clause = ", ".join(set_fields)

    return f"""
        UPDATE charts
        SET {set_clause}
        WHERE id = $6;
    """, tuple(
        args + [chart_id]
    )


def generate_add_like_query(chart_id: str, sonolus_id: str) -> Tuple[str, Tuple]:
    return """
        UPDATE charts
        SET likes = array_append(likes, $1), updated_at = CURRENT_TIMESTAMP
        WHERE id = $2;

        UPDATE accounts
        SET previous_likes = array_append(previous_likes, $2)
        WHERE sonolus_id = $1;
    """, (
        sonolus_id,
        chart_id,
    )


def generate_remove_like_query(chart_id: str, sonolus_id: str) -> Tuple[str, Tuple]:
    return """
        UPDATE charts
        SET likes = array_remove(likes, $1), updated_at = CURRENT_TIMESTAMP
        WHERE id = $2;
    """, (
        sonolus_id,
        chart_id,
    )


def generate_update_status_query(chart_id: str, status: str) -> Tuple[str, Tuple]:
    return """
        UPDATE charts
        SET status = $1, updated_at = CURRENT_TIMESTAMP
        WHERE id = $2;
    """, (
        status,
        chart_id,
    )
