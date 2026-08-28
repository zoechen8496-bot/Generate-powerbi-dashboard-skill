param(
    [Parameter(Mandatory=$true)]
    [string]$VisualPath,
    [ValidateSet('y1AxisReferenceLine')]
    [string]$Feature = 'y1AxisReferenceLine',
    [double]$Value = 100,
    [string]$DisplayName = 'Y-Axis Constant Line 1',
    [string]$AssetRoot
)

$ErrorActionPreference = 'Stop'
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
if (-not $AssetRoot) { $AssetRoot = Join-Path $ScriptDir '..\assets\pbir' }
$Utf8NoBom = New-Object System.Text.UTF8Encoding($false)
$resolvedPath = (Resolve-Path -LiteralPath $VisualPath).Path
$doc = Get-Content -Raw -LiteralPath $resolvedPath | ConvertFrom-Json

if ($doc.'$schema' -notmatch '/visualContainer/([^/]+)/schema\.json$') {
    throw "Unsupported or missing visualContainer schema in $resolvedPath"
}
$schemaVersion = $Matches[1]
$visualType = $doc.visual.visualType
if (-not $visualType) { throw "Missing visual.visualType in $resolvedPath" }

$featurePath = Join-Path $AssetRoot "visual-container-$schemaVersion\features\$visualType.$Feature.json"
if (-not (Test-Path -LiteralPath $featurePath)) {
    throw "No Desktop-authored $Feature asset for visualType '$visualType' and schema $schemaVersion."
}
$featureDoc = Get-Content -Raw -LiteralPath $featurePath | ConvertFrom-Json
$featureValue = $featureDoc.objects.$Feature

if ($Feature -eq 'y1AxisReferenceLine') {
    $literal = $Value.ToString('0.################', [Globalization.CultureInfo]::InvariantCulture) + 'D'
    foreach ($line in @($featureValue)) {
        $line.properties.value.expr.Literal.Value = $literal
        $line.properties.displayName.expr.Literal.Value = "'$DisplayName'"
    }
}

if (-not $doc.visual.objects) {
    $doc.visual | Add-Member -NotePropertyName objects -NotePropertyValue ([pscustomobject]@{})
}
$doc.visual.objects | Add-Member -NotePropertyName $Feature -NotePropertyValue @($featureValue) -Force
[System.IO.File]::WriteAllText($resolvedPath, ($doc | ConvertTo-Json -Depth 50), $Utf8NoBom)
