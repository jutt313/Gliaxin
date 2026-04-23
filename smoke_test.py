#!/usr/bin/env python3
"""
Gliaxin smoke test — run this after docker compose up to confirm everything works.
Usage: python3 smoke_test.py
"""

import json
import os
import sys
import time
import urllib.request
import urllib.error

API_URL = os.getenv("GLIAXIN_API_URL", "http://localhost:9823")
API_KEY = os.getenv("GLIAXIN_API_KEY", "")
USER_ID = os.getenv("GLIAXIN_USER_ID", "smoke-test-user")

PASS = "\033[92m  PASS\033[0m"
FAIL = "\033[91m  FAIL\033[0m"

errors = 0


def req(method, path, body=None):
    data = json.dumps(body).encode() if body else None
    r = urllib.request.Request(
        f"{API_URL}{path}",
        data=data,
        headers={"X-Api-Key": API_KEY, "Content-Type": "application/json"},
        method=method,
    )
    with urllib.request.urlopen(r, timeout=10) as resp:
        return json.loads(resp.read())


def check(label, fn):
    global errors
    try:
        result = fn()
        print(f"{PASS}  {label}")
        return result
    except Exception as e:
        print(f"{FAIL}  {label}")
        print(f"        {e}")
        errors += 1
        return None


print(f"\nGliaxin smoke test — {API_URL}\n")

# 1. Health check
check("API is up (/health)", lambda: req("GET", "/health"))

# 2. Auth check — wrong key should 401
def auth_check():
    r = urllib.request.Request(
        f"{API_URL}/v1/memory/get?end_user_id={USER_ID}",
        headers={"X-Api-Key": "wrong-key"},
    )
    try:
        urllib.request.urlopen(r, timeout=5)
        raise AssertionError("Expected 401 but got 200")
    except urllib.error.HTTPError as e:
        assert e.code == 401, f"Expected 401, got {e.code}"

check("Auth rejects bad API key", auth_check)

# 3. Add a memory turn
layer_a_id = None

def add_memory():
    global layer_a_id
    result = req("POST", "/v1/memory/add", {
        "end_user_id": USER_ID,
        "messages": [
            {"role": "user", "content": "I prefer TypeScript over JavaScript for all new projects."},
            {"role": "assistant", "content": "Got it, I'll use TypeScript going forward."},
        ],
    })
    assert "layer_a_id" in result, f"Missing layer_a_id in response: {result}"
    layer_a_id = result["layer_a_id"]

check("POST /v1/memory/add", add_memory)

# 4. Wait for worker to extract
print(f"\n  Waiting 12s for background worker to extract memories...\n")
time.sleep(12)

# 5. Search for the memory
def search_memory():
    result = req("GET", f"/v1/memory/search?query=TypeScript&end_user_id={USER_ID}&limit=5")
    memories = result.get("memories", [])
    assert len(memories) > 0, "Search returned no memories — worker may not have extracted yet"

check("GET /v1/memory/search returns results", search_memory)

# 6. Get memory list
def get_memories():
    result = req("GET", f"/v1/memory/get?end_user_id={USER_ID}&limit=10")
    assert "memories" in result

check("GET /v1/memory/get", get_memories)

# 7. Conflicts endpoint
check("GET /v1/memory/conflicts", lambda: req("GET", f"/v1/memory/conflicts?end_user_id={USER_ID}"))

# 8. Clean up — forget test user
check("DELETE /v1/memory/forget (cleanup)", lambda: req("DELETE", f"/v1/memory/forget?end_user_id={USER_ID}"))

# Result
print()
if errors == 0:
    print("\033[92mAll checks passed. Gliaxin is working.\033[0m\n")
else:
    print(f"\033[91m{errors} check(s) failed. See above.\033[0m\n")
    print("Common fixes:")
    print("  - API not up: run 'docker compose up -d' from the oss/ folder")
    print("  - 401 errors: set GLIAXIN_API_KEY to match OSS_API_KEY in .env")
    print("  - Search empty: check worker logs with 'docker compose logs api --tail=30'")
    print()
    sys.exit(1)
