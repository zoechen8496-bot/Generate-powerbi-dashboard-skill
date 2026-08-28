---
name: generate-powerbi-dashboard
description: Generate, modify, and validate a Power BI dashboard project from a Markdown dashboard specification, raw data, and visual assets. Use when Codex needs to profile and transform dashboard data; persist semantic-model relationships and DAX measures in TMDL; bind PBIR visuals to required model fields and roles; define Power Query M, themes, layouts, or interactions; create or update PBIP/PBIR/TMDL artifacts; prepare a PBIX handoff; or test a reproducible Power BI dashboard build.
---

# Generate Power BI Dashboard

Build reproducible Power BI artifacts from explicit business definitions. Prefer a text-based PBIP project over direct binary PBIX editing.

## Read the input contract

Read [references/input-contract.md](references/input-contract.md) before changing files. Use its minimum input checklist, specification template, defaults, and output contract.

## Route PBIR resources

Before creating, modifying, or diagnosing PBIR visuals, read [references/pbir-visual-types.md](references/pbir-visual-types.md). Resolve requested visual names with `scripts/resolve_pbir_visual_type.ps1` and use the matching schema-versioned resources under `assets/pbir/`; do not invent `visualType` identifiers, query roles, analytics object names, selectors, or nesting.

Before creating or validating TMDL measures, TMDL relationships, or PBIR field bindings, read [references/model-visual-contract.md](references/model-visual-contract.md). Generate its machine-readable requirements manifest from the dashboard request and treat it as the binding validation baseline.

Before generating a bound visual, read [references/pbir-binding-assets.md](references/pbir-binding-assets.md). Use the binding asset matching both the declared visual-container schema and `visualType`; require every requested role and binding kind to have a Desktop-authored projection template.

When new Power BI Desktop-authored visual or Analytics samples are supplied, run `scripts/normalize_pbir_samples.ps1` to regenerate canonical assets. Inspect the registry diff and preserve only schema-stable features; never bundle project-specific visual IDs, positions, field bindings, titles, filters, or local paths.

When new Desktop-authored bound visuals are supplied, run `scripts/normalize_pbir_binding_samples.py` to regenerate schema-versioned role/query and formatting assets. Reject generated binding assets that retain project table names, fields, titles, filters, saved selections, visual IDs, or positions.

Apply supported Analytics features with `scripts/set_pbir_visual_feature.ps1`. Run `scripts/validate_pbir.ps1` against every generated or updated Report folder. Treat an unregistered `visualType` or missing schema-specific feature asset as a blocking validation failure until a Desktop-authored sample is available.

## Establish scope

1. Locate the dashboard specification, raw-data package, visual assets, the `template/` directory, existing PBIP/PBIX, and project-local tools.
2. Inventory relevant files without reading unrelated or sensitive content.
3. Distinguish requested deliverables:
   - data preparation only;
   - model and DAX artifacts;
   - report layout and theme;
   - editable PBIP project;
   - final PBIX handoff;
   - Power BI Service publication.
4. Treat publication, credential changes, gateway configuration, production refresh, and overwriting deployed content as separate actions requiring explicit authorization.
5. If a missing business choice would materially change results, report it. Otherwise use the defaults in the input contract and record the assumption.

## Select an execution mode

Use one of the following modes to determine the workflow and required outputs. Treat the selected mode as the default output contract for the current task, so the user does not need to repeat every artifact in the prompt.

### `full`

Use when raw data must be processed and a complete dashboard build is requested.

```text
raw data → processed assets → Power BI sources → PBIP → optional PBIX
```

Perform input profiling, data processing, documentation, semantic-model design, Power BI source generation, report creation, and all available validation.

### `data-only`

Use when the user wants prepared reporting assets and data documentation without creating a Power BI report.

```text
raw data → processed assets + data documentation + validation
```

Stop after asset generation and data validation. Do not generate M, DAX, themes, layouts, PBIP, or PBIX unless the user explicitly adds them to the task.

### `report-only`

Use when processed assets already exist and the user wants Power BI artifacts or a report.

```text
existing assets → asset validation → Power BI sources → PBIP → optional PBIX
```

Validate the supplied asset schemas and representative metrics, but do not recreate or modify those assets unless explicitly requested. Generate documentation needed to explain the model and report.

### `validate-only`

Use for read-only diagnosis or validation of raw data, assets, Power BI sources, PBIP, or PBIX.

```text
existing inputs or outputs → read-only checks → validation report
```

