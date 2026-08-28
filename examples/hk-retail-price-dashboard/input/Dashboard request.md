# Dashboard request

## 0. Setting Info

Power BI Desktop Address: D:\Power Bi\bin\PBIDesktop.exe

 

## 1. Goal and audience

- **Dashboard name:** Retail Price Intelligence
- **Business goal:** Compare retailer assortment breadth, matched-SKU price competitiveness, promotion intensity, and annual retailer positioning across product categories and time.
- **Primary questions:**
  1. Which retailers provide broader SKU and brand coverage within a selected Category 1?
  2. Which retailers have a regular or promotional price advantage relative to the matched-SKU market average?
  3. How frequently and deeply does each retailer promote products?
  4. How do annual price competitiveness and assortment breadth position each retailer?
- **Intended users:** Retail pricing, category management, sourcing, commercial, and vendor-negotiation teams.
- **Refresh frequency:** Monthly, after the complete monthly XLSX file is placed in `rawdata/`.
- **Locale:** English field and visual labels; source prices are interpreted as Hong Kong retail prices.
- **Time zone:** Asia/Hong_Kong for business interpretation; the current data contains dates without time-of-day values.
- **Expected reference output:** `Dashboard.pbix`, last modified 2026-08-24.
- **Expected report scope:** Four report pages. The external opportunity CSV assets and proposed fifth opportunity page are not part of the current reference PBIX.

## 2. Inputs

### 2.1 Raw data package

- **Path:** `rawdata/*.xlsx`
- **Files:** 3 monthly workbooks, from `202401.xlsx` through `202403.xlsx`.
- **Worksheet:** `data` in every workbook.
- **Schema consistency:** All 3 workbooks have the same 13-column schema.
- **Date coverage:** 2024-01-01 through 2024-03-31.
- **Expected file naming:** `YYYYMM.xlsx`.
- **Append rule:** Append all monthly workbooks after schema validation; do not overwrite or modify raw workbooks.

### 2.2 Raw columns

| Raw column | Target name | Type | Meaning | Required | Sensitive |
|---|---|---|---|---|---|
| `data_date` | `data_date` | Date | Daily price-observation date | Yes | No |
| `source_csv` | Excluded from the current normalized fact | Text | Original daily source-file identifier | No | No |
| `Category 1` | `category1` | Text | Top-level product category | Yes | No |
| `Category 2` | `category2` | Text | Second-level product category | Yes | No |
| `Category 3` | `category3` | Text | Third-level product category | Yes | No |
| `Product Code` | `sku` | Text | SKU/business product identifier | Yes | No |
| `Brand` | `brand` | Text | Product brand | Yes | No |
| `Product Name` | `product_name` | Text | Product description | Yes | No |
| `Supermarket Code` | `retailer` | Text | Retailer identifier | Yes | No |
| `Price` | `regular_price` | Decimal | Listed regular price | Yes; nulls tolerated and excluded from price calculations | No |
| `Offers` | `offers` | Text | Raw promotion description | No | No |
| `offer_category` | `offer_category` | Text | Normalized promotion mechanism | Yes | No |
| `real_unit_price` | `real_unit_price` | Decimal | Effective unit price after offer | No; fall back to regular price | No |



## 3. Data-processing rules

### 3.1 Normalization

1. Trim raw column names and fail when a required column is missing.
2. Rename category, SKU, brand, product, retailer, and regular-price columns to the target names in section 2.2.
3. Parse `data_date`; derive:
   - `month = YYYY-MM`
   - `year`
   - `month_days`
4. Convert `regular_price` and `real_unit_price` to numeric values.
5. Set `promo_price = real_unit_price`; when it is null, use `regular_price`.
6. Set `is_promo = TRUE` only when `offers` is nonblank and `offer_category <> "no_offer"`.
7. Set `discount_pct = (regular_price - promo_price) / regular_price` when the row is promotional and regular price is greater than zero; otherwise blank.
8. Remove rows missing `data_date`, `sku`, `retailer`, or `category1` from the normalized fact.

### 3.2 Business definitions

