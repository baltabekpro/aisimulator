-- Script to add external_id column to users table for Apple OAuth support
-- This fixes the "column users.external_id does not exist" error

-- Add external_id column if it doesn't exist yet
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                  WHERE table_name='users' AND column_name='external_id') THEN
        ALTER TABLE users ADD COLUMN external_id VARCHAR(255);
        -- Add an index for faster lookups by external_id
        CREATE INDEX idx_users_external_id ON users(external_id);
    END IF;
END $$;