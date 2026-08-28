# TMDL model and PBIR field-binding contract

Read this reference for every `full`, `report-only`, or `validate-only` task that creates or checks a semantic model or report.

## Build a machine-readable requirements manifest

Translate the dashboard request into `output/documentation/visual_requirements.json` before editing PBIR or TMDL. Preserve the request's table, field, measure, role, page, filter, sort, interaction, and analytics requirements. Use this minimum shape:

```json
{
  "measures": [
    {"table": "Part2PriceIndex", "name": "Regular Price Index"}
  ],
  "relationships": [
    {
      "fromTable": "DimMonth",
      "fromColumn": "Month",
      "toTable": "Part2PriceIndex",
      "toColumn": "month",
      "active": true,
      "crossFilteringBehavior": "oneDirection"
    }
  ],
  "visuals": [
    {
      "page": "2. Price Index",
      "visualId": "price-index-regular-trend",
      "visualType": "lineChart",
      "bindings": [
        {"role": "Category", "table": "DimMonth", "field": "MonthStart", "kind": "column"},
        {"role": "Y", "table": "Part2PriceIndex", "field": "Regular Price Index", "kind": "measure"},
        {"role": "Series", "table": "Part2PriceIndex", "field": "retailer", "kind": "column"}
      ]
    }
  ]
}
```

Use the exact PBIR role names established by a Power BI Desktop-authored bound sample for the selected visual type and schema. Do not translate a business role such as “X-axis” into a guessed internal role.

## Persist the semantic model

- Write every requested measure as a `measure` object inside a referenced table `.tmdl` file. A standalone DAX Query View `DEFINE MEASURE` file is a reproducible source, not proof that the measure exists in the model.
- Write every requested relationship as a `relationship` object in TMDL and reference it from `model.tmdl` when the serialization layout requires a reference.
- Set relationship columns, cardinality, cross-filtering behavior, and active state explicitly. Do not treat relationship documentation as model implementation.
- Preserve display folders, descriptions, formats, hidden state, and sort-by columns required by the request.

## Persist PBIR field mappings

Every data-bound visual must contain all of the following:

1. A semantic query/select definition that resolves each referenced column or measure to the intended model table.
2. `queryState` projections or the schema-equivalent role mapping for every required role.
3. A matching data shape/field mapping when required by the declared PBIR schema and visual type.
4. Filters, sorting, highlights, and interactions required by the dashboard request.

An unbound visual containing only `visualType`, position, and formatting is a placeholder. It must fail report reconciliation in `full` and `report-only` modes.

If the supplied template lacks a Desktop-authored bound sample for a required visual type, stop report completion and obtain or create one in Power BI Desktop. Normalize the structural pattern without retaining sample-specific table names, fields, IDs, or filters, then bind it to the current requirements. Do not downgrade the requirement to an unbound visual.

## Validate

Run `scripts/validate_powerbi_contract.py` with the generated report root, semantic-model root, and requirements manifest. Treat any missing measure, relationship, visual, role, field, query definition, or mapping as a blocking failure. Include its JSON result in the validation documentation.

Desktop validation remains required after static validation. Confirm that measures compile, relationships appear in Model view, fields populate every visual, filters propagate as intended, and saving/reopening preserves all bindings.
