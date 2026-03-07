import os
import urllib.parse
from sqlalchemy.engine import make_url

raw_url = "postgresql://postgres.klqpapkkkanglnpnfvrz:ghkd96529652!@aws-1-ap-northeast-2.pooler.supabase.com:5432/postgres"

# Original logic
prefix_part, rest = raw_url.split("://", 1)
auth_part, host_part = rest.split("@", 1)
user_part, pass_part = auth_part.split(":", 1)
encoded_pass = urllib.parse.quote_plus(pass_part)
safe_url = f"{prefix_part}://{user_part}:{encoded_pass}@{host_part}"

print("Safe URL:", safe_url)

# Add query strings
connection_url = safe_url
connection_url += "?connect_timeout=10&keepalives_idle=30&keepalives_interval=10&keepalives_count=5"
print("Final URL:", connection_url)

try:
    url = make_url(connection_url)
    print("Parsed OK:", url)
except Exception as e:
    print("ERROR:", e)