- **Category Total SKU Count:** Distinct SKUs available from any retailer in the selected month and Category 1.
- **SKU Count:** Distinct SKUs available from one retailer in the selected month and Category 1.
- **Category Coverage %:** Retailer SKU Count divided by Category Total SKU Count.
- **Exclusive SKU Count:** Distinct SKUs sold by exactly one retailer within the selected month and Category 1.
- **Common SKU Count:** Distinct SKUs sold by more than one retailer within the selected month and Category 1.
- **Matched SKU:** A SKU sold by more than one retailer within the same month and selected category level.
- **Matched SKU Count:** Number of distinct matched SKUs used in the price-index calculation.
- **Market price for a matched SKU:** Average applicable price for that SKU across retailers.
- **Retailer Price Index:** Average retailer price for matched SKUs divided by average matched-SKU market price, multiplied by 100.
- **Regular Price Index:** Price Index calculated from `regular_price`.
- **Promo Price Index:** Price Index calculated from `promo_price`, including regular-price fallback when no effective promotion price is available.
- **Price-index interpretation:** Below 100 is cheaper than market; 100 is market average; above 100 is more expensive than market.
- **Promo Days:** Count of observed SKU-days where `is_promo = TRUE`.
- **Promo SKU %:** SKUs with at least one valid promotion divided by total observed SKUs.
- **Average Promo Days:** Average Promo Days at SKU level within the current aggregation context.
- **Promotion Frequency:** Average Promo Days divided by calendar days in the month.
- **Average Discount %:** Mean SKU-level promotional discount percentage.
- **Median Discount %:** Median of SKU-level median promotional discount percentages.
- **Annual metrics:** Arithmetic mean of the corresponding monthly Category 1/retailer results within each calendar year. The 2026 value is year-to-date through July.

## 4. Semantic-model tables

| Table | Grain | Main columns | Role |
|---|---|---|---|
| `DimDate` | One row per calendar date | Date, Year, MonthNo, Month, MonthName | Calendar helper |
| `DimMonth` | One row per month | Month, MonthStart, Year, MonthNo, MonthName, YearMonthSort | Shared monthly axis and relationship key |
| `DimSkuCatalog` | One row per SKU using latest description | sku, product_name, brand, category1, category2, category3 | SKU/product dimension |
| `FactPriceObservations` | One daily SKU-retailer observation | normalized raw fields plus month, year, promo fields | Detailed fact; avoid using for summary visuals unless needed |
| `Part1Assortment` | Month × Category 1 × retailer | counts and coverage metrics | Page 1 summary |
| `Part2PriceIndex` | Month × category level/value × retailer × index type | matched counts, average prices, index | Page 2 summary |
| `Part3PromotionIntensity` | Month × category level/value × retailer | promotion and discount metrics | Page 3 summary |
| `Part4RetailerPositioningMatrix` | Year × Category 1 × retailer | annual coverage and index metrics | Page 4 summary |

Opportunity CSV files may remain in `assets/`, but the current reference PBIX does not establish their inclusion in the semantic model or report pages.

## 5. Model relationships

The PBIX diagram confirms the eight tables above, but its compressed DataModel relationships were not decoded during this documentation pass. The following target relationships must be verified in Power BI Desktop:

| From | To | Cardinality | Filter direction | Active | Purpose |
|---|---|---|---|---|---|
| `DimMonth[Month]` | `Part1Assortment[month]` | 1:* | Single | Yes | Shared monthly filtering |
| `DimMonth[Month]` | `Part2PriceIndex[month]` | 1:* | Single | Yes | Shared monthly filtering and line-chart axis |
| `DimMonth[Month]` | `Part3PromotionIntensity[month]` | 1:* | Single | Yes | Shared monthly filtering and line-chart axis |
| `DimMonth[Month]` | `DimDate[Month]` | 1:* | Single | Yes | Shared monthly filtering |
| `DimSkuCatalog[sku]` | `FactPriceObservations[sku]` | 1:* | Single | Yes | Product-to-observation filtering |

Additional guidance:

