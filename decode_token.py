import json
import base64
import sys

token = sys.argv[1] if len(sys.argv) > 1 else input("Paste your token: ")

if token.startswith('Bearer '):
    token = token[7:]

parts = token.split('.')
if len(parts) != 3:
    print("Invalid token format")
    sys.exit(1)

payload = parts[1]
payload += '=' * (4 - len(payload) % 4)

try:
    decoded = base64.urlsafe_b64decode(payload)
    data = json.loads(decoded)
    print(json.dumps(data, indent=2))
    print(f"\nAudience (aud): {data.get('aud', 'NOT FOUND')}")
except Exception as e:
    print(f"Error: {e}")
