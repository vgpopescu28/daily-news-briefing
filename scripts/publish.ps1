param(
  [string]$Message
)

$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")

function Invoke-GitWithRetry {
  param(
    [string[]]$GitArgs,
    [int]$MaxAttempts = 5
  )

  for ($attempt = 1; $attempt -le $MaxAttempts; $attempt++) {
    $output = & git @GitArgs 2>&1
    if ($LASTEXITCODE -eq 0) {
      return $output
    }

    $text = ($output | Out-String)
    $isLockError = $text -match 'index\.lock' -or $text -match 'Permission denied' -or $text -match 'Unable to create'
    if (-not $isLockError -or $attempt -eq $MaxAttempts) {
      throw $text
    }

    Start-Sleep -Seconds ([Math]::Min($attempt * 2, 8))
  }
}

function Get-DefaultBranch {
  $remoteHead = (& git symbolic-ref --quiet --short refs/remotes/origin/HEAD 2>$null)
  if ($LASTEXITCODE -eq 0 -and $remoteHead) {
    return ($remoteHead -replace '^origin/', '')
  }

  $current = (& git branch --show-current 2>$null)
  if ($LASTEXITCODE -eq 0 -and $current) {
    return $current.Trim()
  }

  return "main"
}

python .\scripts\build_site.py

if (-not $Message) {
  $today = Get-Date -Format "yyyy-MM-dd"
  $Message = "Publish daily news for $today"
}

$gitDir = (& git rev-parse --git-dir 2>$null)
if ($LASTEXITCODE -eq 0 -and $gitDir -match "[/\\]\.git[/\\]worktrees[/\\]") {
  python .\scripts\publish_via_github_api.py --message $Message
  exit $LASTEXITCODE
}

try {
  Invoke-GitWithRetry -GitArgs @("add", "README.md", "content", "docs", "prompts", "scripts", "site", ".gitattributes", ".gitignore")
} catch {
  $text = ($_ | Out-String)
  if ($text -match 'index\.lock' -or $text -match 'Permission denied' -or $text -match 'Unable to create') {
    python .\scripts\publish_via_github_api.py --message $Message
    exit $LASTEXITCODE
  }
  throw
}

git diff --cached --quiet
if ($LASTEXITCODE -eq 0) {
  Write-Host "No changes to commit."
  exit 0
}

Invoke-GitWithRetry -GitArgs @("commit", "-m", $Message)

$currentBranch = (& git branch --show-current 2>$null)
if ($LASTEXITCODE -eq 0 -and $currentBranch) {
  Invoke-GitWithRetry -GitArgs @("push")
} else {
  $targetBranch = Get-DefaultBranch
  Invoke-GitWithRetry -GitArgs @("push", "origin", "HEAD:refs/heads/$targetBranch")
}
