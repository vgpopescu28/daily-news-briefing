param(
  [string]$Message
)

$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")

python .\scripts\build_site.py

git add README.md content docs prompts scripts site .gitignore

git diff --cached --quiet
if ($LASTEXITCODE -eq 0) {
  Write-Host "No changes to commit."
  exit 0
}

if (-not $Message) {
  $today = Get-Date -Format "yyyy-MM-dd"
  $Message = "Publish daily news for $today"
}

git commit -m $Message
git push