Do not repair, regenerate, overwrite, refresh, publish, or save source artifacts in this mode. A validation report is the only default generated deliverable.

### Choose a mode when omitted

Apply these rules in order:

1. Use the mode explicitly named by the user.
2. Infer `validate-only` when the user asks only to inspect, diagnose, review, or validate.
3. Infer `report-only` when prepared assets are supplied and raw-data processing is not requested.
4. Infer `full` when raw data is supplied and the user asks to build a dashboard.
5. Infer `data-only` only when the user requests data preparation without a report.
6. If two modes remain materially plausible and would produce different mutations or deliverables, request clarification before building. Otherwise state the inferred mode and proceed.

An explicit prompt instruction can narrow or extend the selected mode for the current task. Record any deviation from the default output contract in the build manifest.

## Apply the mode output contract

Generate or validate the following artifacts by default:

| Output | `full` | `data-only` | `report-only` | `validate-only` |
|---|---|---|---|---|
| Input profile | Generate | Generate | Validate available metadata | Validate |
| Processed assets | Generate | Generate | Use existing; do not modify | Validate only |
| Data dictionary | Generate | Generate | Generate or update | Validate only |
| Asset/build manifest | Generate | Generate | Generate | Do not modify existing; include validation run manifest when useful |
| Power Query M | Generate | No | Generate | Validate only |
| DAX measures persisted in TMDL | Generate | No | Generate | Validate only |
| Theme JSON | Generate | No | Generate | Validate only |
| Page-layout specification | Generate | No | Generate | Validate only |
| Relationships persisted in TMDL and documented | Generate | No | Generate | Validate only |
| PBIP/PBIR/TMDL | Generate or update | No | Generate or update | Validate only |
| PBIX | Conditional | No | Conditional | Validate existing only |
| Validation report | Generate | Generate | Generate | Generate |
| Power BI Service publication | Disabled by default | Disabled | Disabled by default | Disabled |

`No` means the artifact is outside the mode's default scope, not forbidden when the user explicitly requests it.

### Treat PBIX as a conditional output

Generate or update PBIX only when all applicable conditions are satisfied:

1. The selected mode is `full` or `report-only`, or the user explicitly requests PBIX.
2. The user has authorized application launch, refresh, conversion, and overwrite actions that are actually required.
3. Power BI Desktop is installed and available, or another verified supported mechanism can perform the requested operation.
4. The PBIP/PBIR opens without blocking model or report errors.
5. Any required refresh succeeds.
6. Power BI Desktop successfully saves the PBIX.

When a condition is not satisfied, deliver the validated source artifacts that can be produced, mark PBIX as `blocked` or `not run` in the validation report, and provide the exact remaining Desktop step. Do not replace a missing PBIX with a renamed archive, preview, layout specification, or unvalidated folder.

### Keep prompt requirements minimal

The invocation prompt normally needs only:

- `$generate-powerbi-dashboard`;
- execution mode;
- paths to the dashboard request, raw data or prepared assets, visual assets, and optional reference report;
- output path;
- task-specific restrictions and authorization boundaries.

Do not require the user to repeat this mode's output list. Follow the mode output contract unless the prompt explicitly changes it.

## Follow the build workflow

### 1. Profile and validate inputs

- Verify file types, sheet names, column names, data types, row counts, keys, nulls, duplicates, date ranges, and units.
- For CSV-backed import partitions, never rely on TMDL column `dataType` alone. Add an explicit Power Query `Table.TransformColumnTypes` step for every imported column, with an explicit culture when decimal/date parsing can vary. Validate that columns consumed by `SUM`, `AVERAGE`, `MEDIAN`, arithmetic, date intelligence, or relationships arrive from M with matching numeric, date, logical, or text types.
- Detect schema drift across periodic files before combining them.
- Never infer relationships from matching names alone; confirm key uniqueness and intended cardinality.
- Do not expose secrets or copy credentials into generated files.
- Preserve raw inputs. Write transformed data to a separate output directory.

### 2. Create reproducible data assets

- Reuse project-local processing scripts when present.
- Make processing deterministic and parameterized by input/output paths.
- Generate tidy CSV, XLSX, or Parquet assets only when the report architecture requires them.
- Record source-to-output lineage, row counts, rejected records, and assumptions.
- Keep generated caches and temporary files out of final deliverables.

### 3. Define the semantic model

