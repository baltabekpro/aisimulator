-- Fix memory_entries table column inconsistency
-- This script handles the case where 'type' column exists but 'memory_type' doesn't or vice versa

-- Check if type column exists but memory_type doesn't
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'memory_entries' AND column_name = 'type'
    ) AND NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'memory_entries' AND column_name = 'memory_type'
    ) THEN
        RAISE NOTICE 'Adding memory_type column and copying data from type column';
        ALTER TABLE memory_entries ADD COLUMN memory_type VARCHAR(50);
        UPDATE memory_entries SET memory_type = type;
    END IF;

    -- Check if memory_type column exists but type doesn't
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'memory_entries' AND column_name = 'memory_type'
    ) AND NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'memory_entries' AND column_name = 'type'
    ) THEN
        RAISE NOTICE 'Adding type column and copying data from memory_type column';
        ALTER TABLE memory_entries ADD COLUMN type VARCHAR(50);
        UPDATE memory_entries SET type = memory_type;
    END IF;

    -- Check if both columns exist and ensure data is synchronized
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'memory_entries' AND column_name = 'memory_type'
    ) AND EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'memory_entries' AND column_name = 'type'
    ) THEN
        RAISE NOTICE 'Both columns exist, synchronizing data between them';
        -- Update any NULL values in memory_type from type column
        UPDATE memory_entries SET memory_type = type WHERE memory_type IS NULL AND type IS NOT NULL;
        -- Update any NULL values in type from memory_type column
        UPDATE memory_entries SET type = memory_type WHERE type IS NULL AND memory_type IS NOT NULL;
    END IF;
    
    -- Ensure we have a category column
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'memory_entries' AND column_name = 'category'
    ) THEN
        RAISE NOTICE 'Adding category column';
        ALTER TABLE memory_entries ADD COLUMN category VARCHAR(50) DEFAULT 'general';
    END IF;

    -- Create view for consistent access
    RAISE NOTICE 'Creating memory_entries_view';
    DROP VIEW IF EXISTS memory_entries_view;
    CREATE VIEW memory_entries_view AS
    SELECT 
        id, 
        character_id, 
        user_id, 
        COALESCE(type, memory_type, 'unknown') as type,
        COALESCE(memory_type, type, 'unknown') as memory_type,
        COALESCE(category, 'general') as category,
        content, 
        importance, 
        is_active, 
        created_at, 
        updated_at 
    FROM memory_entries;

    -- Create indexes
    RAISE NOTICE 'Creating indexes';
    CREATE INDEX IF NOT EXISTS idx_memory_entries_character_user ON memory_entries(character_id, user_id);
    CREATE INDEX IF NOT EXISTS idx_memory_entries_type ON memory_entries(type);
    CREATE INDEX IF NOT EXISTS idx_memory_entries_memory_type ON memory_entries(memory_type);
    CREATE INDEX IF NOT EXISTS idx_memory_entries_character_id_text ON memory_entries((character_id::text));
END $$;