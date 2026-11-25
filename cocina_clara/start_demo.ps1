$ErrorActionPreference = "Stop"

$projectRoot = $PSScriptRoot
$packagesPath = Join-Path $env:LOCALAPPDATA "Microsoft\WinGet\Packages"
$cloudflared = Get-ChildItem -Path $packagesPath -Filter "cloudflared.exe" -File -Recurse -ErrorAction SilentlyContinue |
    Select-Object -First 1

if (-not $cloudflared) {
    throw "No se encontró cloudflared. Instálalo con: winget install --id Cloudflare.cloudflared -e"
}

$python = Get-Command python -ErrorAction Stop
$server = Start-Process -FilePath $python.Source -ArgumentList @("run_demo.py") `
    -WorkingDirectory $projectRoot -PassThru -WindowStyle Hidden

try {
    $ready = $false
    for ($attempt = 0; $attempt -lt 30; $attempt++) {
        $server.Refresh()
        if ($server.HasExited) {
            throw "El servidor de Eco Menu se cerró antes de iniciar."
        }

        try {
            $response = Invoke-WebRequest -Uri "http://127.0.0.1:5002/login" -UseBasicParsing -TimeoutSec 2
            if ($response.StatusCode -eq 200) {
                $ready = $true
                break
            }
        }
        catch {
            Start-Sleep -Seconds 1
        }
    }

    if (-not $ready) {
        throw "Eco Menu no respondió en el puerto 5002."
    }

    Write-Host "Eco Menu está activo. Usa la URL que mostrará Cloudflare para crear el QR."
    & $cloudflared.FullName tunnel --protocol http2 --url "http://127.0.0.1:5002"
}
finally {
    $server.Refresh()
    if (-not $server.HasExited) {
        Stop-Process -Id $server.Id -ErrorAction SilentlyContinue
    }
}
