-- Replit Auth Tables Migration
-- Run this in production database ONCE before deployment

-- Create users table
CREATE TABLE IF NOT EXISTS users (
    id VARCHAR PRIMARY KEY,
    email VARCHAR UNIQUE,
    first_name VARCHAR,
    last_name VARCHAR,
    profile_image_url TEXT,
    role VARCHAR DEFAULT 'viewer',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create oauth table for token storage
CREATE TABLE IF NOT EXISTS oauth (
    id SERIAL PRIMARY KEY,
    provider VARCHAR NOT NULL,
    provider_user_id VARCHAR,
    token TEXT,
    user_id VARCHAR REFERENCES users(id),
    browser_session_key VARCHAR NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_user_browser_session_key_provider 
        UNIQUE (user_id, browser_session_key, provider)
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_oauth_user_id ON oauth(user_id);
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);

-- Verify migration
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'users') THEN
        RAISE EXCEPTION 'Migration failed: users table not created';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'oauth') THEN
        RAISE EXCEPTION 'Migration failed: oauth table not created';
    END IF;
    RAISE NOTICE 'Migration successful: auth tables created';
END $$;
