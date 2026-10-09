"""Create/update local Nexer auth settings without storing a plaintext password."""

from __future__ import annotations

import getpass
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = ROOT / ".env"


def main() -> int:
    username = input("Usuário local do Nexer: ").strip()
    if not re.fullmatch(r"[A-Za-z0-9_.-]{1,80}", username):
        print("Usuário inválido.", file=sys.stderr)
        return 2

    password = getpass.getpass("Nova senha (mínimo 12 caracteres): ")
    confirmation = getpass.getpass("Confirme a senha: ")
    if password != confirmation:
        print("As senhas não coincidem.", file=sys.stderr)
        return 2

    sys.path.insert(0, str(ROOT / "apps" / "backend"))
    from app.security import hash_password

    try:
        password_hash = hash_password(password)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    finally:
        password = ""
        confirmation = ""

    values = {
        "NEXER_AUTH_USERNAME": username,
        "NEXER_AUTH_PASSWORD_HASH": password_hash,
    }
    lines = ENV_FILE.read_text(encoding="utf-8").splitlines() if ENV_FILE.exists() else []
    keys = set(values)
    lines = [line for line in lines if line.split("=", 1)[0].strip() not in keys]
    lines.extend(f"{key}={value}" for key, value in values.items())
    ENV_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Autenticação local configurada em {ENV_FILE}. A senha não foi gravada em texto claro.")
    print("Reinicie o backend para carregar a configuração.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
