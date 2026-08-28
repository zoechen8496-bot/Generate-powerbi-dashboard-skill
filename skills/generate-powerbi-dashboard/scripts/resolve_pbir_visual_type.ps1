param(
    [Parameter(Mandatory=$true)]
    [string]$RequestedType,
    [string]$SchemaVersion = '2.11.0',
    [string]$AssetRoot
)

$ErrorActionPreference = 'Stop'
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
if (-not $AssetRoot) { $AssetRoot = Join-Path $ScriptDir '..\assets\pbir' }

function Normalize-Name([string]$Value) {
    return (($Value -replace '[^A-Za-z0-9]', '').ToLowerInvariant())
}

$registryPath = Join-Path $AssetRoot "visual-container-$SchemaVersion\registry.json"
if (-not (Test-Path -LiteralPath $registryPath)) {
    throw "PBIR registry not found for visualContainer schema $SchemaVersion`: $registryPath"
}

$registry = Get-Content -Raw -LiteralPath $registryPath | ConvertFrom-Json
$needle = Normalize-Name $RequestedType
$matches = @()
foreach ($entry in $registry.visualTypes) {
    $names = @($entry.visualType, $entry.sampleName) + @($entry.aliases)
    if (@($names | Where-Object { (Normalize-Name $_) -eq $needle }).Count -gt 0) {
        $matches += $entry
    }
}

if ($matches.Count -eq 0) {
    $supported = @($registry.visualTypes | ForEach-Object visualType | Sort-Object) -join ', '
    throw "No Desktop-authored PBIR mapping for '$RequestedType' under schema $SchemaVersion. Supported visualTypes: $supported"
}
if ($matches.Count -gt 1) {
    throw "Ambiguous PBIR visual type alias '$RequestedType': $(@($matches | ForEach-Object visualType) -join ', ')"
}

$matches[0].visualType
