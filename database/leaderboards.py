from typing import Optional, Tuple
from database.query import ExecutableQuery, SelectQuery
from helpers.models import LeaderboardDBResponse, Count


def insert_leaderboard_entry(
    submitter: str, chart_id: str, replay_hash: str
) -> ExecutableQuery:
    return ExecutableQuery(
        """
        INSERT INTO leaderboards (submitter, chart_id, replay_hash)
        VALUES ($1, $2, $3)
        """,
        submitter,
        chart_id,
        replay_hash,
    )


def get_leaderboard_for_chart(
    chart_id: str,
    limit: int = 10,
    page: int = 0,
    sort_desc: bool = True,
    sonolus_id: Optional[str] = None,
) -> Tuple[SelectQuery[LeaderboardDBResponse], SelectQuery[Count]]:
    """
    Returns (leaderboard_entries_query, count_query).
    Use count_query to calculate total pages.
    """
    order_clause = (
        "ORDER BY l.created_at DESC" if sort_desc else "ORDER BY l.created_at ASC"
    )
    offset = page * limit

    leaderboard_query = SelectQuery(
        LeaderboardDBResponse,
        f"""
            SELECT 
                l.id,
                l.submitter,
                l.replay_hash,
                l.chart_id,
                l.created_at,
                CONCAT(c.chart_author, '/', c.id) AS chart_prefix
            FROM leaderboards l
            JOIN charts c ON l.chart_id = c.id
            WHERE l.chart_id = $1
            {order_clause}
            LIMIT $2 OFFSET $3;
        """,
        chart_id,
        limit,
        offset,
    )

    count_query = SelectQuery(
        Count,
        """
            SELECT COUNT(*) AS total_count
            FROM leaderboards l
            WHERE l.chart_id = $1;
        """,
        chart_id,
    )

    return (
        leaderboard_query,
        count_query,
    )  # XXX: return owner (just like comment or chart does)


def delete_leaderboard_entry(entry_id: int) -> ExecutableQuery:
    return ExecutableQuery(
        """
        DELETE FROM leaderboards
        WHERE id = $1
        """,
        entry_id,
    )


def delete_leaderboard_for_chart(chart_id: str) -> ExecutableQuery:
    return ExecutableQuery(
        """
        DELETE FROM leaderboards
        WHERE chart_id = $1
        """,
        chart_id,
    )
