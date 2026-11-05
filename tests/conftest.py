import pytest
from werkzeug.security import generate_password_hash
from backend.app import create_app
from backend.db import initialize, transaction
from backend.models import User

@pytest.fixture
def app(tmp_path):
    app=create_app({'TESTING':True,'DATA_DIR':str(tmp_path),'JWT_SECRET_KEY':'isolated-tests-only-secret-at-least-32-characters','DATABASE_URL':'','CORS_ORIGINS':['http://localhost:3000']})
    initialize(app.extensions['engine'])
    yield app
    app.extensions['engine'].dispose()
@pytest.fixture
def client(app): return app.test_client()
@pytest.fixture
def accounts(app,client):
    result={}
    with transaction(app.extensions['engine']) as db:
        for role in ['USER','RTO','ADMIN','GOVT','OTHER']:
            u=User(email=role.lower()+'@example.test',full_name=role,role='USER' if role=='OTHER' else role,password_hash=generate_password_hash('unique-test-password'))
            db.add(u); db.flush(); result[role]={'id':u.id}
    for role in result:
        r=client.post('/api/auth/login',json={'email':role.lower()+'@example.test','password':'unique-test-password'})
        assert r.status_code==200,r.json
        result[role]['headers']={'Authorization':'Bearer '+r.json['access_token']}
    return result