- Do not relate summary tables directly on nonunique Category 1 fields.
- Page-specific category slicers may use columns from their respective summary tables.
- Synced or hidden slicers found in the PBIX must not be replaced with ambiguous many-to-many relationships.
- Confirm `DimMonth[Month]` uniqueness and sort `MonthName`/Month by `YearMonthSort`.
- Keep `Part4RetailerPositioningMatrix` filtered by its own `year` and `category1` slicers unless a dedicated year/category dimension is introduced deliberately.

## 6. Measures

Create explicit model measures and use the formats below. Avoid implicit aggregation in a rebuilt version even where the current PBIX contains an implicit Sum or Average binding.

| Measure | Definition | Format |
|---|---|---|
| `Selected Month Count` | `DISTINCTCOUNT(DimDate[Month])` | Whole number |
| `Retailer Count` | `DISTINCTCOUNT(Part1Assortment[retailer])` | Whole number |
| `SKU Count` | `SUM(Part1Assortment[sku_count])` | Whole number |
| `Brand Count` | `SUM(Part1Assortment[brand_count])` | Whole number |
| `Category Total SKU Count` | `MAX(Part1Assortment[category_total_sku_count])` | Whole number |
| `Category Coverage %` | `AVERAGE(Part1Assortment[category_coverage_pct])` | 0.0% |
| `Exclusive SKU Count` | `SUM(Part1Assortment[exclusive_sku_count])` | Whole number |
| `Common SKU Count` | `SUM(Part1Assortment[common_sku_count])` | Whole number |
| `Coverage Gap %` | `1 - [Category Coverage %]` | 0.0% |
| `Show Visual` | Return 1 only when exactly one `Part1Assortment[category1]` is selected; otherwise 0 | Whole number, hidden |
| `Regular Price Index` | Average `Part2PriceIndex[price_index]` filtered to `regular_price_index` | 0.0 |
| `Promo Price Index` | Average `Part2PriceIndex[price_index]` filtered to `promo_price_index` | 0.0 |
| `Matched SKU Count` | Average `Part2PriceIndex[matched_sku_count]` in current context | 0 |
| `Price Advantage vs Market` | `100 - [Regular Price Index]` | 0.0 |
| `Promo Price Advantage vs Market` | `100 - [Promo Price Index]` | 0.0 |
| `Promo SKU %` | Average `Part3PromotionIntensity[promo_sku_pct]` | 0.0% |
| `Average Promo Days` | Average `Part3PromotionIntensity[avg_promo_days]` | 0.0 |
| `Promotion Frequency` | Average `Part3PromotionIntensity[promotion_frequency]` | 0.0% |
| `Average Discount %` | Average `Part3PromotionIntensity[avg_discount_pct]` | 0.0% |
| `Median Discount %` | Average `Part3PromotionIntensity[median_discount_pct]` | 0.0% |
| `Promo Matched SKU Count` | Average `Part3PromotionIntensity[promo_index_matched_sku_count]` | 0 |
| `Annual SKU Coverage %` | Average `Part4RetailerPositioningMatrix[avg_category_coverage_pct]` | 0.0% |
| `Annual Regular Price Index` | Average annual regular-price index column | 0.0 |
| `Annual Promo Price Index` | Average annual promo-price index column | 0.0 |
| `Annual Avg SKU Count` | Average `Part4RetailerPositioningMatrix[avg_sku_count]` | 0.0 |
| `Annual Avg Brand Count` | Average `Part4RetailerPositioningMatrix[avg_brand_count]` | 0.0 |

The exact executable DAX remains in `powerbi/dax_measures.dax`. If measures are created through DAX Query View, run the query and then select **Update model with changes**; running the query alone does not persist query-scoped measures.

## 7. Report pages

### Global report behavior

- **Canvas:** 1280 × 720, 16:9.
- **Page order:** Assortment, Price Index, Promotion Intensity, Retailer Positioning Matrix.
- **Theme:** `powerbi/dashboard_theme.json` / embedded `Retail Price Intelligence` theme.
- **Visual interactions:** Slicers filter the visuals on their own page unless explicitly disabled. Preserve the reference PBIX's synced/overlapping slicer behavior until it is intentionally redesigned.
- **Reference PBIX note:** Several synced helper slicers overlap visible slicers. Rebuilding must preserve the effective filtering behavior, not necessarily the overlap itself.

