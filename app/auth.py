import httpx
from jose import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from os import getenv

KEYCLOAK_URL = getenv('KEYCLOAK_URL')
REALM = getenv('KEYCLOAK_REALM')
CLIENT_ID = getenv('KEYCLOAK_CLIENT_ID')

oauth2_scheme = OAuth2PasswordBearer(
  tokenUrl=f'{KEYCLOAK_URL}/realms/{REALM}/protocol/openid-connect/token'
)

JWKS_URL = f'{KEYCLOAK_URL}/realms/{REALM}/protocol/openid-connect/certs'


async def get_public_key(kid: str):
  async with httpx.AsyncClient() as client:
      resp = await client.get(JWKS_URL)
      resp.raise_for_status()
      keys = resp.json()['keys']

  for key in keys:
      if key['kid'] == kid:
          return key
  raise HTTPException(status_code=401, detail='Invalid token')


async def get_current_user(token: str = Depends(oauth2_scheme)):
  header = jwt.get_unverified_header(token)
  key = await get_public_key(header['kid'])

  try:
      payload = jwt.decode(
          token,
          key,
          algorithms=['RS256'],
          audience='account',
          options={'verify_exp': True},
      )
  except Exception as e:
      raise HTTPException(status_code=401, detail=f'Invalid token: {str(e)}')

  return payload

def require_role(role: str):
  def checker(user=Depends(get_current_user)):
      roles = user.get('realm_access', {}).get('roles', [])
      
      if 'admin' in roles:
        return user

      if role not in roles:
          raise HTTPException(
              status_code=status.HTTP_403_FORBIDDEN,
              detail='Insufficient permissions',
          )
      return user

  return checker

