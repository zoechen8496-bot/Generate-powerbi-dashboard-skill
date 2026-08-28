# PBIR binding and formatting assets

Use this reference when generating `visual.query.queryState`, projections, sorting, or visual formatting.

## Asset contract

Binding templates live under `assets/pbir/visual-container-<schema>/bindings/`. Each `*.binding.json` records:

- the exact Desktop-authored PBIR schema and visual type;
- supported internal query roles;
- observed projection counts;
- projection templates for column, measure, or aggregation bindings;
- a schema-authored sort-definition template when observed;
- normalized `objects` and `visualContainerObjects` formatting;
- source provenance and SHA-256 without retaining project field names, titles, positions, filters, or saved slicer state.

Substitute every `{{...}}` placeholder before writing a deliverable `visual.json`. Never copy the binding asset itself as a visual: it is a template description, not a valid visual container.

## Available schema 2.11.0 bindings

| Visual type | Roles | Asset |
|---|---|---|
| `areaChart` | Category, Series, Y | `bindings/areaChart.binding.json` |
| `barChart` | Category, Y | `bindings/barChart.binding.json` |
| `cardVisual` | Data | `bindings/cardVisual.binding.json` |
| `clusteredBarChart` | Category, Y | `bindings/clusteredBarChart.binding.json` |
| `clusteredColumnChart` | Category, Y | `bindings/clusteredColumnChart.binding.json` |
| `columnChart` | Category, Y | `bindings/columnChart.binding.json` |
| `hundredPercentStackedBarChart` | Category, Y | `bindings/hundredPercentStackedBarChart.binding.json` |
| `hundredPercentStackedColumnChart` | Category, Y | `bindings/hundredPercentStackedColumnChart.binding.json` |
| `lineChart` | Category, Series, Y | `bindings/lineChart.binding.json` |
| `scatterChart` | Series, Size, X, Y | `bindings/scatterChart.binding.json` |
| `slicer` | Values | `bindings/slicer.binding.json` |
| `stackedAreaChart` | Category, Series, Y | `bindings/stackedAreaChart.binding.json` |
| `tableEx` | Values | `bindings/tableEx.binding.json` |

Treat any future registered visual type not listed here as binding-unavailable until a Desktop-authored bound sample is supplied.

## Regenerate

Run:

```powershell
python scripts/normalize_pbir_binding_samples.py `
  --report-root <Desktop-authored.Report> `
  --asset-root assets/pbir `
  --registry assets/pbir/visual-container-2.11.0/registry.json `
  --result assets/pbir/visual-container-2.11.0/bindings/extraction-result.json
```

Inspect the registry diff and generated assets. Confirm all business table names, fields, titles, filters, saved selections, visual IDs, and positions were removed. Run the contract validator against a generated report; normalization alone does not prove that placeholder substitution is correct.
