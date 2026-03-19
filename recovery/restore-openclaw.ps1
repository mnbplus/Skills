param(
  [string]$StateDir = "$HOME\.openclaw-restored",
  [switch]$Force
)

$ErrorActionPreference = "Stop"

function Replace-Placeholder {
  param(
    [Parameter(Mandatory = $true)]$Value,
    [Parameter(Mandatory = $true)][string]$StateDir
  )

  if ($Value -is [string]) {
    return $Value.Replace('${STATE_DIR}', $StateDir)
  }

  if ($Value -is [System.Collections.IEnumerable] -and $Value -isnot [string]) {
    $items = @()
    foreach ($item in $Value) {
      $items += ,(Replace-Placeholder -Value $item -StateDir $StateDir)
    }
    return $items
  }

  if ($Value -is [pscustomobject] -or $Value -is [hashtable]) {
    $result = [ordered]@{}
    foreach ($prop in $Value.PSObject.Properties) {
      $result[$prop.Name] = Replace-Placeholder -Value $prop.Value -StateDir $StateDir
    }
    return [pscustomobject]$result
  }

  return $Value
}

$RepoRoot = Split-Path -Parent $PSScriptRoot
$RecoveryFile = Join-Path $PSScriptRoot 'openclaw.recovery.json'
$Recovery = Get-Content $RecoveryFile -Raw | ConvertFrom-Json -Depth 100

$ResolvedStateDir = [System.IO.Path]::GetFullPath($StateDir)

foreach ($dirTemplate in $Recovery.requiredDirectories) {
  $dir = $dirTemplate.Replace('${STATE_DIR}', $ResolvedStateDir)
  New-Item -ItemType Directory -Force -Path $dir | Out-Null
}

$ConfigObject = Replace-Placeholder -Value $Recovery.config -StateDir $ResolvedStateDir
$ConfigPath = Join-Path $ResolvedStateDir 'openclaw.json'

if ((Test-Path $ConfigPath) -and -not $Force) {
  throw "Config already exists at $ConfigPath. Re-run with -Force to overwrite."
}

$ConfigObject | ConvertTo-Json -Depth 100 | Set-Content -Path $ConfigPath -Encoding UTF8

$SecretsPath = Join-Path $ResolvedStateDir 'openclaw.secrets.required.txt'
$Recovery.requiredSecrets | Set-Content -Path $SecretsPath -Encoding UTF8

Write-Output "Restored skeleton config to: $ConfigPath"
Write-Output "Secret placeholders listed in: $SecretsPath"
Write-Output "Fill the redacted secrets before starting OpenClaw."
