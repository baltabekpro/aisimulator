-- Fix the memory_entries table to add missing type column
ALTER TABLE memory_entries ADD COLUMN IF NOT EXISTS type VARCHAR(50) NOT NULL DEFAULT 'general';

-- Add missing category column with a default value to avoid NULL values
ALTER TABLE memory_entries ADD COLUMN IF NOT EXISTS category VARCHAR(50) NOT NULL DEFAULT 'general';

-- Create index for faster queries
CREATE INDEX IF NOT EXISTS idx_memory_entries_character_user 
ON memory_entries(character_id, user_id);

-- Update existing rows to set category value if it was added as nullable first
UPDATE memory_entries SET category = 'general' WHERE category IS NULL;

-- Add index on category column for better performance on category filtering
CREATE INDEX IF NOT EXISTS idx_memory_entries_category 
ON memory_entries(category);
