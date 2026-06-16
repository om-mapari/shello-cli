# run_shello_with_proxy.ps1
# Set up mitmproxy settings and execute Shello CLI.

# 1. Start mitmweb in the background if it's not already running
$mitmwebProcess = Get-Process -Name mitmweb -ErrorAction SilentlyContinue
if (-not $mitmwebProcess) {
    Write-Host "🚀 Starting mitmweb (Web-based Proxy GUI)..." -ForegroundColor Cyan
    # Start mitmweb minimized
    Start-Process -FilePath "mitmweb" -WindowStyle Minimized
    # Wait for mitmweb to bind to ports
    Start-Sleep -Seconds 2
} else {
    Write-Host "✅ mitmweb is already running." -ForegroundColor Green
}

Write-Host "🌐 mitmweb UI is available at: http://127.0.0.1:8123" -ForegroundColor Green

# 2. Configure Environment Variables for Python/HTTP proxy
$env:HTTP_PROXY = "http://127.0.0.1:8080"
$env:HTTPS_PROXY = "http://127.0.0.1:8080"

# 3. Path to mitmproxy CA Certificate
$caCertPath = "$env:USERPROFILE\.mitmproxy\mitmproxy-ca-cert.pem"
if (Test-Path $caCertPath) {
    $env:REQUESTS_CA_BUNDLE = $caCertPath
    $env:SSL_CERT_FILE = $caCertPath
    Write-Host "🔒 Certificate configured correctly for SSL interception." -ForegroundColor Green
} else {
    Write-Warning "⚠️ mitmproxy CA certificate not found at $caCertPath."
    Write-Warning "You might get SSL errors. Run 'mitmweb' once to generate it."
}

# 4. Run Shello CLI
Write-Host "▶ Running Shello CLI with proxy configuration..." -ForegroundColor Yellow
if ($args.Count -eq 0) {
    # Default to chat subcommand if no args passed
    & .venv\Scripts\shello chat
} else {
    & .venv\Scripts\shello $args
}
