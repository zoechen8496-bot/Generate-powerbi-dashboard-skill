param(
    [Parameter(Mandatory=$true)]
    [string]$ReportRoot,
    [string]$AssetRoot,
    [string]$ResultPath,
    [switch]$AllowUnknownVisualType
)

$ErrorActionPreference = 'Stop'
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
if (-not $AssetRoot) { $AssetRoot = Join-Path $ScriptDir '..\assets\pbir' }
$issues = New-Object System.Collections.Generic.List[object]
$checked = 0

function Add-Issue([string]$Severity,[string]$Code,[string]$Path,[string]$Message) {
    $script:issues.Add([pscustomobject]@{ severity=$Severity; code=$Code; path=$Path; message=$Message })
}

function Get-SchemaVersion([string]$SchemaUri) {
    if ($SchemaUri -match '/visualContainer/([^/]+)/schema\.json$') { return $Matches[1] }
    return $null
}

$resolvedRoot = (Resolve-Path -LiteralPath $ReportRoot).Path
$visualFiles = Get-ChildItem -LiteralPath $resolvedRoot -Recurse -Filter 'visual.json' -File
$registryCache = @{}

foreach ($file in $visualFiles) {
    $checked++
    $relativePath = $file.FullName.Substring($resolvedRoot.Length).TrimStart('\')
    $bytes = [System.IO.File]::ReadAllBytes($file.FullName)
    if ($bytes.Length -ge 3 -and $bytes[0] -eq 239 -and $bytes[1] -eq 187 -and $bytes[2] -eq 191) {
        Add-Issue 'error' 'PBIR_UTF8_BOM' $relativePath 'PBIR files must use UTF-8 without BOM.'
    }

    try { $doc = Get-Content -Raw -LiteralPath $file.FullName | ConvertFrom-Json }
    catch { Add-Issue 'error' 'PBIR_JSON_PARSE' $relativePath $_.Exception.Message; continue }

    $schemaVersion = Get-SchemaVersion $doc.'$schema'
    if (-not $schemaVersion) {
        Add-Issue 'error' 'PBIR_VISUAL_SCHEMA' $relativePath 'Missing or unsupported visualContainer $schema URI.'
        continue
    }
    if (-not $doc.name -or -not $doc.position -or -not $doc.visual -or -not $doc.visual.visualType) {
        Add-Issue 'error' 'PBIR_REQUIRED_PROPERTY' $relativePath 'Visual requires name, position, visual, and visual.visualType.'
        continue
    }

    $registryPath = Join-Path $AssetRoot "visual-container-$schemaVersion\registry.json"
    if (-not $registryCache.ContainsKey($schemaVersion)) {
        if (Test-Path -LiteralPath $registryPath) {
            $registryCache[$schemaVersion] = Get-Content -Raw -LiteralPath $registryPath | ConvertFrom-Json
        } else {
            $registryCache[$schemaVersion] = $null
        }
    }
    $registry = $registryCache[$schemaVersion]
    if (-not $registry) {
        Add-Issue 'error' 'PBIR_SCHEMA_ASSETS_MISSING' $relativePath "No canonical asset registry exists for visualContainer schema $schemaVersion."
    } else {
        $knownTypes = @($registry.visualTypes | ForEach-Object visualType)
        if ($knownTypes -notcontains $doc.visual.visualType) {
            $message = if ($doc.visual.visualType -eq 'stackedBarChart') {
                'Use barChart for the built-in stacked bar chart. stackedBarChart is interpreted as a missing custom visual.'
            } else {
                "visualType '$($doc.visual.visualType)' is not backed by a Desktop-authored sample for schema $schemaVersion."
            }
            if ($AllowUnknownVisualType) { Add-Issue 'warning' 'PBIR_VISUAL_TYPE_UNVERIFIED' $relativePath $message }
            else { Add-Issue 'error' 'PBIR_VISUAL_TYPE_UNVERIFIED' $relativePath $message }
        }
    }

    $containerObjects = $doc.visual.visualContainerObjects
    if ($containerObjects -and $containerObjects.PSObject.Properties.Name -contains 'referenceLine') {
        Add-Issue 'error' 'PBIR_ANALYTICS_WRONG_SCOPE' $relativePath 'referenceLine is not allowed at /visual/visualContainerObjects; use the Desktop-authored visual.objects feature.'
    }

    $referenceLines = $doc.visual.objects.y1AxisReferenceLine
    if ($referenceLines) {
        $featurePath = Join-Path $AssetRoot "visual-container-$schemaVersion\features\$($doc.visual.visualType).y1AxisReferenceLine.json"
        if (-not (Test-Path -LiteralPath $featurePath)) {
            Add-Issue 'error' 'PBIR_ANALYTICS_SAMPLE_MISSING' $relativePath "No y1AxisReferenceLine sample exists for visualType '$($doc.visual.visualType)' and schema $schemaVersion."
        }
        foreach ($line in @($referenceLines)) {
            $show = $line.properties.show.expr.Literal.Value
            $value = $line.properties.value.expr.Literal.Value
            if ($show -ne 'true') { Add-Issue 'error' 'PBIR_ANALYTICS_SHOW' $relativePath 'Reference line requires show=true.' }
            if ($value -notmatch '^-?[0-9]+(?:\.[0-9]+)?D$') { Add-Issue 'error' 'PBIR_ANALYTICS_VALUE' $relativePath "Invalid constant-line literal: $value" }
            if (-not $line.properties.displayName.expr.Literal.Value -or -not $line.selector.id) {
                Add-Issue 'error' 'PBIR_ANALYTICS_IDENTITY' $relativePath 'Reference line requires displayName and selector.id.'
            }
        }
    }
}

$issueArray = $issues.ToArray()
$errorCount = @($issueArray | Where-Object severity -eq 'error').Count
$warningCount = @($issueArray | Where-Object severity -eq 'warning').Count
$result = [ordered]@{
    reportRoot = $resolvedRoot
    checkedVisualFiles = $checked
    errors = $errorCount
    warnings = $warningCount
    status = if ($errorCount -eq 0) { 'Passed' } else { 'Failed' }
    issues = $issueArray
}

if ($ResultPath) {
    $parent = Split-Path -Parent $ResultPath
    if ($parent) { New-Item -ItemType Directory -Path $parent -Force | Out-Null }
    $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
    [System.IO.File]::WriteAllText($ResultPath, ($result | ConvertTo-Json -Depth 20), $utf8NoBom)
}

$result | ConvertTo-Json -Depth 20
if ($errorCount -gt 0) { exit 1 }
exit 0
