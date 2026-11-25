"""Consulta el JWKS y los algoritmos que anuncia el proyecto Supabase."""

import json
from pathlib import Path

import requests
from decouple import config


def leer_frontend_env() -> dict:
    ruta = Path(__file__).resolve().parent.parent.parent / "frontend" / ".env"
    valores: dict = {}
    if ruta.exists():
        for linea in ruta.read_text(encoding="utf-8").splitlines():
            if "=" in linea and not linea.strip().startswith("#"):
                clave, valor = linea.split("=", 1)
                valores[clave.strip()] = valor.strip()
    return valores


env = leer_frontend_env()
backend_url = config("SUPABASE_URL", default="").rstrip("/")
frontend_url = env.get("VITE_SUPABASE_URL", "").rstrip("/")
url = frontend_url or backend_url

print("backend  SUPABASE_URL:", backend_url or "(vacio)")
print("frontend VITE_SUPABASE_URL:", frontend_url or "(vacio)")
print("coinciden:", backend_url == frontend_url)
print("JWT secret definido:", bool(config("SUPABASE_JWT_SECRET", default="")))

r = requests.get(f"{url}/auth/v1/.well-known/jwks.json", timeout=15)
print(f"\nJWKS {url} -> HTTP {r.status_code}")
try:
    claves = r.json().get("keys", [])
    print(f"claves: {len(claves)}")
    for k in claves:
        print(
            "  kid=", k.get("kid"), "kty=", k.get("kty"), "alg=", k.get("alg"), "use=", k.get("use")
        )
except json.JSONDecodeError:
    print("respuesta no JSON:", r.text[:200])
