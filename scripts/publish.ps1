param(
  [string]$Message,
  [ValidateSet("auto", "daily", "all")]
  [string]$Scope = "auto"
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

function Get-DailyPublishTargets {
  $dates = [System.Collections.Generic.HashSet[string]]::new()
  $collectDate = {
    param([string]$PathValue)
    if (-not $PathValue) {
      return
    }

    $path = $PathValue.Trim()
    if ($path.StartsWith('"') -and $path.EndsWith('"')) {
      $path = $path.Substring(1, $path.Length - 2)
    }
    $path = $path -replace '\\', '/'

    if ($path -match '^content/(\d{4}-\d{2}-\d{2})\.json$') {
      $null = $dates.Add($matches[1])
      return
    }
    if ($path -match '^docs/(\d{4}-\d{2}-\d{2})\.html$') {
      $null = $dates.Add($matches[1])
      return
    }
    if ($path -match '^docs/(\d{4}-\d{2}-\d{2})/index\.html$') {
      $null = $dates.Add($matches[1])
      return
    }
  }

  $statusLines = (& git status --porcelain=v1 --untracked-files=all -- content docs 2>$null)
  if ($LASTEXITCODE -eq 0) {
    foreach ($line in $statusLines) {
      if (-not $line -or $line.Length -lt 4) {
        continue
      }
      & $collectDate $line.Substring(3)
    }
  }

  $aheadLines = (& git diff --name-only origin/main..HEAD -- content docs 2>$null)
  if ($LASTEXITCODE -eq 0) {
    foreach ($path in $aheadLines) {
      & $collectDate $path
    }
  }

  if ($dates.Count -eq 0) {
    return @()
  }

  $targets = @()
  foreach ($date in ($dates | Sort-Object)) {
    $targets += "content/$date.json"
    $targets += "docs/$date.html"
    $targets += "docs/$date/index.html"
  }

  $targets += "docs/index.html"
  $targets += "docs/latest.html"
  $targets += "docs/latest/index.html"
  $targets += "docs/.nojekyll"
  return $targets
}

python .\scripts\build_site.py

if (-not $Message) {
  $today = Get-Date -Format "yyyy-MM-dd"
  $Message = "Publish daily news for $today"
}

$dailyTargets = Get-DailyPublishTargets
$effectiveScope = $Scope
if ($effectiveScope -eq "auto") {
  $effectiveScope = if ($dailyTargets.Count -gt 0) { "daily" } else { "all" }
}

$gitDir = (& git rev-parse --git-dir 2>$null)
if ($LASTEXITCODE -eq 0 -and $gitDir -match "[/\\]\.git[/\\]worktrees[/\\]") {
  python .\scripts\publish_via_github_api.py --message $Message --scope $effectiveScope
  exit $LASTEXITCODE
}

try {
  if ($effectiveScope -eq "daily") {
    if ($dailyTargets.Count -eq 0) {
      Write-Host "No daily edition changes to commit."
      exit 0
    }
    Invoke-GitWithRetry -GitArgs (@("add", "--") + $dailyTargets)
  } else {
    Invoke-GitWithRetry -GitArgs @("add", "README.md", "content", "docs", "prompts", "scripts", "site", ".gitattributes", ".gitignore")
  }
} catch {
  $text = ($_ | Out-String)
  if ($text -match 'index\.lock' -or $text -match 'Permission denied' -or $text -match 'Unable to create') {
    python .\scripts\publish_via_github_api.py --message $Message --scope $effectiveScope
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
