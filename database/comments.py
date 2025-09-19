import uuid

from database.query import ExecutableQuery, SelectQuery
from helpers.models import Comment


def create_comment(sonolus_id: str, chart_id: str, content: str) -> ExecutableQuery:
    comment_id = str(uuid.uuid4())
    return ExecutableQuery(
        """
            INSERT INTO comments (id, commenter, content, created_at, chart_id)
            VALUES ($1, $2, $3, CURRENT_TIMESTAMP, $4);
        """,
        comment_id,
        sonolus_id,
        content,
        chart_id,
    )


def delete_comment(comment_id: str) -> ExecutableQuery:
    return ExecutableQuery(
        """
            UPDATE comments
            SET deleted_at = CURRENT_TIMESTAMP
            WHERE id = $1;
        """,
        comment_id,
    )


def get_comments(
    chart_id: str, limit: int = 3, page: int = 0, sort_desc: bool = False
) -> SelectQuery[Comment]:
    """
    sort_desc: setting to True will put NEWER comments on top instead of OLDER comments
    """
    order_clause = (
        "ORDER BY created_at DESC" if sort_desc else "ORDER BY created_at ASC"
    )
    offset = page * limit
    return SelectQuery(
        Comment,
        f"""
            SELECT id, commenter, content, created_at, deleted_at, chart_id
            FROM comments
            WHERE chart_id = $1 AND deleted_at IS NULL
            {order_clause}
            LIMIT $2 OFFSET $3;
        """,
        chart_id,
        limit,
        offset,
    )


def get_comments_by_account(
    sonolus_id: str, limit: int = 3, page: int = 0, sort_desc: bool = False
) -> SelectQuery[Comment]:
    """
    sort_desc: setting to True will put NEWER comments on top instead of OLDER comments
    """
    order_clause = (
        "ORDER BY created_at DESC" if sort_desc else "ORDER BY created_at ASC"
    )
    offset = page * limit
    return SelectQuery(
        Comment,
        f"""
            SELECT id, commenter, content, created_at, deleted_at, chart_id
            FROM comments
            WHERE commenter = $1 AND deleted_at IS NULL
            {order_clause}
            LIMIT $2 OFFSET $3;
        """,
        sonolus_id,
        limit,
        offset,
    )