- Produce a data dictionary with table grain, column types, business meanings, keys, formats, and hidden-field recommendations.
- Specify relationships with from/to columns, cardinality, filter direction, and active state.
- Prefer a star schema unless the supplied requirements justify another design.
- Define a marked date table and fiscal rules when time intelligence is required.
- Document row-level security, incremental refresh, calculation groups, and localization only when requested or present.
- Persist every requested measure inside a referenced table TMDL file. A standalone `.dax` file is supporting source only and does not satisfy the model deliverable.
- Persist every requested relationship as a TMDL relationship with explicit endpoints, cardinality, filter direction, and active state. Documentation alone does not satisfy the model deliverable.

### 4. Generate Power BI source artifacts

Create only artifacts supported by the requested architecture:

- Power Query M for ingestion and transformations;
- DAX Query View `DEFINE MEASURE` blocks for batch measure creation and evaluation;
- TMDL for model objects when working with PBIP or TMDL View;
- a Power BI theme JSON file;
- a page-layout specification covering visuals, field wells, filters, interactions, sorting, drill-through, tooltips, conditional formatting, and reference lines;
- PBIR report definitions only when an existing valid PBIP/PBIR structure or documented schema is available.

Before generating PBIR, translate every dashboard-request visual into `output/documentation/visual_requirements.json` using the contract reference. Do not create a data-bound visual until its visual type, internal role names, table/field or measure bindings, filters, sorting, and interactions are known.

For PBIR visual generation, use the canonical registry matching the report's declared visual-container schema. Treat the registry as an allowlist for generated built-in visuals. For example, generate a stacked bar chart as `barChart`, never `stackedBarChart`.

Do not fabricate internal PBIX binary content. Do not claim a PBIX exists unless Power BI Desktop successfully opened and saved it.

### 5. Create or update the report

- For `full` and `report-only` modes, use the complete PBIP template stored in the input root's `template/` directory by default. Power BI project templates use the `.pbip` extension; do not search for or invent a `.pbib` file.
- Resolve the template in this order: an explicitly supplied template path; the single `template/*.pbip` project; otherwise a uniquely identifiable `.pbip` project inside `template/`. If multiple candidates remain, stop before modifying files and request the intended template.
- Require the selected template to include sibling `<template-name>.pbip`, `<template-name>.Report/`, and `<template-name>.SemanticModel/` components. Treat a missing component or broken relative reference as an invalid template.
- Copy the complete template project from `template/` to `<output-root>/report/` before editing. Rename the three copied PBIP components to a common requested report-name stem when needed, and update their relative references. Never use the source template directory as the report output.
- Prefer modifying this copied PBIP template because it preserves valid report structure and identifiers.
- Treat the template as a structural and visual-style starting point, never as a limit on the final number of pages, slicers, cards, charts, tables, buttons, or other visuals.
- Create, duplicate, replace, or remove PBIR visual containers as required to implement every visual specified in the dashboard request. Do not stop after binding the template's existing placeholder visuals.
- For every page, build a requirement inventory before editing PBIR that lists each required visual, its type, title, field roles, filters, interactions, and analytics settings. Map every requirement to a generated PBIR visual identifier.
- Write every required field mapping into the corresponding `visual.json` semantic query and `queryState` projections using Desktop-authored role structures. A visual that contains only `visualType`, position, or formatting is an unbound placeholder and is not a report deliverable.
- Require every field referenced by PBIR to exist in the generated TMDL model. Require every requested measure binding to reference a measure actually persisted in TMDL.
- If no bound Desktop-authored sample establishes the role/query structure for a required visual type and schema, stop report completion and obtain or create that sample in Desktop. Do not substitute an unbound visual while claiming the page is complete.
- When the dashboard request specifies multiple slicers, create a separate slicer for every requested field unless the request explicitly calls for a field parameter, hierarchy slicer, combined control, or another shared selection mechanism.
- For every slicer, treat the internal slicer header and the visual-container title as separate settings. By default, set the slicer header to **Off** and the visual title to **On**.
- Use the business-facing field label for the default slicer visual title. An explicit page-level or visual-level instruction in the dashboard request overrides either default independently.
- Preserve unrelated user changes and stable object identifiers.
- Use consistent display folders, names, descriptions, number formats, and sort rules.
- Implement slicer interactions explicitly; never assume every slicer affects every visual.
- Ensure titles and terminology match the business specification.
- If only a PBIX is supplied, request or perform a Power BI Desktop conversion to PBIP when authorized. Treat Desktop conversion as an application step, not a text-file transformation.

### 6. Validate in layers

Run all applicable checks:

