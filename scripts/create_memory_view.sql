-- Create a view for memory entries to ensure consistent access
DROP VIEW IF EXISTS memory_entries_view;

CREATE VIEW memory_entries_view AS
SELECT 
    id,
    character_id,
    user_id,
    COALESCE(memory_type, type, 'unknown') as memory_type,
    COALESCE(category, 'general') as category,
    content,
    COALESCE(importance, 5) as importance,
    COALESCE(is_active, TRUE) as is_active,
    created_at,
    updated_at
FROM memory_entries;