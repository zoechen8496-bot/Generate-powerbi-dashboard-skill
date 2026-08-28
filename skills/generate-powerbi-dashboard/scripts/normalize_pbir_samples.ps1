param(
    [Parameter(Mandatory=$true)]
    [string]$PbirSamplesRoot,
    [Parameter(Mandatory=$true)]
    [string]$AnalyticsSamplesRoot,
    [string]$OutputRoot
)

$ErrorActionPreference = 'Stop'
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
if (-not $OutputRoot) { $OutputRoot = Join-Path $ScriptDir '..\assets\pbir' }
$Utf8NoBom = New-Object System.Text.UTF8Encoding($false)

function Write-JsonNoBom([string]$Path, $Value) {
    $parent = Split-Path -Parent $Path
    New-Item -ItemType Directory -Path $parent -Force | Out-Null
    [System.IO.File]::WriteAllText($Path, ($Value | ConvertTo-Json -Depth 50), $Utf8NoBom)
}

function Get-SchemaVersion([string]$SchemaUri) {
    if ($SchemaUri -match '/visualContainer/([^/]+)/schema\.json$') { return $Matches[1] }
    throw "Unsupported visual-container schema URI: $SchemaUri"
}

$pbirRoot = (Resolve-Path -LiteralPath $PbirSamplesRoot).Path
$analyticsRoot = (Resolve-Path -LiteralPath $AnalyticsSamplesRoot).Path
$registryByType = [ordered]@{}
$featureEntries = New-Object System.Collections.Generic.List[object]

foreach ($file in Get-ChildItem -LiteralPath $pbirRoot -Recurse -Filter 'visual.json' -File | Sort-Object FullName) {
    $doc = Get-Content -Raw -LiteralPath $file.FullName | ConvertFrom-Json
    $visualType = $doc.visual.visualType
    if (-not $visualType) { throw "Sample has no visual.visualType: $($file.FullName)" }
    $schemaVersion = Get-SchemaVersion $doc.'$schema'
    $sampleName = $file.Directory.Name
    $versionRoot = Join-Path $OutputRoot "visual-container-$schemaVersion"
    $assetRelative = "visual-types/$visualType.visual.json"
    $canonical = [ordered]@{
        '$schema' = $doc.'$schema'
        visual = [ordered]@{
            visualType = $visualType
            drillFilterOtherVisuals = if ($null -eq $doc.visual.drillFilterOtherVisuals) { $true } else { [bool]$doc.visual.drillFilterOtherVisuals }
        }
    }
    Write-JsonNoBom (Join-Path $versionRoot $assetRelative) $canonical
    $registryByType[$visualType] = [ordered]@{
        visualType = $visualType
        sampleName = $sampleName
        aliases = @(@($sampleName, $visualType) | Sort-Object -Unique)
        asset = $assetRelative
    }
}

foreach ($kindDir in Get-ChildItem -LiteralPath $analyticsRoot -Directory | Sort-Object Name) {
    $afterPath = Join-Path $kindDir.FullName 'after.visual.json'
    if (-not (Test-Path -LiteralPath $afterPath)) { continue }
    $after = Get-Content -Raw -LiteralPath $afterPath | ConvertFrom-Json
    $visualType = $after.visual.visualType
    $schemaVersion = Get-SchemaVersion $after.'$schema'
    $versionRoot = Join-Path $OutputRoot "visual-container-$schemaVersion"

    if (-not $registryByType.Contains($visualType)) {
        $assetRelative = "visual-types/$visualType.visual.json"
        $canonicalVisual = [ordered]@{
            '$schema' = $after.'$schema'
            visual = [ordered]@{
                visualType = $visualType
                drillFilterOtherVisuals = if ($null -eq $after.visual.drillFilterOtherVisuals) { $true } else { [bool]$after.visual.drillFilterOtherVisuals }
            }
        }
        Write-JsonNoBom (Join-Path $versionRoot $assetRelative) $canonicalVisual
        $registryByType[$visualType] = [ordered]@{
            visualType = $visualType
            sampleName = $kindDir.Name
            aliases = @(@($kindDir.Name, $visualType) | Sort-Object -Unique)
            asset = $assetRelative
        }
    }

    $referenceLine = $after.visual.objects.y1AxisReferenceLine
    if ($referenceLine) {
        $featureRelative = "features/$visualType.y1AxisReferenceLine.json"
        $feature = [ordered]@{
            '$schema' = $after.'$schema'
            visualType = $visualType
            feature = 'y1AxisReferenceLine'
            objects = [ordered]@{ y1AxisReferenceLine = @($referenceLine) }
        }
        Write-JsonNoBom (Join-Path $versionRoot $featureRelative) $feature
        $featureEntries.Add([ordered]@{
            visualType = $visualType
            feature = 'y1AxisReferenceLine'
            asset = $featureRelative
        })
    }
}

$versions = Get-ChildItem -LiteralPath $OutputRoot -Directory -ErrorAction SilentlyContinue | Where-Object Name -like 'visual-container-*'
foreach ($versionDir in $versions) {
    $schemaVersion = $versionDir.Name.Substring('visual-container-'.Length)
    $types = @($registryByType.Values | Where-Object { Test-Path -LiteralPath (Join-Path $versionDir.FullName $_.asset) } | Sort-Object visualType)
    $features = @($featureEntries | Where-Object { Test-Path -LiteralPath (Join-Path $versionDir.FullName $_.asset) } | Sort-Object visualType,feature)
    $registry = [ordered]@{
        schemaVersion = $schemaVersion
        generatedFrom = @('Desktop-authored visual-container samples', 'Desktop-authored analytics samples')
        visualTypes = $types
        features = $features
    }
    Write-JsonNoBom (Join-Path $versionDir.FullName 'registry.json') $registry
}

[pscustomobject]@{
    outputRoot = (Resolve-Path -LiteralPath $OutputRoot).Path
    visualTypeCount = $registryByType.Count
    featureCount = $featureEntries.Count
} | ConvertTo-Json
