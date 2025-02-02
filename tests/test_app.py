import pytest
from fastapi.testclient import TestClient
from app import app
import json
import os

client = TestClient(app)

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}

def test_generate_pdf_missing_file():
    response = client.post(
        "/generate-pdf",
        data={
            "data": json.dumps({"test": "data"})
        }
    )
    assert response.status_code == 422

def test_generate_pdf_invalid_json():
    # Создаем тестовый файл
    with open("test_template.docx", "wb") as f:
        f.write(b"test content")

    with open("test_template.docx", "rb") as f:
        response = client.post(
            "/generate-pdf",
            files={"template_file": ("template.docx", f)},
            data={"data": "invalid json"}
        )

    # Удаляем тестовый файл
    os.remove("test_template.docx")
    assert response.status_code == 500

def test_generate_pdf_success():
    # Этот тест требует реального docx файла
    test_data = {
        "operation": "CREATE",
        "id": "test-id",
        "email": "test@test.com",
        "phone": "123456789",
        "applicantType": "ORGANIZATION",
        "organizationInfo": {
            "name": "Test Org",
            "agent": "Test Agent",
            "address": "Test Address"
        }
    }

    # Проверяем наличие тестового шаблона
    if not os.path.exists("test_template.docx"):
        pytest.skip("Test template file not found")

    with open("test_template.docx", "rb") as f:
        response = client.post(
            "/generate-pdf",
            files={"template_file": ("template.docx", f)},
            data={"data": json.dumps(test_data)}
        )

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf" 