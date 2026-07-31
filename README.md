# MCP SQL Server Read-Only Investigator

Servidor MCP local para investigar SQL Server desde Claude Desktop, Claude Code o Codex. Expone tools de solo lectura para explorar esquemas, tablas, columnas, indices, claves foraneas, dependencias, muestras controladas, consultas `SELECT` capadas y planes estimados.

## Instalacion Rapida

1. Instala `uv`.
2. Instala un driver ODBC para SQL Server.
3. Clona este repositorio.
4. Crea y completa `.env` a partir de `.env.example`.
5. Ejecuta el instalador del cliente que uses:
   - Claude Desktop: `scripts\install-claude-desktop.ps1`
   - Codex: `scripts\install-codex.ps1`
6. Reinicia el cliente.

## Requisitos

- Windows 10/11.
- Acceso al SQL Server o a su replica.
- PowerShell.
- `uv`.
- Un driver ODBC de SQL Server:
  - recomendado: `ODBC Driver 18 for SQL Server`
  - alternativa: `ODBC Driver 17 for SQL Server`

## Como instalar los requisitos

### 1. Instalar uv

Opcion recomendada:

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

Verificacion:

```powershell
uv --version
```

### 2. Instalar ODBC Driver para SQL Server

Instala uno de estos paquetes oficiales de Microsoft:

- `ODBC Driver 18 for SQL Server`
- `ODBC Driver 17 for SQL Server`

Verificacion rapida en PowerShell:

```powershell
Get-OdbcDriver | Where-Object { $_.Name -like '*SQL Server*' } | Select-Object Name
```

## Preparar el proyecto

Clona el repositorio y entra al directorio:

```powershell
git clone <URL_DEL_REPO>
cd mcp_sql_sever
```

Copia `.env.example` a `.env` y completa los valores.

### Ejemplo para SQL Authentication

```env
MSSQL_SERVER=mi-servidor
MSSQL_AUTH=sql
MSSQL_DATABASE=mi_base_replica
MSSQL_USERNAME=readonly_user
MSSQL_PASSWORD=tu_password
MSSQL_DRIVER=ODBC Driver 18 for SQL Server
MSSQL_ENCRYPT=yes
MSSQL_TRUST_SERVER_CERTIFICATE=yes
MCP_SQL_MAX_ROWS=200
MCP_SQL_TIMEOUT_SECONDS=30
```

### Ejemplo para Windows Authentication

```env
MSSQL_SERVER=localhost\SQLEXPRESS
MSSQL_AUTH=windows
MSSQL_DATABASE=
MSSQL_DRIVER=ODBC Driver 18 for SQL Server
MSSQL_ENCRYPT=yes
MSSQL_TRUST_SERVER_CERTIFICATE=yes
MCP_SQL_MAX_ROWS=200
MCP_SQL_TIMEOUT_SECONDS=30
```

Notas:

- `MSSQL_DATABASE=` vacio usa la base por defecto del login.
- Si `ODBC Driver 18` da problemas en una instancia local, el conector intenta fallbacks controlados con `Encrypt=no`, `ODBC Driver 17` y el driver legado `SQL Server`.
- No guardes secretos en el repo.

## Registrar el MCP en Codex

Este repo incluye un instalador para Codex:

```powershell
.\scripts\install-codex.ps1
```

Ese script:

- crea backup de `C:\Users\TU_USUARIO\.codex\config.toml` si ya existe
- preserva el resto de la configuracion
- registra o actualiza `mcp_sql_server`
- habilita el MCP
- deja todas las tools en modo `approve`

Opciones utiles:

```powershell
.\scripts\install-codex.ps1 -ServerName "sql_server_readonly"
.\scripts\install-codex.ps1 -UvPath "C:\Users\TU_USUARIO\.local\bin\uv.exe"
.\scripts\install-codex.ps1 -CodexConfigPath "$env:USERPROFILE\.codex\config.toml"
```

## Configuracion manual de Codex

Si prefieres editar el archivo a mano, agrega esta entrada en:

`%USERPROFILE%\.codex\config.toml`

