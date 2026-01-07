# Script PowerShell para parsear YAML y extraer variables
$envFile = $args[0]

if (-not (Test-Path $envFile)) {
    Write-Error "Archivo no encontrado: $envFile"
    exit 1
}

$content = Get-Content $envFile -Raw
$lines = $content -split "`n"

foreach ($line in $lines) {
    $trimmed = $line.Trim()
    if ($trimmed -and -not $trimmed.StartsWith('#')) {
        if ($trimmed -match '^([A-Z_]+):\s*"(.*)"$') {
            $key = $matches[1]
            $value = $matches[2]
            Write-Output "$key=$value"
        }
    }
}