### Page 1 — `1. Assortment`

- **Purpose:** Compare assortment coverage and shared/exclusive SKU breadth by retailer after selecting a Category 1.
- **Slicers found in PBIX:**
  - Visible/primary month selection from `Part1Assortment[month]`.
  - Category selection from `Part1Assortment[category1]`.
  - Retailer helper selection from `FactPriceObservations[retailer]`.
  - Overlapping/synced helper month selection from `Part2PriceIndex[month]`.
- **Reference default selections stored in PBIX:** Category 1 = `Bakery / Cereals / Spreads`; helper month values include `2024-01` and `2024-02`. Defaults should be treated as sample state, not hard-coded business rules.
- **Visuals:**

| Type | Title/purpose | Field mapping | Interaction/filter |
|---|---|---|---|
| Card | Category Total SKU Count | `Category Total SKU Count` | Page slicers |
| Card | Category Coverage % | `Category Coverage %` | Page slicers |
| Card | Retailer Count | `Retailer Count` | Page slicers |
| Stacked bar | Common vs Exclusive SKU Count by Retailer | Category: retailer; Values: Common SKU Count, Exclusive SKU Count | Visual filter `[Show Visual] = 1` |
| Clustered bar | Category Coverage % by Retailer | Category: retailer; Value: Category Coverage % | Visual filter `[Show Visual] = 1` |

- **Conditional visibility:** The two charts display data only when one Category 1 is selected.
- **Sort:** Retailer categories in stable ascending label order unless the user explicitly selects metric sorting.

### Page 2 — `2. Price Index`

- **Purpose:** Compare regular and promotional price competitiveness using only matched SKUs.
- **Slicers found in PBIX:**
  - `Part2PriceIndex[month]`
  - `Part2PriceIndex[category1]`
  - `Part2PriceIndex[category2]`
  - `Part2PriceIndex[category3]`
  - An overlapping/helper `DimSkuCatalog[category1]` slicer
- **Category behavior:** `category2` and `category3` use the generated `ALL` member when the selected aggregation is at a higher category level.
- **Visuals:**

| Type | Recommended title | Field mapping | Analytics |
|---|---|---|---|
| Table | Retailer Price Index Summary | retailer, Regular Price Index, Promo Price Index | No total required |
| Line chart | Regular Price Competitiveness Over Time | X: `DimMonth[MonthStart]`; Y: Regular Price Index; Legend: retailer | Zoom slider; market reference is 100 |
| Line chart | Promotional Price Competitiveness Over Time | X: `DimMonth[MonthStart]`; Y: Promo Price Index; Legend: retailer | Zoom slider; market reference is 100 |

- **Time-axis sort:** Ascending by `MonthStart`.
- **Interpretation:** Lower index means greater price advantage.

### Page 3 — `3. Promotion Intensity`

- **Purpose:** Compare how frequently and deeply retailers promote products.
- **Slicers found in PBIX:**
  - `Part3PromotionIntensity[month]`
  - `Part3PromotionIntensity[category1]`
  - `Part3PromotionIntensity[category2]`
  - `Part3PromotionIntensity[category3]`
  - An overlapping/helper `DimSkuCatalog[category1]` slicer
- **Visuals:**

| Type | Recommended title | Field mapping |
|---|---|---|
| Table | Promotion Intensity by Retailer | retailer, Promo SKU %, Promo Matched SKU Count, Median Discount %, Average Promo Days, Average Discount % |
| Line chart | Promotion Frequency Over Time | X: `DimMonth[MonthStart]`; Y: Promotion Frequency; Legend: retailer |

- **Time-axis behavior:** Ascending month order with zoom slider.
- **Percentage formatting:** Promo SKU %, Promotion Frequency, Average Discount %, and Median Discount % use percentage formatting.

### Page 4 — `4. Retailer Positioning Matrix`

- **Purpose:** Show annual retailer positioning by Category 1 using assortment breadth and price competitiveness.
- **Slicers found in PBIX:**
  - Visible year selection from `Part4RetailerPositioningMatrix[year]`.
  - Visible category selection from `Part4RetailerPositioningMatrix[category1]`.
  - Overlapping/helper `Part2PriceIndex[month]` and `DimSkuCatalog[category1]` slicers.
