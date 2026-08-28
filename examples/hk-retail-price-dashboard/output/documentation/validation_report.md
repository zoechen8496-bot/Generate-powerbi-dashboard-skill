# Validation report

## Input and data

- Passed: 3 XLSX files with the required worksheet and schema.
- Passed: 442,096 normalized rows covering 2024-01-01 to 2024-03-31.
- Warning: the request's historical 31-file acceptance baseline differs from the three files physically supplied.

## Output placement and PBIP integrity

- Passed: complete source `Dashboard.pbip`, `Dashboard.Report`, and `Dashboard.SemanticModel` copied to `output/report`.
- Passed: source template preserved.
- Passed: `Dashboard.pbip` resolves `Dashboard.Report`, whose `definition.pbir` resolves `../Dashboard.SemanticModel`.
- PBIX: pending interactive Desktop save; PBIP is the generated source artifact.

## Contract summary

- Requested/persisted measures: 27
- Persisted relationships: 9
- PBIR visuals: 31; visuals with semantic bindings: 31
- Passed: Power BI contract validation (`errors: 0`).
- Passed: PBIR validation (`errors: 0`, `warnings: 0`).
- Passed: all 31 visuals contain generated `queryState` bindings.
- Passed: 31 visuals remain inside the 1280 x 720 canvas margins; all slicers occupy the normalized top row.
- Passed: JSON-like files parse successfully, no UTF-8 BOM was found, and no Markdown fences remain in TMDL.

## Generated datasets

| File | Rows | Columns |
|---|---:|---:|
| dim_date.csv | 91 | 5 |
| dim_month.csv | 3 | 6 |
| dim_sku_catalog.csv | 2,319 | 6 |
| fact_price_observations.csv | 442,096 | 19 |
| part1_assortment.csv | 158 | 9 |
| part2_price_index.csv | 8,604 | 11 |
| part3_promotion_intensity.csv | 4,540 | 16 |
| part4_retailer_positioning_matrix.csv | 56 | 12 |

## Desktop validation

- Power BI Desktop launch target: `D:\Power Bi\bin\PBIDesktop.exe`.
- Initial load failed at `tables/DimDate.tmdl:5`: a generated measure had been inserted before the table-level `lineageTag`, violating TMDL property ordering.
- Fixed: new measures are now inserted after table scalar properties and before the first child object.
- Fixed: both the report generator and skill contract validator now reject table properties emitted after child objects.
- Re-generated and re-launched `Dashboard.pbip` in Power BI Desktop (process PID 2264).
- Passed: the original DimDate indentation error did not recur; Desktop and `msmdsrv` remained responsive while importing the model.
- Passed: no new Power BI Frown snapshot was generated during the post-fix observation window.
- PBIX was not created automatically; use **Save As** in Desktop if a standalone `.pbix` deliverable is required.
