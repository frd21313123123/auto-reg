Param(
    [string]$BackendHost = "0.0.0.0",
    [int]$BackendPort = 8000,
    [int]$FrontendPort = 5173
)

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$backendDir = Join-Path $root "backend"
$frontendDir = Join-Path $root "frontend"

Write-Host "Starting backend on http://$BackendHost`:$BackendPort"
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$backendDir'; uvicorn app.main:app --reload --host $BackendHost --port $BackendPort"

Write-Host "Starting frontend on http://localhost:$FrontendPort"
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$frontendDir'; npm run dev -- --port $FrontendPort"

Write-Host "Both services were started in separate windows."
