"""Google Identity Services token exchange. No client secret or redirect token URL."""
import secrets
import uuid
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from auth import create_access_token, hash_password
from config import get_settings
from database import get_db
import models
from schemas import TokenResponse

router = APIRouter(prefix='/api/auth/google', tags=['Auth'])


class GoogleCredential(BaseModel):
    credential: str = Field(min_length=1, max_length=16384)
    nonce: str = Field(min_length=16, max_length=128)


def verify_google_credential(credential, audience):
    from google.auth.transport.requests import Request as GoogleRequest
    from google.oauth2.id_token import verify_oauth2_token
    transport = GoogleRequest()
    def bounded_request(url, method='GET', **kwargs):
        kwargs['timeout'] = 10
        return transport(url, method=method, **kwargs)
    return verify_oauth2_token(credential, bounded_request, audience=audience)


@router.get('/config')
def google_config():
    return {'client_id': get_settings().GOOGLE_CLIENT_ID}


@router.post('', response_model=TokenResponse)
def google_login(payload: GoogleCredential, request: Request, db: Session = Depends(get_db)):
    settings = get_settings()
    if not settings.GOOGLE_CLIENT_ID:
        raise HTTPException(503, 'Google sign-in is not available yet. Please use email and password.')
    # GIS popup credentials are posted as JSON from our own frontend, not as a
    # cross-site HTML form. Reject other origins before verifying credentials.
    if request.headers.get('origin') not in settings.allowed_origins_list:
        raise HTTPException(403, 'Sign-in origin is not allowed')
    try:
        claims = verify_google_credential(payload.credential, settings.GOOGLE_CLIENT_ID)
    except ValueError:
        raise HTTPException(401, 'Google sign-in expired or is invalid. Please try again.') from None
    except Exception:
        raise HTTPException(503, 'Google sign-in could not be verified. Please try again.') from None
    if (claims.get('iss') not in ('accounts.google.com', 'https://accounts.google.com')
            or claims.get('aud') != settings.GOOGLE_CLIENT_ID
            or not claims.get('sub') or claims.get('email_verified') is not True
            or not isinstance(claims.get('nonce'), str)
            or not secrets.compare_digest(claims['nonce'], payload.nonce)):
        raise HTTPException(401, 'Google sign-in could not be verified. Please try again.')
    email = str(claims.get('email', '')).strip().lower()
    if '@' not in email or len(email) > 255 or len(claims['sub']) > 255:
        raise HTTPException(401, 'Google did not provide a valid email address')
    identity = db.get(models.GoogleIdentity, claims['sub'])
    user = db.get(models.User, identity.user_id) if identity else None
    if not identity:
        user = db.query(models.User).filter(func.lower(models.User.email) == email).first()
        if user:
            # Google is not authoritative for a third-party email without hd.
            if not (email.endswith('@gmail.com') or claims.get('hd')):
                raise HTTPException(409, 'This email already has an account. Please sign in with your password.')
            linked = db.query(models.GoogleIdentity).filter(models.GoogleIdentity.user_id == user.id).first()
            if linked:
                raise HTTPException(409, 'Please use the Google account originally linked to this account.')
        else:
            user = models.User(id=uuid.uuid4(), email=email,
                               name=str(claims.get('name') or email.split('@')[0])[:200],
                               hashed_password=hash_password(secrets.token_urlsafe(48)))
            db.add(user)
        if not user.is_active and user.is_active is not None:
            raise HTTPException(403, 'This account is unavailable')
        try:
            db.flush()  # Persist a new user before its identity's foreign key.
            db.add(models.GoogleIdentity(subject=claims['sub'], user_id=user.id))
            db.commit()
        except IntegrityError:
            db.rollback()
            raise HTTPException(409, 'Account sign-in changed. Please try again.') from None
        db.refresh(user)
    if not user or not user.is_active:
        raise HTTPException(403, 'This account is unavailable')
    return TokenResponse(access_token=create_access_token(user.id, user.email),
                         user_id=user.id, name=user.name, email=user.email)
