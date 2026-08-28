# Generate Power BI Dashboard Skill

A Codex skill for generating, modifying, and validating reproducible Power BI dashboard projects from Markdown requirements, raw data, visual assets, and Power BI project templates.

The skill produces version-controllable Power BI artifacts such as PBIP, PBIR, TMDL, DAX, Power Query M, themes, processed data assets, and validation reports. It favors text-based Power BI projects over direct manipulation of binary PBIX files.

## Features

- Profile and transform Excel, CSV, and other tabular source data
- Generate reproducible reporting assets and data documentation
- Create Power Query M, DAX measures, and TMDL semantic models
- Persist model relationships and business measures in TMDL
- Build Power BI reports from complete PBIP templates
- Generate and bind PBIR visuals using Desktop-authored structures
- Validate PBIR structure, visual types, and Analytics features
- Validate model-to-visual field and measure bindings
- Produce data dictionaries, build manifests, and validation reports
- Support `full`, `data-only`, `report-only`, and `validate-only` workflows

## Repository Structure

```text
.
|-- skills/
|   `-- generate-powerbi-dashboard/
|       |-- SKILL.md
|       |-- agents/
|       |-- assets/
|       |-- references/
|       `-- scripts/
`-- examples/
    `-- hk-retail-price-dashboard/
        |-- input/
        |-- output/
        `-- build_full.py
```

Key locations:

- `skills/generate-powerbi-dashboard/`: the skill definition and runtime resources
- `skills/generate-powerbi-dashboard/scripts/`: PBIR and model-contract validation tools
- `skills/generate-powerbi-dashboard/assets/pbir/`: normalized Power BI visual assets
- `skills/generate-powerbi-dashboard/references/`: input, visual-type, and model-binding contracts
- `examples/hk-retail-price-dashboard/`: an end-to-end retail price dashboard example

## Requirements

- Codex with skill support
- Python 3.10 or later
- Windows PowerShell
- Power BI Desktop when opening, refreshing, or saving PBIP/PBIX files is required

Static generation and validation do not require Power BI Desktop. Final DAX compilation, data refresh, rendering, and PBIX creation must still be verified in Power BI Desktop.

## Installation

Clone the repository:

```powershell
git clone <repository-url>
cd Codex-generate-powerbi-dashboard-skill
```

Install or link `skills/generate-powerbi-dashboard` in the skill directory used by your Codex environment.

## Usage

Invoke the skill from Codex with the desired execution mode and input paths. For example:

```text
Use $generate-powerbi-dashboard in full mode with:

- Dashboard specification: examples/hk-retail-price-dashboard/input/Dashboard request.md
- Raw data: examples/hk-retail-price-dashboard/input/rawdata/
- PBIP template: examples/hk-retail-price-dashboard/input/template/
- Output directory: examples/hk-retail-price-dashboard/output/

Generate the complete PBIP project and validation report. Do not publish to Power BI Service.
```

### Execution Modes

| Mode | Purpose |
|---|---|
| `full` | Process raw data and generate a complete dashboard project |
| `data-only` | Generate processed data assets and data documentation only |
| `report-only` | Generate or update a report from existing processed assets |
| `validate-only` | Validate existing inputs or outputs without modifying source artifacts |

For the complete workflow and output contract, see:

- [Skill instructions](skills/generate-powerbi-dashboard/SKILL.md)
- [Input and output contract](skills/generate-powerbi-dashboard/references/input-contract.md)
- [Model and visual binding contract](skills/generate-powerbi-dashboard/references/model-visual-contract.md)
- [PBIR visual type reference](skills/generate-powerbi-dashboard/references/pbir-visual-types.md)

## Inputs

A complete dashboard build typically requires:

1. A Markdown dashboard specification
2. Raw or prepared data in Excel, CSV, or another supported tabular format
3. A data dictionary or representative samples
4. Measure names and business definitions
5. Page, visual, and field-binding requirements
6. A complete PBIP template when generating a report

A PBIP template must contain these sibling components:

```text
Dashboard.pbip
Dashboard.Report/
Dashboard.SemanticModel/
```

The skill preserves the input template and builds the report in a separate output directory unless an in-place update is explicitly requested.

## Outputs

A full build uses the following output structure by default:

```text
output/
|-- assets/
|-- dashboard_base/
|-- documentation/
|   |-- build_manifest.md
|   |-- data_dictionary.md
|   |-- measure_list.md
|   |-- model_relationships.md
|   |-- visual_requirements.json
|   `-- validation_report.md
|-- report/
|   |-- Dashboard.pbip
|   |-- Dashboard.Report/
|   `-- Dashboard.SemanticModel/
`-- tools/
```

A `.pbix` file is considered a valid output only after Power BI Desktop successfully opens and saves it.

## Example Project

The repository includes an end-to-end Hong Kong retail price dashboard example:

```powershell
python examples\hk-retail-price-dashboard\build_full.py
```

The build script regenerates files under the example's `output/` directory. Review local changes before running it if you have modified the example outputs.

## Validation

### PBIR Structure Validation

From the repository root, run:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass `
  -File skills\generate-powerbi-dashboard\scripts\validate_pbir.ps1 `
  -ReportRoot examples\hk-retail-price-dashboard\output\report\Dashboard.Report
```

This validation checks:

- JSON syntax and required report files
- UTF-8 encoding without BOM
- Registered PBIR visual types
- Supported Analytics feature placement
- Valid numeric literals
- Schema-aware visual structure rules

### Model-to-Visual Contract Validation

```powershell
python skills\generate-powerbi-dashboard\scripts\validate_powerbi_contract.py `
  --report-root examples\hk-retail-price-dashboard\output\report\Dashboard.Report `
  --semantic-model-root examples\hk-retail-price-dashboard\output\report\Dashboard.SemanticModel `
  --requirements examples\hk-retail-price-dashboard\output\documentation\visual_requirements.json
```

This validation checks:

- Required measures persisted in TMDL
- Required model relationships
- Required report pages and visuals
- PBIR semantic queries and `queryState` projections
- Field, measure, and visual-role bindings

The bundled example currently passes both validators:

```text
PBIR validation: Passed
Visual files checked: 31
Errors: 0
Warnings: 0

Model-to-visual contract validation: Passed
Errors: 0
```

Static validation does not replace validation in Power BI Desktop.

## Design Principles

- Prefer reviewable PBIP, PBIR, and TMDL sources over binary PBIX manipulation
- Never fabricate or rename an archive to imitate a PBIX file
- Preserve raw inputs and source templates
- Do not guess internal Power BI visual types, query roles, or Analytics structures
- Use normalized Power BI Desktop-authored assets as structural evidence
- Treat unbound visual containers as incomplete placeholders
- Validate every required field and measure binding against a machine-readable manifest
- Keep publishing, credentials, gateways, and production refresh outside the default scope

## Limitations

- DAX compilation, data refresh, and final rendering require Power BI Desktop validation
- Unregistered visual types require a compatible Power BI Desktop-authored sample
- A missing bound sample can block completion of a data-bound visual
- Power BI Service publishing and gateway configuration are not performed by default
- A PBIX file cannot be produced through text-file generation alone

## Contributing

Issues and pull requests are welcome. Before submitting a change:

1. Run the PBIR structure validator.
2. Run the model-to-visual contract validator.
3. Confirm that the example build remains reproducible.
4. Do not commit credentials, sensitive data, caches, or machine-specific paths.
5. Include Power BI Desktop-authored source evidence for new visual types or binding structures.

## License

No license has been selected yet. Add a `LICENSE` file before distributing or accepting external contributions, and update this section with the chosen license.
