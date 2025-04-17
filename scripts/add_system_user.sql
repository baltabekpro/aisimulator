-- Create system user if it doesn't exist
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM users WHERE user_id::text = '00000000-0000-0000-0000-000000000000') THEN
        INSERT INTO users (user_id, username, email, name, password_hash, created_at, is_admin)
        VALUES ('00000000-0000-0000-0000-000000000000', 'system', 'system@example.com', 'System', 
                -- Placeholder password hash for 'system' (not for actual login)
                '$2b$12$K8uw2YYdIzp2XvRWMs9vpO6STRyI53aUEym.Oi4XwqVgRvG/f7kUC', 
                NOW(), false);
        RAISE NOTICE 'Created system user for memory entries';
    ELSE
        RAISE NOTICE 'System user already exists';
    END IF;
END $$;

-- Update any null user_id values in memory_entries to use system user
UPDATE memory_entries SET user_id = '00000000-0000-0000-0000-000000000000'::uuid
WHERE user_id IS NULL;