- **Visuals:**

| Type | Title | Field mapping | Analytics |
|---|---|---|---|
| Scatter | Regular Price Advantage & Assortment Breadth | X: Annual SKU Coverage %; Y: Annual Regular Price Index; Size: Annual Avg SKU Count; Legend/Series: retailer | Y constant line = 100 |
| Scatter | Promotional Price Advantage & Assortment Breadth | X: Annual SKU Coverage %; Y: Annual Promo Price Index; Size: Annual Avg SKU Count; Legend/Series: retailer | Y constant line = 100 |
| Table | Annual Retailer Positioning Summary | retailer, Annual Regular Price Index, Annual Promo Price Index, Annual SKU Coverage % | Filtered by year and Category 1 |

- **Scatter detail behavior:** The current PBIX does not bind `category1` to the Details field. Category 1 is selected through the slicer, so each bubble represents a retailer within the selected year/category context.
- **Interpretation:** Moving right indicates broader SKU coverage; moving downward below 100 indicates stronger price advantage.

## 8. Visual system

- **Theme name:** Retail Price Intelligence
- **Primary palette:** `#2166AC`, `#B2182B`, `#4D9221`, `#F4A582`, `#5E3C99`, `#35978F`, `#9970AB`, `#BF812D`
- **Canvas background:** `#F7F8FA`
- **Visual background:** `#FFFFFF`
- **Foreground/title color:** `#202124`
- **Secondary label color:** `#4F5661`
- **Border:** `#E1E4E8`, radius 4
- **Title font:** Segoe UI Semibold, 11 pt at visual level
- **Page/title text class:** Segoe UI Semibold, 16 pt
- **Label font:** Segoe UI, 10 pt
- **Callout font:** Segoe UI Semibold, 22 pt
- **Logo:** None embedded or required by the reference PBIX.
- **Number formats:**
  - Counts: `#,0`
  - Percentage metrics: `0.0%`
  - Price indexes: `0.0`
  - Prices: currency/decimal format appropriate to HKD, normally two decimal places

### 8.1 Page layout requirements

Apply these requirements to every report page unless a page-specific instruction explicitly overrides them:

- **Canvas:** 1280 × 720, 16:9.
- **Grid:** Use a 12-column layout grid.
- **Outer margin:** 24 px on the left, right, top, and bottom.
- **Horizontal and vertical gap:** 16 px between adjacent visuals.
- **Usable page width:** `1280 - 24 - 24 = 1232 px`.
- **Page title area:** X = 24, Y = 24, Width = 1232, Height = 32.
- Keep every visual inside the usable canvas: `X ≥ 24`, `Y ≥ 24`, `X + Width ≤ 1256`, and `Y + Height ≤ 696`.
- Do not overlap visuals. Align visual edges to the grid wherever practical.

#### Slicer row

- Place all page slicers in a single row at the top of the page, immediately below the title area.
- Use Y = 72 and Height = 72 for every slicer.
- Give every slicer on the same page the same width.
- Use a 16 px horizontal gap between slicers.
- Calculate slicer width as `(1232 - (slicer_count - 1) × 16) ÷ slicer_count`.
- Set the default slicer style to **Dropdown**.
- Keep slicer titles visible and use the business-facing field name.
- Do not use a template's existing slicer count as a limit; create one slicer for every field required by the page specification.

Standard slicer positions:

| Slicer count | Width | X positions |
|---:|---:|---|
| 2 | 608 | 24, 648 |
| 3 | 400 | 24, 440, 856 |
| 4 | 296 | 24, 336, 648, 960 |

#### KPI and content rows

- Start the next row at Y = 160 after a single slicer row.
- Use Height = 96 for KPI cards.
- Give KPI cards in the same row equal widths and heights.
- Use Width = 296 for four equal KPI cards, Width = 400 for three, and Width = 608 for two.
- Use Width = 608 for two half-page visuals placed at X = 24 and X = 648.
- Use Width = 400 for three equal visuals placed at X = 24, X = 440, and X = 856.
- Use Width = 1232 for any visual that occupies a row by itself.
- Center every single-row visual by setting X = 24; its width must equal the usable page width of 1232 px.
- Give visuals in the same row identical Y and Height values.
- Use a 16 px vertical gap between rows.

