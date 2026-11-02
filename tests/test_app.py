import pytest


ACTIVITY = "Chess Club"
SIGNUP_URL = "/activities/Chess%20Club/signup"
UNREGISTER_URL = "/activities/Chess%20Club/unregister"
NEW_EMAIL = "new.student+chess@mergington.edu"


def test_root_redirect(client):
    response = client.get("/", follow_redirects=False)

    assert response.status_code == 307
    assert response.headers["location"] == "/static/index.html"


def test_get_activities(client, activity_data):
    response = client.get("/activities")

    assert response.status_code == 200
    assert response.json() == activity_data
    activities = response.json()
    assert any(activity["participants"] for activity in activities.values())
    assert any(not activity["participants"] for activity in activities.values())
    for activity in activities.values():
        assert set(activity) == {
            "description", "schedule", "max_participants", "participants"
        }
        assert isinstance(activity["description"], str)
        assert isinstance(activity["schedule"], str)
        assert isinstance(activity["max_participants"], int)
        assert isinstance(activity["participants"], list)
        assert all(isinstance(email, str) for email in activity["participants"])


def test_signup_adds_one_participant(client, activity_data):
    response = client.post(SIGNUP_URL, params={"email": NEW_EMAIL})

    assert response.status_code == 200
    assert response.json() == {"message": f"Signed up {NEW_EMAIL} for {ACTIVITY}"}
    activity_data[ACTIVITY]["participants"].append(NEW_EMAIL)
    assert client.get("/activities").json() == activity_data


def test_duplicate_signup_does_not_change_state(client, activity_data):
    email = activity_data[ACTIVITY]["participants"][0]

    response = client.post(SIGNUP_URL, params={"email": email})

    assert response.status_code == 400
    assert response.json() == {"detail": "Student already signed up for this activity"}
    assert client.get("/activities").json() == activity_data


@pytest.mark.parametrize(
    ("method", "action"), [("POST", "signup"), ("DELETE", "unregister")]
)
def test_unknown_activity_does_not_change_state(client, activity_data, method, action):
    response = client.request(
        method, f"/activities/Unknown%20Activity/{action}", params={"email": NEW_EMAIL}
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Activity not found"}
    assert client.get("/activities").json() == activity_data


def test_unregister_removes_participant(client, activity_data):
    email = activity_data[ACTIVITY]["participants"][0]

    response = client.delete(UNREGISTER_URL, params={"email": email})

    assert response.status_code == 200
    assert response.json() == {"message": f"Unregistered {email} from {ACTIVITY}"}
    activity_data[ACTIVITY]["participants"].remove(email)
    assert client.get("/activities").json() == activity_data


def test_unregister_unknown_participant_does_not_change_state(client, activity_data):
    response = client.delete(UNREGISTER_URL, params={"email": NEW_EMAIL})

    assert response.status_code == 404
    assert response.json() == {"detail": "Participant not found in this activity"}
    assert client.get("/activities").json() == activity_data


def test_repeated_unregister_does_not_change_state_twice(client, activity_data):
    email = activity_data[ACTIVITY]["participants"][0]
    first = client.delete(UNREGISTER_URL, params={"email": email})
    second = client.delete(UNREGISTER_URL, params={"email": email})

    assert first.status_code == 200
    assert second.status_code == 404
    assert second.json() == {"detail": "Participant not found in this activity"}
    activity_data[ACTIVITY]["participants"].remove(email)
    assert client.get("/activities").json() == activity_data


def test_signup_unregister_round_trip(client, activity_data):
    signup = client.post(SIGNUP_URL, params={"email": NEW_EMAIL})
    assert signup.status_code == 200
    assert NEW_EMAIL in client.get("/activities").json()[ACTIVITY]["participants"]

    unregister = client.delete(UNREGISTER_URL, params={"email": NEW_EMAIL})
    assert unregister.status_code == 200
    assert client.get("/activities").json() == activity_data


@pytest.mark.parametrize(
    ("method", "url"), [("POST", SIGNUP_URL), ("DELETE", UNREGISTER_URL)]
)
def test_missing_email_does_not_change_state(client, activity_data, method, url):
    response = client.request(method, url)

    assert response.status_code == 422
    assert any(
        error["loc"] == ["query", "email"] for error in response.json()["detail"]
    )
    assert client.get("/activities").json() == activity_data


@pytest.mark.parametrize(
    ("path", "content_types"),
    [
        ("/static/index.html", {"text/html"}),
        ("/static/app.js", {"text/javascript", "application/javascript"}),
        ("/static/styles.css", {"text/css"}),
        ("/docs", {"text/html"}),
        ("/redoc", {"text/html"}),
    ],
)
def test_static_and_documentation_pages(client, path, content_types):
    response = client.get(path)

    assert response.status_code == 200
    assert response.headers["content-type"].split(";")[0] in content_types
    assert response.content


def test_openapi_schema_contains_application_routes(client):
    response = client.get("/openapi.json")

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/json"
    paths = response.json()["paths"]
    for path, method in [
        ("/", "get"),
        ("/activities", "get"),
        ("/activities/{activity_name}/signup", "post"),
        ("/activities/{activity_name}/unregister", "delete"),
    ]:
        assert method in paths[path]
