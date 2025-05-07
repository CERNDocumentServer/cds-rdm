import json

import pytest
from flask_security import login_user
from invenio_access.models import ActionRoles, Role
from invenio_accounts.testutils import login_user_via_session
from invenio_administration.permissions import administration_access_action


@pytest.fixture()
def sync_data():
    return {"parent_record_pid": "test-parent", "clc_record_pid": "test-clc"}


@pytest.fixture
def admin_role_need(db):
    """Store 1 role with 'superuser-access' ActionNeed.

    WHY: This is needed because expansion of ActionNeed is
         done on the basis of a User/Role being associated with that Need.
         If no User/Role is associated with that Need (in the DB), the
         permission is expanded to an empty list.
    """
    role = Role(name="admin-access", id="admin-access")
    db.session.add(role)

    action_role = ActionRoles.create(action=administration_access_action, role=role)
    db.session.add(action_role)

    db.session.commit()

    return action_role.need


@pytest.fixture()
def admin(UserFixture, app, db, admin_role_need):
    """Admin user for requests."""
    u = UserFixture(
        email="admin@inveniosoftware.org",
        password="admin",
    )
    u.create(app, db)

    datastore = app.extensions["security"].datastore
    _, role = datastore._prepare_role_modify_args(u.user, "admin-access")

    datastore.add_role_to_user(u.user, role)
    db.session.commit()
    return u


@pytest.fixture
def client_with_admin_login(client, admin):
    """Log in a user to the client."""
    user = admin.user
    login_user(user)
    login_user_via_session(client, email=user.email)
    return client


def test_create_sync(app, client_with_admin_login, headers, sync_data):
    res = client_with_admin_login.post(
        "/api/clc/", headers=headers, data=json.dumps(sync_data)
    )
    assert res.status_code == 201
    data = res.get_json()
    assert data["parent_record_pid"] == sync_data["parent_record_pid"]


def test_create_existing_sync(app, client_with_admin_login, headers, sync_data):
    res = client_with_admin_login.post(
        "/api/clc/", headers=headers, data=json.dumps(sync_data)
    )
    assert res.status_code == 201
    res = client_with_admin_login.post(
        "/api/clc/", headers=headers, data=json.dumps(sync_data)
    )
    assert res.status_code == 409


def test_read_sync(client_with_admin_login, headers, sync_data):
    res = client_with_admin_login.post(
        "/api/clc/", headers=headers, data=json.dumps(sync_data)
    )
    assert res.status_code == 201
    res = client_with_admin_login.get(
        f"/api/clc/{sync_data['parent_record_pid']}", headers=headers
    )
    assert res.status_code == 200
    data = res.get_json()
    assert data["clc_record_pid"] == sync_data["clc_record_pid"]


def test_update_sync(client_with_admin_login, headers, sync_data):
    res = client_with_admin_login.post(
        "/api/clc/", headers=headers, data=json.dumps(sync_data)
    )
    json_data = res.get_json()
    updated_data = {**sync_data, "clc_record_pid": "updated-clc"}
    updated_res = client_with_admin_login.put(
        f"/api/clc/{json_data['id']}", headers=headers, data=json.dumps(updated_data)
    )
    assert updated_res.status_code == 200
    assert updated_res.get_json()["clc_record_pid"] == "updated-clc"


def test_delete_sync(client_with_admin_login, headers, sync_data):
    res = client_with_admin_login.post(
        "/api/clc/", headers=headers, data=json.dumps(sync_data)
    )
    res_json = res.get_json()
    res = client_with_admin_login.delete(f"/api/clc/{res_json['id']}", headers=headers)
    assert res.status_code == 204


def test_search_sync(client_with_admin_login, headers, sync_data):
    res = client_with_admin_login.post(
        "/api/clc/", headers=headers, data=json.dumps(sync_data)
    )
    res = client_with_admin_login.get("/api/clc/", headers=headers)
    assert res.status_code == 200
    data = res.get_json()
    assert any(
        item["parent_record_pid"] == sync_data["parent_record_pid"]
        for item in data["hits"]["hits"]
    )
