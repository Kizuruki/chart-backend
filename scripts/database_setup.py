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
    # uncomment first block ONLY to delete all tables.
    # should not ever be run for production
    queries = [
        # """DO $$
        # DECLARE
        #     r RECORD;
        # BEGIN
        #     -- Iterate over each table and drop it
        #     FOR r IN (SELECT tablename FROM pg_tables WHERE schemaname = 'public') LOOP
        #         EXECUTE 'DROP TABLE IF EXISTS public.' || r.tablename || ' CASCADE';
        #     END LOOP;
        # END $$;
        # """,
        """DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'chart_status') THEN
        CREATE TYPE chart_status AS ENUM ('UNLISTED', 'PRIVATE', 'PUBLIC');
    END IF;
END $$;""",
        """CREATE TABLE IF NOT EXISTS accounts (
    sonolus_id TEXT PRIMARY KEY,
    sonolus_handle BIGINT NOT NULL,
    discord_id BIGINT,
    patreon_id TEXT,
    previous_likes TEXT[] DEFAULT '{}',
    chart_upload_cooldown TIMESTAMP,
    sonolus_sessions JSONB,
    oauth_details JSONB,
    subscription_details JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    mod BOOL DEFAULT false,
    banned BOOL DEFAULT false
);""",
        """CREATE TABLE IF NOT EXISTS charts (
    id TEXT PRIMARY KEY,
    rating INT DEFAULT 1,
    author TEXT REFERENCES accounts(sonolus_id) ON DELETE CASCADE,
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
        """CREATE TABLE IF NOT EXISTS comments (
    id TEXT PRIMARY KEY,
    commenter TEXT REFERENCES accounts(sonolus_id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP DEFAULT NULL,
    chart_id TEXT REFERENCES charts(id) ON DELETE CASCADE
);""",
        """CREATE TABLE IF NOT EXISTS leaderboards (
    id TEXT PRIMARY KEY,
    submitter TEXT REFERENCES accounts(sonolus_id) ON DELETE CASCADE,
    replay_hash TEXT NOT NULL,
    chart_id TEXT REFERENCES charts(id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);""",
        """CREATE OR REPLACE FUNCTION remove_likes_on_account_delete()
RETURNS TRIGGER AS $$
BEGIN
    IF OLD.previous_likes IS NOT NULL THEN
        UPDATE charts
        SET likes = array_remove(likes, OLD.sonolus_id)
        WHERE id = ANY(OLD.previous_likes)
          AND id IN (SELECT id FROM charts);
    END IF;
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
