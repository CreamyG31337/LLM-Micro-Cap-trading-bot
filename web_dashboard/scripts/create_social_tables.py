#!/usr/bin/env python3
"""
Create Social Sentiment AI Analysis Tables
"""

from postgres_client import PostgresClient

def main():
    pc = PostgresClient()

    # Create social_posts table
    create_posts = """
    CREATE TABLE IF NOT EXISTS social_posts (
        id SERIAL PRIMARY KEY,
        metric_id INTEGER REFERENCES social_metrics(id),
        platform VARCHAR(20) NOT NULL CHECK (platform IN ('stocktwits', 'reddit')),
        post_id VARCHAR(100),
        content TEXT NOT NULL,
        author VARCHAR(100),
        posted_at TIMESTAMPTZ,
        engagement_score INTEGER DEFAULT 0,
        url TEXT,
        extracted_tickers TEXT[],
        created_at TIMESTAMPTZ DEFAULT NOW()
    )
    """
    pc.execute_update(create_posts)

    # Create sentiment_sessions table
    create_sessions = """
    CREATE TABLE IF NOT EXISTS sentiment_sessions (
        id SERIAL PRIMARY KEY,
        ticker VARCHAR(20) NOT NULL,
        platform VARCHAR(20) NOT NULL CHECK (platform IN ('stocktwits', 'reddit')),
        session_start TIMESTAMPTZ NOT NULL,
        session_end TIMESTAMPTZ NOT NULL,
        post_count INTEGER DEFAULT 0,
        total_engagement INTEGER DEFAULT 0,
        needs_ai_analysis BOOLEAN DEFAULT TRUE,
        created_at TIMESTAMPTZ DEFAULT NOW()
    )
    """
    pc.execute_update(create_sessions)

    print('✅ Created social_posts and sentiment_sessions tables')

if __name__ == "__main__":
    main()