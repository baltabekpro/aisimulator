-- Drop the existing foreign key constraint on user_id
ALTER TABLE memory_entries DROP CONSTRAINT IF EXISTS fk_user;

-- Create indices for better query performance 
CREATE INDEX IF NOT EXISTS idx_memory_entries_user_id_text 
ON memory_entries ((user_id::text));

CREATE INDEX IF NOT EXISTS idx_memory_entries_character_id_text 
ON memory_entries ((character_id::text));

-- If we still want to enforce referential integrity for character_id
ALTER TABLE memory_entries DROP CONSTRAINT IF EXISTS fk_character;
ALTER TABLE memory_entries ADD CONSTRAINT fk_character
    FOREIGN KEY(character_id) 
    REFERENCES characters(id)
    ON DELETE CASCADE;

-- Make sure all existing records have non-NULL values
UPDATE memory_entries SET user_id = '00000000-0000-0000-0000-000000000000'::uuid 
WHERE user_id IS NULL;

-- Check if any system user exists that can be used for orphaned memories
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM users WHERE user_id = '00000000-0000-0000-0000-000000000000'::uuid) THEN
        -- Create a system user for orphaned memories with a password hash
        -- Using a placeholder hash for 'system' - not for actual login
        INSERT INTO users (user_id, username, email, name, password_hash, created_at, is_admin)
        VALUES ('00000000-0000-0000-0000-000000000000', 'system', 'system@example.com', 'System', 
                '$2b$12$K8uw2YYdIzp2XvRWMs9vpO6STRyI53aUEym.Oi4XwqVgRvG/f7kUC', 
                NOW(), false);
    END IF;
END $$;