#### Tables and charts

- Use a full-width table when it occupies a row by itself: X = 24 and Width = 1232.
- Use equal-height, equal-width containers for charts presented as a comparison pair.
- Default table font: Segoe UI, 10 pt; header: Segoe UI Semibold, 10–11 pt.
- Default table row padding: 6–8 px.
- Disable value wrapping and column-header wrapping unless the page specification requires long text.
- Disable automatic column-width changes after finalizing the layout.
- Left-align text fields and right-align counts, currency, percentages, and price indexes.
- Use consistent title height, font, padding, background, and border styling across all visuals.

## 9. Security and deployment

- **RLS:** No RLS requirement is established by the reference PBIX.
- **Sensitivity classification:** No sensitive or personal columns were identified in the supplied schema.
- **Credentials:** Raw data is local-file based; do not embed user-specific credentials in M, DAX, PBIP, or documentation.
- **Target workspace:** Not specified.
- **Overwrite published content:** Not authorized.
- **Gateway:** Not required for local Desktop use; required deployment behavior is not specified.
- **Publication:** Out of scope unless separately requested.

## 10. Acceptance criteria

### Data

- All 31 workbooks load from the `data` worksheet with the expected schema.
- Normalized row count is 5,773,143 before any newly supplied month is added.
- Date coverage is 2024-01-01 through 2026-07-31 for the current package.
- All nine expected retailers are present.
- Price-index calculations use only matched SKUs sold by more than one retailer.
- Null effective-unit prices fall back to regular price.
- Source files remain unchanged.

### Model

- The eight expected tables load and the four target relationships are reviewed in Model View.
- `DimMonth[Month]` is unique and month labels sort chronologically.
- Measures compile and have the formats specified in section 6.
- No accidental many-to-many category relationship is introduced.
- The 2026 annual positioning metrics are clearly understood as year-to-date through July.

### Report

- The report contains exactly four visible pages in the order documented in section 7.
- Every page uses a 1280 × 720 canvas and the Retail Price Intelligence theme.
- Page 1 charts show values only after a single Category 1 is selected.
- Page 2 contains the retailer table and separate regular/promo index trend charts.
- Page 3 contains the promotion table and promotion-frequency trend chart.
- Page 4 contains two scatter charts, both with a Y-axis constant line at 100, and the annual summary table.
- The scatter charts use retailer as the series and do not require Category 1 in Details.
- Slicer interactions match the effective behavior of the reference PBIX.

### Deliverables and validation

- Required final file: `Dashboard.pbix` matching the documented reference structure.
- Required reproducible sources: processing script, processed CSV assets, Power Query M, DAX measure source, theme JSON, and this dashboard request.
- PBIX must open successfully in Power BI Desktop without model or visual errors.
- Refresh is required only when validating changed input or query logic; do not publish.
- Validate representative totals and selected Category 1/month combinations against the processed CSV assets.
- Record unresolved relationship, sync-slicer, and implicit-measure differences before replacing the reference PBIX.

## 11. Evidence and known limitations

- **Confirmed directly from raw data:** workbook count, sheet name, column schema, row counts, date coverage, null profile, retailer/category counts, and observed value ranges.
- **Confirmed directly from `Dashboard.pbix`:** four page names/order, 1280 × 720 canvas, visual types and field bindings, embedded theme name, two scatter constant lines at 100, saved slicer states, and the eight tables shown in Diagram Layout.
- **Confirmed from processing code:** normalization rules, promotion logic, matched-SKU index logic, annual aggregation, and processed asset definitions.
- **Requires Power BI Desktop validation:** physical relationships inside the compressed DataModel, hidden/synced slicer intent, exact committed DAX expressions for measures not present in the saved DAX query, and refresh behavior.
- The PBIX contains a saved DAX Query View script for opportunity measures, but this does not prove those measures were committed to the model. They are therefore excluded from the expected four-page output.
