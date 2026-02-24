#!/usr/bin/env powershell
# Start ClawChat Server

cd C:\Users\hippa\src\clawChat\udp_hole_punching

$env:CLAWCHAT_BOOTSTRAP_KEY = "default-key-32bytes-for-testing!"

# Create directory
New-Item -ItemType Directory -Force -Path C:\temp\clawchat\security | Out-Null

# Remove old security files
Remove-Item C:\temp\clawchat\security\*.sec -ErrorAction SilentlyContinue

Write-Host "Starting server..."
Write-Host "Bootstrap key: $env:CLAWCHAT_BOOTSTRAP_KEY"
Write-Host ""

python run_server.py --ip 127.0.0.1 --port 55555
