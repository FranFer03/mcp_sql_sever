from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


DEFAULT_DRIVER = "ODBC Driver 18 for SQL Server"
DEFAULT_MAX_ROWS = 200
DEFAULT_TIMEOUT_SECONDS = 30
DEFAULT_AUTH = "sql"
DEFAULT_ENCRYPT = "yes"


class ConfigError(ValueError):
    """Raised when required runtime configuration is missing or invalid."""


@dataclass(frozen=True)
class Settings:
    server: str
    database: str = ""
    username: str = ""
    password: str = ""
    auth: str = DEFAULT_AUTH
    driver: str = DEFAULT_DRIVER
    encrypt: str = DEFAULT_ENCRYPT
    trust_server_certificate: str = "yes"
    max_rows: int = DEFAULT_MAX_ROWS
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS

    @classmethod
    def from_env(cls) -> "Settings":
        _load_dotenv()
        auth = os.getenv("MSSQL_AUTH", DEFAULT_AUTH).lower()
        if auth not in {"sql", "windows"}:
            raise ConfigError("MSSQL_AUTH must be either 'sql' or 'windows'")

        required = {"MSSQL_SERVER": os.getenv("MSSQL_SERVER")}
        if auth == "sql":
            required["MSSQL_USERNAME"] = os.getenv("MSSQL_USERNAME")
            required["MSSQL_PASSWORD"] = os.getenv("MSSQL_PASSWORD")
        missing = [name for name, value in required.items() if not value]
        if missing:
            raise ConfigError(f"Missing required environment variables: {', '.join(missing)}")

        return cls(
            server=required["MSSQL_SERVER"] or "",
            database=os.getenv("MSSQL_DATABASE", ""),
            username=os.getenv("MSSQL_USERNAME", ""),
            password=os.getenv("MSSQL_PASSWORD", ""),
            auth=auth,
            driver=os.getenv("MSSQL_DRIVER", DEFAULT_DRIVER),
            encrypt=_normalize_encrypt(os.getenv("MSSQL_ENCRYPT", DEFAULT_ENCRYPT)),
            trust_server_certificate=os.getenv("MSSQL_TRUST_SERVER_CERTIFICATE", "yes"),
            max_rows=_env_int("MCP_SQL_MAX_ROWS", DEFAULT_MAX_ROWS, minimum=1, maximum=10_000),
            timeout_seconds=_env_int(
                "MCP_SQL_TIMEOUT_SECONDS",
                DEFAULT_TIMEOUT_SECONDS,
                minimum=1,
                maximum=600,
            ),
        )

    def connection_string(self) -> str:
        parts = {
            "DRIVER": f"{{{self.driver}}}",
            "SERVER": self.server,
            "Encrypt": self.encrypt,
            "TrustServerCertificate": self.trust_server_certificate,
            "Connection Timeout": str(self.timeout_seconds),
            "ApplicationIntent": "ReadOnly",
            "Application Name": "mcp-sql-server-read-only",
        }
        if self.database:
            parts["DATABASE"] = self.database
        if self.auth == "windows":
            parts["Trusted_Connection"] = "yes"
        else:
            parts["UID"] = self.username
            parts["PWD"] = self.password
        return ";".join(f"{key}={value}" for key, value in parts.items())

    def with_overrides(
        self,
        *,
        driver: str | None = None,
        encrypt: str | None = None,
        server: str | None = None,
    ) -> "Settings":
        return Settings(
            server=server if server is not None else self.server,
            database=self.database,
            username=self.username,
            password=self.password,
            auth=self.auth,
            driver=driver if driver is not None else self.driver,
            encrypt=_normalize_encrypt(encrypt) if encrypt is not None else self.encrypt,
            trust_server_certificate=self.trust_server_certificate,
            max_rows=self.max_rows,
            timeout_seconds=self.timeout_seconds,
        )

    def public_dict(self) -> dict[str, object]:
        return {
            "server": self.server,
            "database": self.database or "<default>",
            "auth": self.auth,
            "username": _redact_identity(self.username) if self.username else "<windows>",
            "driver": self.driver,
            "encrypt": self.encrypt,
            "trust_server_certificate": self.trust_server_certificate,
            "max_rows": self.max_rows,
            "timeout_seconds": self.timeout_seconds,
            "application_intent": "ReadOnly",
        }


def _load_dotenv(path: str = ".env") -> None:
    env_path = Path(path)
    if not env_path.exists():
        return
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, value = line.split("=", 1)
        name = name.strip()
        value = value.strip().strip('"').strip("'")
        if name and name not in os.environ:
            os.environ[name] = value


def _env_int(name: str, default: int, *, minimum: int, maximum: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw == "":
        return default
    try:
        value = int(raw)
    except ValueError as exc:
        raise ConfigError(f"{name} must be an integer") from exc
    if not minimum <= value <= maximum:
        raise ConfigError(f"{name} must be between {minimum} and {maximum}")
    return value


def _normalize_encrypt(value: str) -> str:
    normalized = value.strip().lower()
    mapping = {
        "yes": "yes",
        "true": "yes",
        "mandatory": "yes",
        "strict": "yes",
        "optional": "no",
        "no": "no",
        "false": "no",
    }
    if normalized not in mapping:
        raise ConfigError(
            "MSSQL_ENCRYPT must be one of: yes, no, mandatory, optional, strict, true, false"
        )
    return mapping[normalized]


def _redact_identity(value: str) -> str:
    if len(value) <= 2:
        return "**"
    if "@" in value:
        local, domain = value.split("@", 1)
        return f"{local[:1]}***@{domain}"
    return f"{value[:1]}***{value[-1:]}"
