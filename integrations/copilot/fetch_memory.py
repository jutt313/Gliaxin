#!/usr/bin/env python3
"""
Fetch Gliaxin memory and write to .gliaxin-context.txt in the current directory.
Usage: python3 fetch_memory.py "your search query"
"""
import json
import os
import sys
import urllib.parse
import urllib.request

API_URL = os.getenv("GLIAXIN_API_URL", "http://localhost:9823")
API_KEY = os.getenv("GLIAXIN_API_KEY", "")
USER_ID = os.getenv("GLIAXIN_USER_ID", "local")

query = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "current work"
limit = 8

url = f"{API_URL}/v1/memory/search?query={urllib.parse.quote(query)}&end_user_id={urllib.parse.quote(USER_ID)}&limit={limit}"
req = urllib.request.Request(url, headers={"X-Api-Key": API_KEY})

try:
    with urllib.request.urlopen(req, timeout=5) as resp:
        data = json.loads(resp.read())
except Exception as e:
    print(f"Gliaxin fetch failed: {e}", file=sys.stderr)
    sys.exit(0)

memories = data.get("memories", [])
if not memories:
    print("No memories found.")
    sys.exit(0)

lines = ["--- Gliaxin Memory ---"]
for m in memories:
    lines.append(m.get("content", ""))
lines.append("--- End Memory ---")

output = "\n".join(lines)

with open(".gliaxin-context.txt", "w") as f:
    f.write(output)

print(f"Wrote {len(memories)} memories to .gliaxin-context.txt")
