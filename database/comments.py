from typing import Tuple
import uuid


def generate_create_comment_query(
    sonolus_id: str, chart_id: str, content: str
) -> Tuple[str, Tuple]:
    comment_id = str(uuid.uuid4())
    return """
        INSERT INTO comments (id, commenter, content, created_at, chart_id)
        VALUES ($1, $2, $3, CURRENT_TIMESTAMP, $4);
    """, (
        comment_id,
        sonolus_id,
        content,
        chart_id,
    )


def generate_delete_comment_query(comment_id: str) -> Tuple[str, Tuple]:
    return """
        UPDATE comments
        SET deleted_at = CURRENT_TIMESTAMP
        WHERE id = $1;
    """, (
        comment_id,
    )


def generate_get_comments_query(
    chart_id: str, limit: int = 3, page: int = 0, sort_desc: bool = False
) -> Tuple[str, Tuple]:
    """
    sort_desc: setting to True will put NEWER comments on top instead of OLDER comments
    """
    order_clause = (
        "ORDER BY created_at DESC" if sort_desc else "ORDER BY created_at ASC"
    )
    offset = page * limit
    return f"""
        SELECT id, commenter, content, created_at, deleted_at, chart_id
        FROM comments
        WHERE chart_id = $1 AND deleted_at IS NULL
        {order_clause}
        LIMIT $2 OFFSET $3;
    """, (
        chart_id,
        limit,
        offset,
    )


def generate_get_comments_by_account_query(
    sonolus_id: str, limit: int = 3, page: int = 0, sort_desc: bool = False
) -> Tuple[str, Tuple]:
    """
    sort_desc: setting to True will put NEWER comments on top instead of OLDER comments
    """
    order_clause = (
        "ORDER BY created_at DESC" if sort_desc else "ORDER BY created_at ASC"
    )
    offset = page * limit
    return f"""
        SELECT id, commenter, content, created_at, deleted_at, chart_id
        FROM comments
        WHERE commenter = $1 AND deleted_at IS NULL
        {order_clause}
        LIMIT $2 OFFSET $3;
    """, (
        sonolus_id,
        limit,
        offset,
    )
