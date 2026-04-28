param(
    [string]$ServerName = "mcp-sql-server",
    [string]$ClaudeConfigPath = "$env:APPDATA\Claude\claude_desktop_config.json",
    [string]$ProjectDir = (Split-Path -Parent $PSScriptRoot),
    [string]$UvPath = ""
)

$ErrorActionPreference = "Stop"

function Resolve-UvPath {
    param([string]$Candidate)

    if ($Candidate -and (Test-Path -LiteralPath $Candidate)) {
        return (Resolve-Path -LiteralPath $Candidate).Path
    }

    $command = Get-Command uv -ErrorAction SilentlyContinue
    if ($command) {
        return $command.Source
    }

    $fallback = Join-Path $env:USERPROFILE ".local\bin\uv.exe"
    if (Test-Path -LiteralPath $fallback) {
        return $fallback
    }

    throw "No se encontro uv. Instalalo primero o pasa -UvPath con la ruta completa a uv.exe."
}

function Read-ClaudeConfig {
    param([string]$Path)

    if (-not (Test-Path -LiteralPath $Path)) {
        return [pscustomobject]@{
            mcpServers = [pscustomobject]@{}
        }
    }

    $raw = Get-Content -LiteralPath $Path -Raw
    if (-not $raw.Trim()) {
        return [pscustomobject]@{
            mcpServers = [pscustomobject]@{}
        }
    }

    return $raw | ConvertFrom-Json
}

$resolvedProjectDir = (Resolve-Path -LiteralPath $ProjectDir).Path
$resolvedUvPath = Resolve-UvPath -Candidate $UvPath

if (-not (Test-Path -LiteralPath (Join-Path $resolvedProjectDir ".env"))) {
    throw "Falta el archivo .env en $resolvedProjectDir. Crea y completa .env antes de registrar el MCP."
}

$configDir = Split-Path -Parent $ClaudeConfigPath
if (-not (Test-Path -LiteralPath $configDir)) {
    New-Item -ItemType Directory -Path $configDir | Out-Null
}

$config = Read-ClaudeConfig -Path $ClaudeConfigPath
if (-not $config.mcpServers) {
    $config | Add-Member -MemberType NoteProperty -Name mcpServers -Value ([pscustomobject]@{})
}

$entry = [pscustomobject]@{
    command = $resolvedUvPath
    args = @(
        "--directory",
        $resolvedProjectDir,
        "run",
        "--python",
        "3.12",
        "mcp-sql-server"
    )
    env = [pscustomobject]@{
        UV_CACHE_DIR = (Join-Path $resolvedProjectDir ".uv-cache")
        UV_PYTHON_INSTALL_DIR = (Join-Path $resolvedProjectDir ".uv-python")
    }
}

if ($config.mcpServers.PSObject.Properties.Name -contains $ServerName) {
    $config.mcpServers.$ServerName = $entry
}
else {
    $config.mcpServers | Add-Member -MemberType NoteProperty -Name $ServerName -Value $entry
}

if (Test-Path -LiteralPath $ClaudeConfigPath) {
    $backup = "$ClaudeConfigPath.bak-$(Get-Date -Format yyyyMMddHHmmss)"
    Copy-Item -LiteralPath $ClaudeConfigPath -Destination $backup
    Write-Output "Backup: $backup"
}

$json = $config | ConvertTo-Json -Depth 20
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText($ClaudeConfigPath, $json, $utf8NoBom)

$validated = Get-Content -LiteralPath $ClaudeConfigPath -Raw | ConvertFrom-Json
$serverList = $validated.mcpServers.PSObject.Properties.Name -join ", "

Write-Output "Claude Desktop configurado."
Write-Output "ServerName: $ServerName"
Write-Output "ProjectDir: $resolvedProjectDir"
Write-Output "uv: $resolvedUvPath"
Write-Output "MCPs actuales: $serverList"