1. **Static:** parse JSON, check required files, paths, encodings, names, and references. Require every PBIP/PBIR JSON, PBIR, PBISM, and TMDL text artifact to use UTF-8 without BOM; Power BI Desktop rejects BOM-prefixed report definition files. When generating files from Windows PowerShell 5.1, use `.NET` `UTF8Encoding(false)` rather than `Set-Content -Encoding utf8`.
   - JSON parsing is necessary but not sufficient for PBIR. Validate every `visual.json` against its declared visual-container schema or an equivalent schema-aware structural rule set. Reject additional properties at schema-constrained paths.
   - Run `scripts/validate_pbir.ps1` with the generated Report folder. Fail when a generated `visualType` is absent from the registry for the declared schema. Do not use `-AllowUnknownVisualType` to approve a deliverable.
   - Reject `stackedBarChart` with a targeted error that directs the builder to the Desktop-authored `barChart` mapping.
   - Never place analytics settings such as reference/constant lines under `visual.visualContainerObjects`; that node is for container formatting such as titles. Do not invent an analytics object name or nesting. Capture a Power BI Desktop-authored PBIR example for each visual type and Desktop version, reproduce its exact structure, then validate it before marking the analytics requirement complete.
2. **Data:** reconcile row counts, uniqueness, date coverage, joins, null behavior, and representative totals.
3. **Model:** validate that every requested measure exists as a TMDL `measure`, every requested relationship exists as a TMDL `relationship`, model references resolve, DAX compiles, formats match, filter context behaves correctly, and representative results reconcile. A standalone DAX file or relationship document cannot pass this layer.
4. **Report:** compare `visual_requirements.json`, the dashboard request, and the generated PBIR page by page. Verify every required visual ID and type, then verify every role-to-table/field/measure mapping in the actual semantic query/queryState, plus interactions, sorting, titles, themes, tooltips, and reference lines. Run `scripts/validate_powerbi_contract.py`; any missing query or binding is a blocking failure.
5. **Desktop:** open the PBIP/PBIR in Power BI Desktop, refresh when authorized, and inspect errors.
6. **Regression:** compare representative KPIs and artifact diffs with the approved baseline.

Do not mark Desktop validation complete when Power BI Desktop was unavailable.

### Validate report output placement and completeness

For `full` and `report-only` builds, place every generated report artifact under `output/report/`. When the caller supplies a different output root, interpret this as `<output-root>/report/`. Copy a supplied template into this destination before modifying it; preserve the original template unless the user explicitly requests an in-place update.

Treat a PBIP project as one unit consisting of sibling artifacts:

