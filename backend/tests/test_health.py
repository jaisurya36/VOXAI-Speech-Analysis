import pytest
from fastapi.testclient import TestClient
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.main import app

client = TestClient(app)


def test_health_returns_200():
    response = client.get('/api/health')
    assert response.status_code == 200


def test_health_response_body():
    response = client.get('/api/health')
    data = response.json()
    assert data['status'] == 'ok'
    assert data['application'] == 'Counterpointing Speech Analytics'
    assert 'version' in data


def test_root_endpoint():
    response = client.get('/')
    assert response.status_code == 200
    data = response.json()
    assert 'message' in data
