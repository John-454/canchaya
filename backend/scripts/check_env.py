"""Diagnóstico de .env: muestra la forma de DATABASE_URL sin exponer secretos."""

import os
import re
from pathlib import Path
from urllib.parse import urlparse

from decouple import config

raw = config("DATABASE_URL", default="")
raw = re.sub(r"@\[([^\]]+)\]", r"@\1", raw).replace("[", "").replace("]", "")
if not raw:
    print("DATABASE_URL: VACIA")
else:
    p = urlparse(raw)
    print("scheme :", p.scheme)
    print("host   :", p.hostname)
    print("port   :", p.port)
    print("dbname :", (p.path or "").lstrip("/"))
    user = p.username or ""
    print("user   :", user, "| tiene punto (ref)?", "." in user)
    print("password presente:", bool(p.password), "| len:", len(p.password or ""))
    if p.password and (p.password.startswith("<") or p.password.endswith(">")):
        print("password parece PLACEHOLDER")
    if "[" in raw or "]" in raw:
        print("ADVERTENCIA: la URI contiene corchetes literales")
    for token in ("<ref>", "<password>", "<region>", "<PASSWORD>"):
        if token in raw:
            print("ADVERTENCIA: contiene el placeholder", token)

env_path = Path(__file__).resolve().parent.parent / ".env"
print("archivo .env:", env_path, "existe:", env_path.exists())
if env_path.exists():
    claves = [
        linea.split("=", 1)[0].strip()
        for linea in env_path.read_text(encoding="utf-8").splitlines()
        if "=" in linea and not linea.strip().startswith("#")
    ]
    print("claves definidas:", claves)
print(
    "SUPABASE_URL definida:",
    bool(os.environ.get("SUPABASE_URL") or config("SUPABASE_URL", default="")),
)
