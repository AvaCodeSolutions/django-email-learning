from django_email_learning.oauth_integrations.models import Session, SessionState


def test_session_generates_session_id_on_save(db):
    session = Session(jwt_token="token")
    session.save()

    assert session.session_id is not None
    assert isinstance(session.session_id, str)
    assert len(session.session_id) > 0


def test_session_default_state_is_pending(db):
    session = Session.objects.create(jwt_token="token")

    assert session.state == SessionState.PENDING


def test_session_preserves_provided_session_id(db):
    session = Session.objects.create(session_id="custom-session-id", jwt_token="token")

    assert session.session_id == "custom-session-id"
