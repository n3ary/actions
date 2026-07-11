#!/usr/bin/env python3
"""
set-secret.py - set a GitHub Actions secret via libsodium sealed-box.

Why: `gh secret set SECRET < file` parses the value as dotenv and
*silently* corrupts PEM-shaped values (private keys, JWT tokens with
`==` padding, anything with `=` or `-` characters). The corrupted
value lands in the GH secret store and a workflow that reads the
secret gets gibberish. The same bug bit us in n3ary/gtfs-publisher
on HETZNER_SSH_KEY (2026-07-10).

The fix: use the GH REST API with libsodium sealed-box encryption.
This is exactly what `gh` does internally, but `gh` adds a dotenv
preprocessor that mangles PEM/JWT values. This script skips the
preprocessor and uses the raw API.

Usage:
  set-secret.py REPO SECRET [VALUE_FILE]
  set-secret.py REPO SECRET -                # read from stdin
  set-secret.py REPO SECRET --delete          # delete the secret

Examples:
  # from a file
  set-secret.py n3ary/gtfs-publisher HETZNER_SSH_KEY ~/.ssh/deploy_key

  # from stdin
  cat deploy_key | set-secret.py n3ary/gtfs-publisher HETZNER_SSH_KEY -

  # dry-run (encrypt + print, don't set)
  set-secret.py n3ary/gtfs-publisher HETZNER_SSH_KEY ~/.ssh/deploy_key --dry-run

  # delete
  set-secret.py n3ary/gtfs-publisher OLD_SECRET --delete

Required: `gh` CLI authenticated for the target repo (uses gh auth
token for the API call). `pynacl` for the sealed-box encryption
(auto-installed into a venv on first run if missing).
"""

import argparse
import base64
import json
import os
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request

API = "https://api.github.com"


def die(msg, code=1):
    print(f"error: {msg}", file=sys.stderr)
    sys.exit(code)


def ensure_pynacl():
    """Make sure pynacl is importable. Auto-install into a venv if not."""
    try:
        import nacl.public  # noqa: F401
        return
    except ImportError:
        pass
    venv = os.path.expanduser("~/.local/share/gh-set-secret-venv")
    site_pkgs = os.path.join(venv, "lib", f"python{sys.version_info.major}.{sys.version_info.minor}", "site-packages")
    if os.path.isdir(site_pkgs):
        sys.path.insert(0, site_pkgs)
        try:
            import nacl.public  # noqa: F401
            return
        except ImportError:
            pass
    print("pynacl not found - bootstrapping venv at", venv, file=sys.stderr)
    subprocess.check_call([sys.executable, "-m", "venv", venv])
    subprocess.check_call([os.path.join(venv, "bin", "pip"), "install", "--quiet", "pynacl"])
    sys.path.insert(0, site_pkgs)
    import nacl.public  # noqa: F401  (re-import after install)


def gh(method, path, body=None):
    """Authenticated GH REST API call. Returns parsed JSON or raw text."""
    token = subprocess.check_output(["gh", "auth", "token"], text=True).strip()
    req = urllib.request.Request(
        f"{API}{path}",
        method=method,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "n3ary-set-secret/1.0",
        },
    )
    data = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, data=data) as resp:
            body_text = resp.read().decode("utf-8")
            if not body_text:
                return None
            return json.loads(body_text)
    except urllib.error.HTTPError as e:
        body_text = e.read().decode("utf-8", errors="replace")
        die(f"GH API {method} {path} -> {e.code}\n{body_text}")


def get_public_key(repo):
    data = gh("GET", f"/repos/{repo}/actions/secrets/public-key")
    return data["key_id"], data["key"]


def encrypt(public_key_b64, plaintext):
    from nacl.public import PublicKey, SealedBox
    pk = PublicKey(base64.b64decode(public_key_b64))
    return SealedBox(pk).encrypt(plaintext)


def set_secret(repo, name, plaintext):
    key_id, pub_key = get_public_key(repo)
    encrypted = encrypt(pub_key, plaintext)
    body = {
        "encrypted_value": base64.b64encode(encrypted).decode("ascii"),
        "key_id": key_id,
    }
    gh("PUT", f"/repos/{repo}/actions/secrets/{name}", body=body)


def delete_secret(repo, name):
    gh("DELETE", f"/repos/{repo}/actions/secrets/{name}")


def list_secrets(repo):
    return gh("GET", f"/repos/{repo}/actions/secrets")


def main():
    p = argparse.ArgumentParser(
        description="Set a GitHub Actions secret via libsodium sealed-box.",
    )
    p.add_argument("repo", help="owner/repo (e.g. n3ary/gtfs-publisher)")
    p.add_argument("secret", help="secret name (case-sensitive)")
    p.add_argument(
        "value",
        nargs="?",
        help="value file, or '-' for stdin. Required unless --delete.",
    )
    p.add_argument("--delete", action="store_true", help="delete the secret")
    p.add_argument("--dry-run", action="store_true", help="encrypt + print, don't set")
    p.add_argument(
        "--verify",
        action="store_true",
        default=True,
        help="verify the secret was set (read updated_at after PUT)",
    )
    args = p.parse_args()

    if not args.delete and not args.value:
        die("value is required (or pass --delete)")

    if args.delete:
        delete_secret(args.repo, args.secret)
        print(f"deleted: {args.repo} -> {args.secret}")
        return

    if args.value == "-":
        plaintext = sys.stdin.buffer.read()
    else:
        with open(args.value, "rb") as f:
            plaintext = f.read()

    if args.dry_run:
        key_id, pub_key = get_public_key(args.repo)
        encrypted = encrypt(pub_key, plaintext)
        b64 = base64.b64encode(encrypted).decode("ascii")
        print(f"would PUT: {args.repo} -> {args.secret}")
        print(f"  plaintext size:  {len(plaintext)} bytes")
        print(f"  ciphertext size: {len(encrypted)} bytes")
        print(f"  base64 size:     {len(b64)} chars")
        print(f"  key_id:          {key_id}")
        print(f"  first 60 of b64: {b64[:60]}...")
        return

    before = list_secrets(args.repo).get("secrets", [])
    before_seen = next((s for s in before if s["name"] == args.secret), None)
    before_updated = before_seen["updated_at"] if before_seen else None

    set_secret(args.repo, args.secret, plaintext)

    if args.verify:
        after = list_secrets(args.repo).get("secrets", [])
        after_seen = next((s for s in after if s["name"] == args.secret), None)
        if not after_seen:
            die(f"verification failed: {args.secret} not in secret list after PUT")
        if before_updated and after_seen["updated_at"] == before_updated:
            die(f"verification failed: updated_at unchanged ({before_updated})")
        print(
            f"ok: {args.repo} -> {args.secret} "
            f"(updated_at {before_updated} -> {after_seen['updated_at']}, "
            f"plaintext {len(plaintext)} bytes)"
        )
    else:
        print(f"set: {args.repo} -> {args.secret}")


if __name__ == "__main__":
    ensure_pynacl()
    main()