```text
output/report/
|-- <report-name>.pbip
|-- <report-name>.Report/
|-- <report-name>.SemanticModel/
`-- <report-name>.pbix           # Optional; only after a successful Desktop save
```

Do not place the `.pbip` pointer file at the output root while leaving its `.Report` or `.SemanticModel` folders elsewhere. Preserve their relative references and use the same `<report-name>` stem for all three PBIP components.

Add an **Output placement and PBIP integrity** section to `output/documentation/validation_report.md`. Verify and report:

- the source template was resolved from the explicit path or the input root's `template/` directory;
- the source template contained a valid sibling `.pbip`, `.Report/`, and `.SemanticModel/` project before copying;
- the resolved report output directory is `<output-root>/report/`;
- the `.pbip`, `.Report`, and `.SemanticModel` artifacts all exist there as siblings when PBIP is required;
- the `.pbip` pointer resolves to the sibling `.Report` folder;
- the report definition resolves to the sibling `.SemanticModel` folder;
- required report and semantic-model definition files exist and parse;
- no generated PBIP component was accidentally left only beside the input template or outside the report output directory;
- the source template was preserved unchanged unless the user explicitly authorized an in-place update;
- any requested PBIX exists in the report directory only after Power BI Desktop successfully saved it.

Set this validation section to `Failed` if any required component is missing, misplaced, inconsistently named, or has a broken relative reference. Do not mark the PBIP deliverable complete until these checks pass. If PBIX creation is blocked, the PBIP placement checks may pass independently, but record PBIX as `blocked` or `not run`.

### Require page-level report reconciliation

Include a reconciliation table in the validation report for every generated or updated report:

| Page | Visual type | Required | Generated | Field bindings verified | Interactions verified | Status |
|---|---|---:|---:|---|---|---|
| Example | Slicer | 3 | 3 | Yes | Yes | Passed |

Apply these rules:

- Set `Passed` only when the generated count and implementation match the request.
- Set `Passed` for field bindings only when the contract validator confirms every requested role, table, field, and measure in the corresponding `visual.json`.
- Set `Failed` when a required page, slicer, card, chart, table, or other visual is missing, extra without justification, incorrectly bound, or configured with the wrong interaction.
- Set `Failed` when a data-bound visual has no semantic query/queryState, even if its `visualType`, geometry, and JSON schema are valid.
- Treat JSON parsing, TMDL parsing, page counts, and total visual counts as structural checks only; they do not prove business requirements were implemented.
- Do not mark the report or PBIP complete while any required page-level reconciliation row is failed or unverified.
- Record intentional deviations separately with the user's instruction or an explicit documented assumption.

### Validate visual layout and formatting

Read the dashboard request's page-layout requirements and validate PBIR geometry and formatting page by page. When the request uses the standard 1280 × 720 layout, enforce these checks unless an explicit page-level override exists:

- Canvas is 1280 × 720.
- Every visual stays within the 24 px outer margin: `X ≥ 24`, `Y ≥ 24`, `X + Width ≤ 1256`, and `Y + Height ≤ 696`.
- Adjacent visuals do not overlap and normally use a 16 px horizontal or vertical gap.
- All slicers appear in the top slicer row at Y = 72 with Height = 72.
- Slicers on the same page have equal widths and 16 px gaps.
- Slicer width follows `(1232 - (slicer_count - 1) × 16) ÷ slicer_count` within normal numeric rounding tolerance.
- Every slicer uses Dropdown style unless the dashboard request explicitly specifies another style.
- Every slicer uses an internal slicer header setting of Off unless the dashboard request explicitly specifies otherwise.
- Slicer visual titles are On and match the requested business-facing labels unless the dashboard request explicitly specifies otherwise.
- Validate slicer header visibility and visual-title visibility independently; do not infer one setting from the other.
- KPI cards in the same row have equal widths and heights; standard KPI height is 96 px.
- Visuals in the same row share the same Y and Height values.
- A visual occupying a row by itself is centered at X = 24 with Width = 1232.
- Two half-page comparison visuals use equal Width = 608 and align at X = 24 and X = 648.
- Tables and charts follow the requested font, wrapping, alignment, title, background, and border rules when those properties are represented in PBIR or the theme.

Include layout results in the validation report:

| Page | Check | Expected | Actual | Status |
|---|---|---|---|---|
| Example | Slicer widths | 3 × 400 px | 3 × 400 px | Passed |
| Example | Slicer style | Dropdown | Dropdown | Passed |
| Example | Full-row table | X 24, Width 1232 | X 24, Width 1232 | Passed |

Set the report layout status to `Failed` when required visuals overlap, exceed the canvas, use inconsistent same-row dimensions, omit requested slicers, or violate an explicit layout requirement. Do not mark PBIP complete until failed layout checks are corrected or explicitly accepted by the user.

## Organize outputs

For every mode that generates or updates a report, `output/report/` is mandatory. It contains the complete PBIP project and any optional PBIX; never split PBIP components across the input directory and output directory.

Use this structure unless the user supplies another one:

```text
output/
├── tools/                 # Reusable processing and validation scripts
├── assets/                # Processed report data and approved visual assets
├── dashboard_base/
│   ├── power_query_import.m
│   ├── data_measures.dax
│   ├── dashboard_theme.json
│   └── page_layout_spec.md
├── report/                # PBIP project and optional Desktop-generated PBIX
└── documentation/
    ├── data_dictionary.md
    ├── measure_list.md
    ├── model_relationships.md
    ├── build_manifest.md
    └── validation_report.md
```

The `report/` directory must contain sibling `<name>.pbip`, `<name>.Report/`, and `<name>.SemanticModel/` artifacts that share the same name stem. Place `<name>.pbix` there only after a successful Desktop save.

Avoid copying raw data into `output/` unless explicitly requested. Use relative paths when practical and keep final artifacts free of machine-specific credentials. Do not modify an input PBIP template in place as the only deliverable: copy the complete project to `output/report/`, then edit and validate that output copy unless the user explicitly requests an in-place update.

## Report completion

Return:

- the exact artifacts created or changed;
- validation performed and results;
- assumptions and unresolved issues;
- whether PBIP was opened successfully in Desktop;
- whether PBIX was actually saved;
- reproducible next commands or manual steps.

Never describe a layout specification, unbound visual container, preview, or unvalidated folder as a completed PBIP/PBIX report. In `full` and `report-only` modes, do not mark the PBIP complete unless required measures and relationships are persisted in TMDL and all dashboard-request field mappings pass contract validation.
