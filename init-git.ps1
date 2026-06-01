# SPRINT 5 PHASE 1 — Git Init + Commit (PowerShell script)
# Uso: Pega esto en PowerShell o Git Bash en el directorio del proyecto

Write-Host "🚀 SPRINT 5 PHASE 1: Git Initialization" -ForegroundColor Cyan

# Step 1: Check current directory
Write-Host "📂 Current directory:" -ForegroundColor Yellow
Get-Location

# Step 2: Initialize git
Write-Host "`n📝 Initializing Git repository..." -ForegroundColor Cyan
git init
git config user.name "Javier Méndez"
git config user.email "javier@mendezconsultoria.com"

# Step 3: Add all files
Write-Host "`n📦 Adding all files to staging..." -ForegroundColor Cyan
git add .

# Step 4: Check status
Write-Host "`n📋 Git status:" -ForegroundColor Yellow
git status

# Step 5: First commit
Write-Host "`n💾 Creating initial commit..." -ForegroundColor Cyan
git commit -m "SPRINT 4: Production deployment infrastructure — 18 files ready for Render"

# Step 6: Show commit
Write-Host "`n✅ Commit created:" -ForegroundColor Green
git log --oneline -1

# Step 7: Instructions for next steps
Write-Host "`n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
Write-Host "📌 NEXT STEPS:" -ForegroundColor Yellow
Write-Host "1. Create repository on GitHub (https://github.com/new)" -ForegroundColor White
Write-Host "2. Copy HTTPS URL from GitHub" -ForegroundColor White
Write-Host "3. Run this in terminal:" -ForegroundColor White
Write-Host "   git remote add origin [GITHUB_URL]" -ForegroundColor Gray
Write-Host "   git branch -M main" -ForegroundColor Gray
Write-Host "   git push -u origin main" -ForegroundColor Gray
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
