import pytest
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'server'))

@pytest.fixture
def env():
    from crisis_room_environment import CrisisRoomEnvironment
    return CrisisRoomEnvironment()

@pytest.fixture
def client():
    from fastapi.testclient import TestClient
    from app import app
    return TestClient(app)

