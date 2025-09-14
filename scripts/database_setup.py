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
        """CREATE EXTENSION IF NOT EXISTS pg_trgm;""",
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
    chart_author TEXT NOT NULL,
    description TEXT,
    title TEXT NOT NULL,
    artists TEXT,
    tags TEXT[] DEFAULT '{}',
    like_count BIGINT NOT NULL DEFAULT 0,
    log_like_score DOUBLE PRECISION DEFAULT 0 NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status chart_status NOT NULL,
    jacket_file_hash TEXT NOT NULL,
    music_file_hash TEXT NOT NULL,
    chart_file_hash TEXT NOT NULL,
    preview_file_hash TEXT,
    background_file_hash TEXT
);""",
        """CREATE TABLE IF NOT EXISTS chart_likes (
    chart_id TEXT NOT NULL REFERENCES charts(id) ON DELETE CASCADE,
    sonolus_id TEXT NOT NULL REFERENCES accounts(sonolus_id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT NOW() NOT NULL,
    PRIMARY KEY (chart_id, sonolus_id)
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
        """CREATE OR REPLACE FUNCTION decayed_like_score(created_at TIMESTAMP, halflife INTERVAL)
RETURNS DOUBLE PRECISION AS $$
    SELECT exp(-EXTRACT(EPOCH FROM (NOW() - created_at)) / EXTRACT(EPOCH FROM halflife));
$$ LANGUAGE SQL IMMUTABLE;""",
        """CREATE OR REPLACE FUNCTION update_like_count()
RETURNS TRIGGER AS $$
DECLARE
    a DOUBLE PRECISION := 1.0 / EXTRACT(EPOCH FROM INTERVAL '7 days');
    tnow DOUBLE PRECISION := EXTRACT(EPOCH FROM NOW());
    s DOUBLE PRECISION;
BEGIN
    IF TG_OP = 'INSERT' THEN
        UPDATE charts
        SET like_count = like_count + 1
        WHERE id = NEW.chart_id;

        SELECT COALESCE(LOG1P(EXP(a * EXTRACT(EPOCH FROM NEW.created_at)) / 
                   EXP(COALESCE(log_like_score,0))), LOG(EXP(a * EXTRACT(EPOCH FROM NEW.created_at)))) 
        INTO s;

        UPDATE charts
        SET log_like_score = COALESCE(log_like_score,0) + LOG1P(EXP(a * EXTRACT(EPOCH FROM NEW.created_at) - COALESCE(log_like_score,0)))
        WHERE id = NEW.chart_id;

    ELSIF TG_OP = 'DELETE' THEN
        UPDATE charts
        SET like_count = like_count - 1
        WHERE id = OLD.chart_id;

        UPDATE charts c
        SET log_like_score = COALESCE((
            SELECT LOG(SUM(EXP(a * EXTRACT(EPOCH FROM cl.created_at))))
            FROM chart_likes cl
            WHERE cl.chart_id = OLD.chart_id
        ), 0)
        WHERE c.id = OLD.chart_id;
    END IF;

    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE TRIGGER trg_update_like_count
AFTER INSERT OR DELETE ON chart_likes
FOR EACH ROW
EXECUTE FUNCTION update_like_count();""",
        """-- Scalar columns: B-Tree
CREATE INDEX IF NOT EXISTS idx_charts_status ON charts(status);
CREATE INDEX IF NOT EXISTS idx_charts_rating ON charts(rating);
CREATE INDEX IF NOT EXISTS idx_charts_created_at ON charts(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_charts_like_count ON charts(like_count DESC);
CREATE INDEX IF NOT EXISTS idx_chart_likes_user ON chart_likes(sonolus_id);
CREATE INDEX IF NOT EXISTS idx_chart_likes_chart ON chart_likes(chart_id);
CREATE INDEX IF NOT EXISTS idx_chart_likes_chart_created
    ON chart_likes (chart_id, created_at DESC);

-- GIN
CREATE INDEX IF NOT EXISTS idx_charts_tags ON charts USING GIN(tags);

-- Text columns with pg_trgm for fast ILIKE
CREATE INDEX IF NOT EXISTS idx_charts_title_trgm ON charts USING GIN (LOWER(title) gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_charts_description_trgm ON charts USING GIN (LOWER(description) gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_charts_artists_trgm ON charts USING GIN (LOWER(artists) gin_trgm_ops);
""",
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