```toml
[mcp_servers.mcp_sql_server]
command = "C:\\Users\\TU_USUARIO\\.local\\bin\\uv.exe"
args = [
  "--directory",
  "C:\\ruta\\a\\mcp_sql_sever",
  "run",
  "--python",
  "3.12",
  "mcp-sql-server"
]
env = { UV_CACHE_DIR = "C:\\ruta\\a\\mcp_sql_sever\\.uv-cache", UV_PYTHON_INSTALL_DIR = "C:\\ruta\\a\\mcp_sql_sever\\.uv-python" }
enabled = true

[mcp_servers.mcp_sql_server.tools.server_info]
approval_mode = "approve"

[mcp_servers.mcp_sql_server.tools.list_schemas]
approval_mode = "approve"

[mcp_servers.mcp_sql_server.tools.list_tables]
approval_mode = "approve"

[mcp_servers.mcp_sql_server.tools.describe_table]
approval_mode = "approve"

[mcp_servers.mcp_sql_server.tools.search_columns]
approval_mode = "approve"

[mcp_servers.mcp_sql_server.tools.table_profile]
approval_mode = "approve"

[mcp_servers.mcp_sql_server.tools.index_info]
approval_mode = "approve"

[mcp_servers.mcp_sql_server.tools.foreign_keys]
approval_mode = "approve"

[mcp_servers.mcp_sql_server.tools.dependencies]
approval_mode = "approve"

[mcp_servers.mcp_sql_server.tools.sample_rows]
approval_mode = "approve"

[mcp_servers.mcp_sql_server.tools.run_select]
approval_mode = "approve"

[mcp_servers.mcp_sql_server.tools.explain_select]
approval_mode = "approve"
```

El MCP carga la conexion SQL desde `.env`, por lo que no hace falta meter `MSSQL_*` dentro del TOML de Codex.

## Registrar el MCP en Claude Desktop

Este repo incluye un instalador para Claude Desktop:

```powershell
.\scripts\install-claude-desktop.ps1
```

Ese script:

- crea backup del `claude_desktop_config.json` si ya existe
- preserva otros MCPs configurados
- registra `mcp-sql-server`
- escribe JSON valido en UTF-8 sin BOM

Opciones utiles:

```powershell
.\scripts\install-claude-desktop.ps1 -ServerName "sql-server-readonly"
.\scripts\install-claude-desktop.ps1 -UvPath "C:\Users\TU_USUARIO\.local\bin\uv.exe"
.\scripts\install-claude-desktop.ps1 -ClaudeConfigPath "$env:APPDATA\Claude\claude_desktop_config.json"
```

## Configuracion manual de Claude Desktop

Si prefieres editar el archivo a mano, agrega esta entrada en:

`%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "mcp-sql-server": {
      "command": "C:\\Users\\TU_USUARIO\\.local\\bin\\uv.exe",
      "args": [
        "--directory",
        "C:\\ruta\\a\\mcp_sql_sever",
        "run",
        "--python",
        "3.12",
        "mcp-sql-server"
      ],
      "env": {
        "UV_CACHE_DIR": "C:\\ruta\\a\\mcp_sql_sever\\.uv-cache",
        "UV_PYTHON_INSTALL_DIR": "C:\\ruta\\a\\mcp_sql_sever\\.uv-python"
      }
    }
  }
}
```

El MCP carga la conexion SQL desde `.env`, por lo que no hace falta meter `MSSQL_*` dentro del JSON de Claude Desktop.

## Probar el MCP

Arranque local:

```powershell
uv run --python 3.12 mcp-sql-server
```

Tests:

```powershell
uv run --python 3.12 pytest
```

Prueba en Codex o Claude Desktop:

1. Reinicia Codex o Claude Desktop.
2. Abre un chat nuevo.
3. Pide:

```text
Usa mcp_sql_server y ejecuta server_info, luego list_schemas.
```

## Tools disponibles

- `server_info`
- `list_schemas`
- `list_tables`
- `describe_table`
- `search_columns`
- `table_profile`
- `index_info`
- `foreign_keys`
- `dependencies`
- `sample_rows`
- `run_select`
- `explain_select`

## Politica de seguridad

- Solo permite `SELECT` y CTEs de lectura.
- Bloquea comentarios, multiples statements, `USE`, `EXEC`, DML, DDL, `MERGE`, `TRUNCATE` y `SELECT INTO`.
- Limita filas y timeout.
- Enmascara columnas sensibles por nombre.
- Fuerza una sola conexion configurada por `.env`.

## Distribucion a otras personas

Para que otro usuario lo instale en su Claude Desktop necesita:

1. Este repositorio.
2. `uv`.
3. Un ODBC Driver de SQL Server.
4. Su propio `.env` con acceso a su SQL Server.
5. Ejecutar `.\scripts\install-codex.ps1` o `.\scripts\install-claude-desktop.ps1`, segun el cliente.

No hace falta que edite Python, ni que toque la configuracion del cliente a mano, salvo que quiera una configuracion personalizada.
