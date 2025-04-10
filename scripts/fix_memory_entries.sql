-- Fix the memory_entries table to add missing type column
ALTER TABLE memory_entries ADD COLUMN IF NOT EXISTS type VARCHAR(50) NOT NULL DEFAULT 'general';

-- Add missing category column
ALTER TABLE memory_entries ADD COLUMN IF NOT EXISTS category VARCHAR(50);

-- Create index for faster queries
CREATE INDEX IF NOT EXISTS idx_memory_entries_character_user 
ON memory_entries(character_id, user_id);
