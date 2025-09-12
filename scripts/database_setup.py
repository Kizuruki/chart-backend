import asyncio

import asyncpg
import yaml

with open("config.yml", "r") as f:
    config = yaml.load(f, yaml.Loader)

psql_config = config["psql"]


async def main():
    db = await asyncpg.create_pool(
        host=psql_config["host"],
        user=psql_config["user"],
        database=psql_config["database"],
        password=psql_config["password"],
        port=psql_config["port"],
        min_size=psql_config["pool-min-size"],
        max_size=psql_config["pool-max-size"],
        ssl="disable",
    )
    print("Connected!")
    queries = [
        """CREATE TYPE chart_status AS ENUM ('UNLISTED', 'PRIVATE', 'PUBLIC');""",
        """CREATE TABLE IF NOT EXISTS charts (
    id TEXT PRIMARY KEY,
    rating INT DEFAULT 1,
    author BIGINT REFERENCES accounts(sonolus_id) ON DELETE CASCADE,
    description TEXT,
    title TEXT NOT NULL,
    artists TEXT,
    tags TEXT[] DEFAULT '{}',
    likes BIGINT[] DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status chart_status NOT NULL,
    jacket_file_hash TEXT NOT NULL,
    music_file_hash TEXT NOT NULL,
    chart_file_hash TEXT NOT NULL,
    preview_file_hash TEXT,
    background_file_hash TEXT
);""",
        """CREATE TABLE IF NOT EXISTS accounts (
    sonolus_id BIGINT PRIMARY KEY,
    discord_id BIGINT,
    patreon_id TEXT,
    chart_upload_cooldown TIMESTAMP,
    oauth_details JSONB,
    subscription_details JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    mod BOOL DEFAULT false,
    banned BOOL DEFAULT false
);""",
        """CREATE TABLE IF NOT EXISTS comments (
    id TEXT PRIMARY KEY,
    commenter BIGINT REFERENCES accounts(sonolus_id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP DEFAULT NULL,
    chart_id TEXT REFERENCES charts(id) ON DELETE CASCADE
);""",
        """CREATE TABLE IF NOT EXISTS leaderboards (
    id TEXT PRIMARY KEY,
    submitter BIGINT REFERENCES accounts(sonolus_id) ON DELETE CASCADE,
    replay_hash TEXT NOT NULL,
    chart_id TEXT REFERENCES charts(id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);""",
        """CREATE OR REPLACE FUNCTION remove_likes_on_account_delete()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE charts
    SET likes = array_remove(likes, OLD.sonolus_id)
    WHERE OLD.sonolus_id = ANY(likes);
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;""",
        """CREATE TRIGGER account_delete_trigger
AFTER DELETE ON accounts
FOR EACH ROW
EXECUTE FUNCTION remove_likes_on_account_delete();""",
    ]

    async with db.acquire() as connection:
        for query in queries:
            try:
                await connection.execute(query)
            except asyncpg.exceptions.InsufficientPrivilegeError as e:
                print(f"Permission denied: {e}")
    print("Done!")


if __name__ == "__main__":
    asyncio.run(main())
