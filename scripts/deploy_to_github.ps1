# Deploy to GitHub - PowerShell Script

Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "   Porter Analytics Agent - GitHub Deployment Helper" -ForegroundColor Cyan
Write-Host "========================================================"
Write-Host ""

# Check if git is installed
if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    Write-Error "Git is not installed. Please install Git."
    Pause
    exit 1
}

# Check if gh cli is installed
if (-not (Get-Command gh -ErrorAction SilentlyContinue)) {
    Write-Error "GitHub CLI (gh) is not installed."
    Write-Host "Please install it from https://cli.github.com/"
    Pause
    exit 1
}

# Check GitHub authentication
Write-Host "Checking GitHub authentication..."
gh auth status 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "Please login to GitHub..."
    gh auth login -w -p https
}

Write-Host ""
Write-Host "[1/3] Creating private repository..." -ForegroundColor Yellow
$repoName = Read-Host "Enter a name for your repository (e.g., porter-analytics)"

if (-not (Test-Path ".git")) {
    git init
    git branch -M main
}

# Create repo
gh repo create $repoName --private --source=. --remote=origin --push

Write-Host ""
Write-Host "[2/3] Configuring Secrets..." -ForegroundColor Yellow

if (-not (Test-Path "config\.env")) {
    Write-Error "config\.env file not found!"
    Pause
    exit 1
}

# Read .env file and set secrets
$envContent = Get-Content "config\.env"
foreach ($line in $envContent) {
    if ($line -match "^[^#]*=.*") {
        $parts = $line -split "=", 2
        $key = $parts[0].Trim()
        $val = $parts[1].Trim()
        
        if (-not [string]::IsNullOrWhiteSpace($key)) {
            Write-Host "Setting secret: $key"
            $val | gh secret set $key --repo $repoName
        }
    }
}

Write-Host "Setting OAuth2 secrets..."
if (Test-Path "credentials.json") {
    Write-Host "Setting secret: GOP_CREDENTIALS_JSON"
    Get-Content "credentials.json" | gh secret set GOP_CREDENTIALS_JSON --repo $repoName
}
else {
    Write-Warning "credentials.json not found!"
}

if (Test-Path "token.json") {
    Write-Host "Setting secret: GOP_TOKEN_JSON"
    Get-Content "token.json" | gh secret set GOP_TOKEN_JSON --repo $repoName
}
else {
    Write-Warning "token.json not found! Automation might fail."
}

Write-Host ""
Write-Host "[3/3] Verifying Deployment..." -ForegroundColor Yellow
Write-Host "Triggering initial workflow run..."
gh workflow run daily_analysis.yml --repo $repoName

Write-Host ""
Write-Host "========================================================" -ForegroundColor Green
Write-Host "   Deployment Complete! 🚀" -ForegroundColor Green
Write-Host "========================================================"
Write-Host ""
Write-Host "Check status here: https://github.com/$env:USERNAME/$repoName/actions"
Pause
