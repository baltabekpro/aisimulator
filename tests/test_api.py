import uuid
from fastapi.testclient import TestClient
from app.main import app  # Ensure your FastAPI app is imported from app/main.py

client = TestClient(app)

def test_get_characters():
    response = client.get("/characters?skip=0&limit=10")
    assert response.status_code == 200
    data = response.json()
    # Expecting a list of characters (possibly empty)
    assert isinstance(data, list)

def test_start_chat_with_character():
    # Use a dummy character_id for testing (adjust as needed)
    dummy_character_id = str(uuid.uuid4())
    response = client.post(f"/characters/{dummy_character_id}/start-chat")
    # Character not found is acceptable; alternatively seed a test partner
    assert response.status_code in [404, 200]

def test_send_message_to_character():
    # Use dummy character_id; adjust according to your test database
    dummy_character_id = str(uuid.uuid4())
    params = {"message": "Привет!"}
    response = client.post(f"/characters/{dummy_character_id}/send", params=params)
    # Depending on test data, 404 or 200 is acceptable
    assert response.status_code in [404, 200]
