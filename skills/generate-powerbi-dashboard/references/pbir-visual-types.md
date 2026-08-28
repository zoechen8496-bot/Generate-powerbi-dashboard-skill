# PBIR visual types and canonical features

Use this reference when generating, modifying, or diagnosing PBIR `visual.json` files. The mappings below are normalized from Power BI Desktop-authored samples using the visual-container `2.11.0` schema.

## Built-in visualType mappings

| Requested visual | PBIR `visualType` | Canonical asset |
|---|---|---|
| Area chart | `areaChart` | `visual-types/areaChart.visual.json` |
| Stacked area chart | `stackedAreaChart` | `visual-types/stackedAreaChart.visual.json` |
| Stacked bar chart | `barChart` | `visual-types/barChart.visual.json` |
| Clustered bar chart | `clusteredBarChart` | `visual-types/clusteredBarChart.visual.json` |
| 100% stacked bar chart | `hundredPercentStackedBarChart` | `visual-types/hundredPercentStackedBarChart.visual.json` |
| Stacked column chart | `columnChart` | `visual-types/columnChart.visual.json` |
| Clustered column chart | `clusteredColumnChart` | `visual-types/clusteredColumnChart.visual.json` |
| 100% stacked column chart | `hundredPercentStackedColumnChart` | `visual-types/hundredPercentStackedColumnChart.visual.json` |
| Card | `cardVisual` | `visual-types/cardVisual.visual.json` |
| Line chart | `lineChart` | `visual-types/lineChart.visual.json` |
| Scatter chart | `scatterChart` | `visual-types/scatterChart.visual.json` |
| Slicer | `slicer` | `visual-types/slicer.visual.json` |
| Table | `tableEx` | `visual-types/tableEx.visual.json` |

Resolve aliases with `scripts/resolve_pbir_visual_type.ps1`. Do not derive a `visualType` from the English display name. In particular, never use `stackedBarChart`: Power BI interprets it as an unavailable custom visual and raises `CustomVisualNotFound`; use `barChart`.

The registry and assets for this schema live under `assets/pbir/visual-container-2.11.0/`. Treat types absent from that registry as unverified, even when they may exist in another Desktop or schema version. Capture a Desktop-authored sample before generating an unregistered type.

## Normalized feature boundary

Canonical visual-type assets preserve only:

- the declared visual-container schema;
- the Desktop-authored `visual.visualType`;
- the default `drillFilterOtherVisuals` behavior.

They intentionally remove visual IDs, page positions, query bindings, business titles, filters, interactions, and machine-specific paths. Generate those project-specific properties from the dashboard request and semantic model.

The source visual-container samples do not establish field-role schemas for most visual types because they contain unbound visuals. Use an existing bound template visual or a separate Desktop-authored bound sample before inventing query roles.

## Bound role/query templates

Read [pbir-binding-assets.md](pbir-binding-assets.md) before generating query bindings. The schema 2.11.0 registry records `bindingStatus`, `bindingAsset`, `boundRoles`, and `bindingSourceCount` for every visual type. A type with `bindingStatus: unavailable` may be structurally generated only as an explicitly incomplete placeholder; it cannot satisfy a data-bound report requirement.

Binding assets preserve normalized Desktop-authored projection and formatting structures with placeholders. Substitute the dashboard request's table, field, measure, aggregation, query reference, display label, title, and sort values; then validate the resulting `visual.json`. Do not place the binding-template document itself in a Report folder.

## Analytics features

Desktop-authored line and scatter samples place Y-axis constant lines at:

```text
visual.objects.y1AxisReferenceLine
```

The feature requires `show`, `displayName`, `value`, and `selector.id`. A numeric constant uses a DAX numeric literal such as `100D`. It must not be placed under `visual.visualContainerObjects`.

The line-chart before/after pair establishes the feature delta. The supplied scatter-chart before/after files are identical and already contain the feature, so use them as structural evidence only, not as a clean delta fixture.

Use these schema-specific assets:

| Visual type | Feature asset |
|---|---|
| `lineChart` | `features/lineChart.y1AxisReferenceLine.json` |
| `scatterChart` | `features/scatterChart.y1AxisReferenceLine.json` |

Apply a canonical feature with `scripts/set_pbir_visual_feature.ps1`; do not copy a complete sample visual because that can leak project-specific IDs and field bindings.

## Sample ingestion and validation

When new Desktop-authored samples are supplied, run `scripts/normalize_pbir_samples.ps1` to rebuild the schema-versioned assets. Preserve the source samples outside the skill until normalization succeeds, then inspect the generated registry diff.

Run `scripts/validate_pbir.ps1` against every generated Report folder. By default, fail on visual types absent from the matching schema registry, invalid analytics placement, missing feature samples, malformed numeric literals, JSON errors, or UTF-8 BOM files. Use `-AllowUnknownVisualType` only for diagnosis; a warning is not evidence that Power BI Desktop can load the visual.
