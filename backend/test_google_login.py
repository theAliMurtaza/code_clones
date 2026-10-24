"""Google exchange tests use a disposable database and locally signed tokens."""
import os
os.environ['DATABASE_URL'] = 'sqlite://'
import time
import unittest
from unittest.mock import patch
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from jose import jwt
from config import get_settings
from database import Base, get_db
from auth import decode_token, hash_password
from google_login import router, verify_google_credential
import models

CLIENT = 'test-client.apps.googleusercontent.com'
NONCE = 'browser-nonce-for-test-session'
ORIGIN = 'http://localhost:5173'


class GoogleTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine('sqlite://', connect_args={'check_same_thread':False}, poolclass=StaticPool)
        event.listen(self.engine, 'connect', lambda db, record: db.execute('PRAGMA foreign_keys=ON'))
        Base.metadata.create_all(self.engine)
        self.session = sessionmaker(bind=self.engine)()
        app = FastAPI(); app.include_router(router)
        app.dependency_overrides[get_db] = lambda: self.session
        self.client = TestClient(app)
        self.addCleanup(self.client.close); self.addCleanup(self.engine.dispose); self.addCleanup(self.session.close)
        setting = patch.multiple(get_settings(), GOOGLE_CLIENT_ID=CLIENT, ALLOWED_ORIGINS=ORIGIN)
        setting.start(); self.addCleanup(setting.stop)
        self.claims = dict(sub='google-user-1', aud=CLIENT, iss='https://accounts.google.com',
                           email='person@gmail.com', email_verified=True, name='Ada', nonce=NONCE)

    def exchange(self, **changes):
        with patch('google_login.verify_google_credential', return_value={**self.claims, **changes}):
            return self.client.post('/api/auth/google', json={'credential':'test-token','nonce':NONCE}, headers={'Origin':ORIGIN})

    def test_create_and_returning_identity_keep_same_account(self):
        first = self.exchange(); self.assertEqual(first.status_code, 200, first.text)
        second = self.exchange(email='renamed@gmail.com')
        self.assertEqual(second.status_code, 200)
        self.assertEqual(first.json()['user_id'], second.json()['user_id'])
        self.assertEqual(decode_token(first.json()['access_token'])['sub'], first.json()['user_id'])
        self.assertEqual(self.session.query(models.User).count(), 1)
        self.assertEqual(self.session.query(models.GoogleIdentity).count(), 1)

    def test_bad_claims_never_create_accounts(self):
        for changes in [dict(aud='other-app'), dict(iss='evil'), dict(email_verified=False),
                        dict(nonce='another-browser'), dict(sub='')]:
            with self.subTest(changes=changes):self.assertEqual(self.exchange(**changes).status_code, 401)
        self.assertEqual(self.session.query(models.User).count(), 0)

    def test_disabled_and_cross_site_requests_rejected(self):
        with patch.object(get_settings(), 'GOOGLE_CLIENT_ID', ''):
            self.assertEqual(self.exchange().status_code, 503)
        response = self.client.post('/api/auth/google', json={'credential':'x','nonce':NONCE}, headers={'Origin':'https://evil.example'})
        self.assertEqual(response.status_code, 403)

    def test_only_authoritative_google_email_can_link_existing_account(self):
        user = models.User(name='Original', email='person@other.example', hashed_password=hash_password('test-password'))
        self.session.add(user); self.session.commit()
        self.assertEqual(self.exchange(email=user.email).status_code, 409)
        user.email = 'person@gmail.com'; self.session.commit()
        response = self.exchange()
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()['user_id'], str(user.id))
        self.assertEqual(self.exchange(sub='different-google-sub').status_code, 409)

    def test_disabled_linked_user_cannot_sign_in(self):
        self.exchange()
        user = self.session.query(models.User).one(); user.is_active = False; self.session.commit()
        self.assertEqual(self.exchange().status_code, 403)

    def test_invalid_token_and_network_errors_are_sanitized(self):
        for error, status in [(ValueError('secret-token'), 401), (RuntimeError('secret-token'), 503)]:
            with patch('google_login.verify_google_credential', side_effect=error):
                response = self.client.post('/api/auth/google', json={'credential':'x','nonce':NONCE}, headers={'Origin':ORIGIN})
            self.assertEqual(response.status_code, status)
            self.assertNotIn('secret-token', response.text)

    def test_real_verifier_checks_signature_expiry_and_audience(self):
        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        private = key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption())
        public = key.public_key().public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo).decode()
        now = int(time.time())
        claims = {**self.claims, 'iat':now-10, 'exp':now+300}
        with patch('google.oauth2.id_token._fetch_certs', return_value={'test-key':public}):
            valid = jwt.encode(claims, private, algorithm='RS256', headers={'kid':'test-key'})
            self.assertEqual(verify_google_credential(valid, CLIENT)['sub'], self.claims['sub'])
            for bad in [dict(aud='other-client'), dict(exp=now-100)]:
                token = jwt.encode({**claims, **bad}, private, algorithm='RS256', headers={'kid':'test-key'})
                with self.assertRaises(ValueError):verify_google_credential(token, CLIENT)
            other = rsa.generate_private_key(public_exponent=65537, key_size=2048)
            other_private = other.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption())
            forged = jwt.encode(claims, other_private, algorithm='RS256', headers={'kid':'test-key'})
            with self.assertRaises(ValueError):verify_google_credential(forged, CLIENT)


if __name__ == '__main__': unittest.main()
