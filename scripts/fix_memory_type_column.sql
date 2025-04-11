-- Fix the memory_entries table to add memory_type column
ALTER TABLE memory_entries ADD COLUMN IF NOT EXISTS memory_type VARCHAR(50);

-- If memory_type is null but type exists, copy values from type column
UPDATE memory_entries SET memory_type = type WHERE memory_type IS NULL AND type IS NOT NULL;

-- Create or replace a trigger to keep the columns in sync
CREATE OR REPLACE FUNCTION sync_memory_type_columns() RETURNS TRIGGER AS $$
BEGIN
    IF NEW.memory_type IS NULL AND NEW.type IS NOT NULL THEN
        NEW.memory_type := NEW.type;
    ELSIF NEW.memory_type IS NOT NULL AND NEW.type IS NULL THEN
        NEW.type := NEW.memory_type;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Drop trigger if exists
DROP TRIGGER IF EXISTS sync_memory_type_trigger ON memory_entries;

-- Create trigger
CREATE TRIGGER sync_memory_type_trigger
BEFORE INSERT OR UPDATE ON memory_entries
FOR EACH ROW
EXECUTE FUNCTION sync_memory_type_columns();

-- Create or replace a view for backward compatibility
CREATE OR REPLACE VIEW memory_entries_view AS
SELECT 
    id, 
    character_id, 
    user_id, 
    COALESCE(memory_type, type, 'unknown') AS memory_type,
    COALESCE(type, memory_type, 'unknown') AS type,
    COALESCE(category, 'general') AS category,
    content, 
    importance, 
    is_active, 
    created_at, 
    updated_at
FROM memory_entries;