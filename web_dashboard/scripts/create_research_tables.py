#!/usr/bin/env python3
"""
Create Social Sentiment AI Analysis Tables (Research DB)
"""

from postgres_client import PostgresClient

def main():
    pc = PostgresClient()

    # Create social_sentiment_analysis table
    create_analysis = """
    CREATE TABLE IF NOT EXISTS social_sentiment_analysis (
        id SERIAL PRIMARY KEY,
        session_id INTEGER NOT NULL,
        ticker VARCHAR(20) NOT NULL,
        platform VARCHAR(20) NOT NULL CHECK (platform IN ('stocktwits', 'reddit')),
        sentiment_score DECIMAL(3,2),
        confidence_score DECIMAL(3,2),
        sentiment_label VARCHAR(20),
        summary TEXT,
        key_themes TEXT[],
        reasoning TEXT,
        model_used VARCHAR(100) DEFAULT 'granite3.1:8b',
        analysis_version INTEGER DEFAULT 1,
        analyzed_at TIMESTAMPTZ DEFAULT NOW()
    )
    """
    pc.execute_update(create_analysis)

    # Create extracted_tickers table
    create_tickers = """
    CREATE TABLE IF NOT EXISTS extracted_tickers (
        id SERIAL PRIMARY KEY,
        analysis_id INTEGER REFERENCES social_sentiment_analysis(id),
        ticker VARCHAR(20) NOT NULL,
        confidence DECIMAL(3,2),
        context TEXT,
        is_primary BOOLEAN DEFAULT FALSE,
        company_name VARCHAR(200),
        sector VARCHAR(100),
        extracted_at TIMESTAMPTZ DEFAULT NOW()
    )
    """
    pc.execute_update(create_tickers)

    # Create post_summaries table
    create_summaries = """
    CREATE TABLE IF NOT EXISTS post_summaries (
        id SERIAL PRIMARY KEY,
        post_id INTEGER NOT NULL,
        summary TEXT NOT NULL,
        key_points TEXT[],
        sentiment_impact DECIMAL(3,2),
        summarized_at TIMESTAMPTZ DEFAULT NOW()
    )
    """
    pc.execute_update(create_summaries)

    print('✅ Created AI analysis tables in research database')

if __name__ == "__main__":
    main()