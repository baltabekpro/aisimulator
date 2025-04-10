-- Add the missing `type` column to memory_entries table
ALTER TABLE memory_entries ADD COLUMN IF NOT EXISTS type VARCHAR(50) NOT NULL;

-- Add an index for faster lookups
CREATE INDEX IF NOT EXISTS idx_memory_entries_character_user ON memory_entries(character_id, user_id);
