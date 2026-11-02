from copy import deepcopy

import pytest
from fastapi.testclient import TestClient

import src.app as app_module


@pytest.fixture
def activity_data():
    return deepcopy(app_module.activities)


@pytest.fixture(autouse=True)
def isolate_activities(monkeypatch, activity_data):
    monkeypatch.setattr(app_module, "activities", deepcopy(activity_data))


@pytest.fixture
def client(isolate_activities):
    with TestClient(app_module.app) as test_client:
        yield test_client
