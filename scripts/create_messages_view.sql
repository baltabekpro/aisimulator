-- Создаем представление для безопасной работы с сообщениями
DROP VIEW IF EXISTS safe_messages_view;

CREATE VIEW safe_messages_view AS
SELECT 
    m.id, 
    m.sender_id, 
    m.sender_type, 
    m.recipient_id, 
    m.recipient_type, 
    m.content, 
    m.emotion, 
    m.created_at,
    CASE 
        WHEN m.sender_type = 'user' AND u1.username IS NOT NULL THEN u1.username::text
        WHEN m.sender_type = 'character' AND c1.name IS NOT NULL THEN c1.name::text
        ELSE m.sender_id::text
    END as sender_name,
    CASE 
        WHEN m.recipient_type = 'user' AND u2.username IS NOT NULL THEN u2.username::text
        WHEN m.recipient_type = 'character' AND c2.name IS NOT NULL THEN c2.name::text
        ELSE m.recipient_id::text
    END as recipient_name
FROM messages m
LEFT JOIN users u1 ON m.sender_id::text = u1.user_id::text AND m.sender_type = 'user'
LEFT JOIN characters c1 ON m.sender_id::text = c1.id::text AND m.sender_type = 'character'
LEFT JOIN users u2 ON m.recipient_id::text = u2.user_id::text AND m.recipient_type = 'user'
LEFT JOIN characters c2 ON m.recipient_id::text = c2.id::text AND m.recipient_type = 'character';
