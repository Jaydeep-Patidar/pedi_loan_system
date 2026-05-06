import base64
import hashlib
import hmac
import json
import time

from django.conf import settings
from django.contrib.auth import get_user_model
from rest_framework import authentication
from rest_framework import exceptions

JWT_ALGORITHM = 'HS256'
ACCESS_TOKEN_LIFETIME = 60 * 60
REFRESH_TOKEN_LIFETIME = 24 * 60 * 60


def base64url_encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b'=').decode('utf-8')


def base64url_decode(value: str) -> bytes:
    padding = '=' * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)


def _sign(message: bytes, secret: str) -> str:
    signature = hmac.new(secret.encode('utf-8'), message, hashlib.sha256).digest()
    return base64url_encode(signature)


def generate_jwt_token(user, token_type='access') -> str:
    now = int(time.time())
    exp = now + (ACCESS_TOKEN_LIFETIME if token_type == 'access' else REFRESH_TOKEN_LIFETIME)
    payload = {
        'user_id': user.pk,
        'username': user.username,
        'token_type': token_type,
        'iat': now,
        'exp': exp,
    }
    header = {'alg': JWT_ALGORITHM, 'typ': 'JWT'}
    header_b64 = base64url_encode(json.dumps(header, separators=(',', ':')).encode('utf-8'))
    payload_b64 = base64url_encode(json.dumps(payload, separators=(',', ':')).encode('utf-8'))
    signature = _sign(f'{header_b64}.{payload_b64}'.encode('utf-8'), settings.SECRET_KEY)
    return f'{header_b64}.{payload_b64}.{signature}'


def decode_jwt_token(token, required_token_type='access') -> dict:
    try:
        header_b64, payload_b64, signature = token.split('.')
    except ValueError:
        raise exceptions.AuthenticationFailed('Invalid token format')

    try:
        expected_signature = _sign(f'{header_b64}.{payload_b64}'.encode('utf-8'), settings.SECRET_KEY)
        if not hmac.compare_digest(expected_signature, signature):
            raise exceptions.AuthenticationFailed('Invalid token signature')

        payload_bytes = base64url_decode(payload_b64)
        payload = json.loads(payload_bytes.decode('utf-8'))
    except (ValueError, json.JSONDecodeError):
        raise exceptions.AuthenticationFailed('Invalid token payload')

    now = int(time.time())
    if payload.get('exp') is None or now >= payload['exp']:
        raise exceptions.AuthenticationFailed('Token has expired')

    if payload.get('token_type') != required_token_type:
        raise exceptions.AuthenticationFailed('Invalid token type')

    return payload


class JWTAuthentication(authentication.BaseAuthentication):
    def authenticate(self, request):
        auth_header = authentication.get_authorization_header(request).split()
        if not auth_header or auth_header[0].lower() != b'bearer':
            return None

        if len(auth_header) != 2:
            raise exceptions.AuthenticationFailed('Invalid Authorization header')

        token = auth_header[1].decode('utf-8')
        payload = decode_jwt_token(token, required_token_type='access')
        User = get_user_model()
        try:
            user = User.objects.get(pk=payload.get('user_id'))
        except User.DoesNotExist:
            raise exceptions.AuthenticationFailed('User not found')

        if not user.is_active:
            raise exceptions.AuthenticationFailed('User is inactive')

        return (user, token)
