# Input and output contract

## Minimum viable input

Provide:

1. A dashboard specification in Markdown.
2. Raw data or a representative, anonymized sample.
3. A data dictionary or enough examples to derive one safely.
4. Measure names and business definitions.
5. Required pages and visual field mappings.
6. The requested final format: source artifacts, PBIP, PBIX, or publication.

For report generation, place the reusable Power BI project template under `<input-root>/template/`. Use a complete PBIP project such as `template/template.pbip`, `template/template.Report/`, and `template/template.SemanticModel/`. The supported project pointer extension is `.pbip`, not `.pbib`.

If no existing PBIP template is available, the skill can still produce data, M, DAX, TMDL, theme, and layout artifacts. It must not promise a fully rendered PBIX without Power BI Desktop validation.

## Recommended dashboard specification

Use this template:

```markdown
# Dashboard request

## Goal and audience
- Business question:
- Intended users:
- Refresh frequency:
- Locale/time zone:

## Inputs
- Raw-data path(s):
- File format and sheet/table names:
- Existing PBIP/PBIX/template path:
- Date coverage:

## Data dictionary
| Table | Column | Type | Meaning | Key | Format | Sensitive |
|---|---|---|---|---|---|---|

## Model relationships
| From | To | Cardinality | Filter direction | Active |
|---|---|---|---|---|

## Measures
| Name | Business definition | DAX or pseudocode | Format | Validation example |
|---|---|---|---|---|

## Pages
### Page name
- Purpose:
- Page filters:
- Slicers:
- Visual:
  - Type:
  - Title:
  - X-axis:
  - Y-axis:
  - Legend:
  - Details:
  - Size:
  - Sort:
  - Tooltip:
  - Interactions:
  - Analytics/reference lines:

## Visual system
- Theme JSON or color palette:
- Font:
- Logo path:
- Canvas size:
- Number-format rules:

## Security and deployment
- RLS requirements:
- Target workspace:
- Overwrite allowed:
- Refresh/gateway requirements:

## Acceptance criteria
- Expected KPI examples:
- Required output files:
- Desktop validation required:
- Publication required:
```

## Raw-data expectations

- Prefer stable, descriptive filenames and include a representative period.
- State whether periodic files must be appended or compared.
- Identify the expected grain and natural/business keys.
- Provide expected totals for at least one small slice when possible.
- Use anonymized samples when production access is unnecessary.
- Supply credentials through an approved secret mechanism, never Markdown.

## Visual assets

Provide approved colors, fonts, logos, icons, theme JSON, screenshots, or wireframes. State whether each asset is mandatory or illustrative and confirm usage rights.

## Defaults when unspecified

- Use the supplied locale; otherwise preserve source culture and flag ambiguity.
- Prefer a star schema and single-direction dimension-to-fact filters.
- Use explicit measures instead of implicit aggregations.
- Use `DIVIDE` for ratios and return `BLANK()` for invalid denominators unless the specification requires zero.
- Preserve numeric values and apply percentage formatting rather than multiplying solely for display.
- Prefer PBIP/TMDL/PBIR source artifacts for automation.
- Do not publish, overwrite, refresh production data, or configure credentials without explicit authorization.

## Output contract

For `full` and `report-only` modes, resolve the PBIP source from an explicitly supplied path or `<input-root>/template/`, then generate the complete report project under `<output-root>/report/`. A PBIP deliverable consists of sibling `<report-name>.pbip`, `<report-name>.Report/`, and `<report-name>.SemanticModel/` artifacts. Place an optional Desktop-generated `<report-name>.pbix` in the same directory. Preserve the source template by copying the complete project to the output directory before editing unless the user explicitly requests an in-place update.

The build manifest must identify:

- input paths and fingerprints or modification timestamps;
- processing scripts and parameters;
- generated files;
- source-to-output lineage;
- assumptions and warnings;
- validation status by layer;
- whether Desktop validation and PBIX save occurred.

For `full` and `report-only` modes, generate `output/documentation/visual_requirements.json` from the dashboard specification. It must enumerate required TMDL measures, TMDL relationships, and every visual's stable ID, type, internal PBIR role, table, field or measure, and binding kind. Use it as the machine-readable acceptance baseline; the Markdown specification remains the business source of truth.

The validation report must separate `passed`, `failed`, `not run`, and `blocked` checks. It must verify template selection and integrity, source-template preservation, the report output directory, sibling PBIP component presence, common naming, relative references, required definition files, requested measures and relationships persisted in TMDL, requested field mappings persisted in PBIR semantic queries/queryState, and PBIX save status. A generated preview or unbound visual container is not evidence that the report is complete.

## Invocation examples

Explicit invocation:

```text
Use $generate-powerbi-dashboard with dashboard_spec.md, rawdata/, and visual_assets/.
Generate processed assets, Power Query M, batch DAX measures, a theme, a page-layout specification, and an editable PBIP project under output/. Validate everything available locally; do not publish.
```

Modify an existing project:

```text
Use $generate-powerbi-dashboard to update report/Sales.pbip from requirements/dashboard_update.md. Preserve unrelated pages, add the requested measures and visuals, and produce a validation report. Do not create or overwrite a PBIX.
```

Artifact-only debugging:

```text
Use $generate-powerbi-dashboard to diagnose why dashboard_base/data_measures.dax and power_query_import.m do not match the current raw-data schema. Report the cause and proposed changes; do not edit files.
```
