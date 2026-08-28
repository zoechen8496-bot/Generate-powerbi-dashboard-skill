from __future__ import annotations

import hashlib
import json
import re
import shutil
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parent
INPUT = ROOT / "input"
TEMPLATE = INPUT / "template"
OUTPUT = ROOT / "output"
ASSETS = OUTPUT / "assets"
REPORT = OUTPUT / "report"
DOCS = OUTPUT / "documentation"
BASE = OUTPUT / "dashboard_base"


def write_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value, encoding="utf-8", newline="\n")


def write_json(path: Path, value: object) -> None:
    write_text(path, json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_fact() -> tuple[pd.DataFrame, list[dict]]:
    required = ["data_date", "Category 1", "Category 2", "Category 3", "Product Code", "Brand",
                "Product Name", "Supermarket Code", "Price", "Offers", "offer_category", "real_unit_price"]
    frames, profile = [], []
    for path in sorted((INPUT / "rawdata").glob("*.xlsx")):
        frame = pd.read_excel(path, sheet_name="data", engine="openpyxl")
        frame.columns = [str(column).strip() for column in frame.columns]
        missing = sorted(set(required) - set(frame.columns))
        if missing:
            raise ValueError(f"{path.name}: missing required columns: {missing}")
        frame["source_file"] = path.name
        frames.append(frame)
        profile.append({"file": path.name, "rows": len(frame), "columns": len(frame.columns) - 1,
                        "sha256": sha256(path), "modified": path.stat().st_mtime})
    raw = pd.concat(frames, ignore_index=True).rename(columns={
        "Category 1": "category1", "Category 2": "category2", "Category 3": "category3",
        "Product Code": "sku", "Brand": "brand", "Product Name": "product_name",
        "Supermarket Code": "retailer", "Price": "regular_price", "Offers": "offers",
    })
    raw["data_date"] = pd.to_datetime(raw["data_date"], errors="coerce").dt.normalize()
    for column in ["regular_price", "real_unit_price"]:
        raw[column] = pd.to_numeric(raw[column], errors="coerce")
    for column in ["sku", "retailer", "category1", "category2", "category3", "brand", "product_name"]:
        raw[column] = raw[column].astype("string").str.strip()
    raw = raw.dropna(subset=["data_date", "sku", "retailer", "category1"]).copy()
    raw["month"] = raw.data_date.dt.strftime("%Y-%m")
    raw["year"] = raw.data_date.dt.year.astype("int64")
    raw["month_days"] = raw.data_date.dt.days_in_month.astype("int64")
    raw["promo_price"] = raw.real_unit_price.fillna(raw.regular_price)
    offer_text = raw.offers.astype("string").str.strip()
    offer_category = raw.offer_category.astype("string").str.strip().str.lower()
    raw["is_promo"] = offer_text.notna() & offer_text.ne("") & offer_category.ne("no_offer")
    raw["discount_pct"] = np.where(raw.is_promo & raw.regular_price.gt(0),
                                    (raw.regular_price - raw.promo_price) / raw.regular_price, np.nan)
    columns = ["data_date", "category1", "category2", "category3", "sku", "brand", "product_name",
               "retailer", "regular_price", "offers", "offer_category", "real_unit_price", "month", "year",
               "promo_price", "is_promo", "discount_pct", "source_file", "month_days"]
    return raw[columns], profile


def assortment(fact: pd.DataFrame) -> pd.DataFrame:
    base = fact[["month", "category1", "retailer", "sku", "brand"]].drop_duplicates()
    retailer_count = base.groupby(["month", "category1", "sku"])["retailer"].nunique().rename("retailer_count")
    tagged = base.merge(retailer_count, on=["month", "category1", "sku"])
    out = tagged.groupby(["month", "category1", "retailer"]).agg(
        sku_count=("sku", "nunique"), brand_count=("brand", "nunique"),
        exclusive_sku_count=("retailer_count", lambda values: int((values == 1).sum())),
        common_sku_count=("retailer_count", lambda values: int((values > 1).sum()))).reset_index()
    totals = base.groupby(["month", "category1"])["sku"].nunique().rename("category_total_sku_count")
    out = out.merge(totals, on=["month", "category1"])
    out["category_coverage_pct"] = out.sku_count / out.category_total_sku_count
    return out[["month", "category1", "retailer", "sku_count", "brand_count", "category_total_sku_count",
                "exclusive_sku_count", "common_sku_count", "category_coverage_pct"]]


def price_index(fact: pd.DataFrame) -> pd.DataFrame:
    pieces = []
    levels = [("category1", ["category1"]), ("category2", ["category1", "category2"]),
              ("category3", ["category1", "category2", "category3"])]
    for level, keys in levels:
        for index_type, price in [("regular_price_index", "regular_price"), ("promo_price_index", "promo_price")]:
            sku_retailer = fact[["month", *keys, "sku", "retailer", price]].dropna(subset=[price]).groupby(
                ["month", *keys, "sku", "retailer"], as_index=False)[price].mean()
            counts = sku_retailer.groupby(["month", *keys, "sku"])["retailer"].nunique().rename("retailer_count")
            matched = sku_retailer.merge(counts, on=["month", *keys, "sku"])
            matched = matched[matched.retailer_count > 1].copy()
            market = matched.groupby(["month", *keys, "sku"])[price].mean().rename("market_price")
            matched = matched.merge(market, on=["month", *keys, "sku"])
            grouped = matched.groupby(["month", *keys, "retailer"]).agg(
                matched_sku_count=("sku", "nunique"), retailer_avg_price=(price, "mean"),
                market_avg_price=("market_price", "mean")).reset_index()
            grouped["price_index"] = grouped.retailer_avg_price / grouped.market_avg_price * 100
            grouped["category_level"] = level
            grouped["index_type"] = index_type
            for category in ["category1", "category2", "category3"]:
                if category not in grouped:
                    grouped[category] = "ALL"
            pieces.append(grouped)
    out = pd.concat(pieces, ignore_index=True)
    return out[["month", "category_level", "category1", "category2", "category3", "retailer", "index_type",
                "matched_sku_count", "retailer_avg_price", "market_avg_price", "price_index"]]


def promotion(fact: pd.DataFrame, indexes: pd.DataFrame) -> pd.DataFrame:
    pieces = []
    for level, keys in [("category1", ["category1"]), ("category2", ["category1", "category2"]),
                        ("category3", ["category1", "category2", "category3"])]:
        group_keys = ["month", *keys, "retailer"]
        sku = fact.groupby([*group_keys, "sku"], as_index=False).agg(
            promo_days=("is_promo", "sum"), month_days=("month_days", "max"),
            sku_avg_discount=("discount_pct", "mean"), sku_median_discount=("discount_pct", "median"))
        out = sku.groupby(group_keys).agg(total_sku_count=("sku", "nunique"),
            promo_sku_count=("promo_days", lambda values: int((values > 0).sum())),
            avg_promo_days=("promo_days", "mean"), month_days=("month_days", "max"),
            avg_discount_pct=("sku_avg_discount", "mean"),
            median_discount_pct=("sku_median_discount", "median")).reset_index()
        out["promo_sku_pct"] = out.promo_sku_count / out.total_sku_count
        out["promotion_frequency"] = out.avg_promo_days / out.month_days
        out["category_level"] = level
        for category in ["category1", "category2", "category3"]:
            if category not in out:
                out[category] = "ALL"
        promo_index = indexes[(indexes.category_level == level) & (indexes.index_type == "promo_price_index")][
            ["month", "category1", "category2", "category3", "retailer", "matched_sku_count", "price_index"]].rename(
                columns={"matched_sku_count": "promo_index_matched_sku_count", "price_index": "promo_price_index"})
        out = out.merge(promo_index, on=["month", "category1", "category2", "category3", "retailer"], how="left")
        pieces.append(out)
    result = pd.concat(pieces, ignore_index=True)
    return result[["month", "category_level", "category1", "category2", "category3", "retailer",
                   "total_sku_count", "promo_sku_count", "promo_sku_pct", "avg_promo_days", "month_days",
                   "promotion_frequency", "avg_discount_pct", "median_discount_pct",
                   "promo_index_matched_sku_count", "promo_price_index"]]


def positioning(part1: pd.DataFrame, part2: pd.DataFrame) -> pd.DataFrame:
    pivot = part2[part2.category_level.eq("category1")].pivot_table(
        index=["month", "category1", "retailer"], columns="index_type",
        values=["matched_sku_count", "price_index"], aggfunc="mean").reset_index()
    pivot.columns = ["_".join(value).rstrip("_") if isinstance(value, tuple) else value for value in pivot.columns]
    monthly = part1.merge(pivot, on=["month", "category1", "retailer"], how="left")
    monthly["year"] = monthly.month.str[:4].astype(int)
    return monthly.groupby(["year", "category1", "retailer"], as_index=False).agg(
        avg_sku_count=("sku_count", "mean"), avg_brand_count=("brand_count", "mean"),
        avg_category_coverage_pct=("category_coverage_pct", "mean"),
        avg_exclusive_sku_count=("exclusive_sku_count", "mean"), avg_common_sku_count=("common_sku_count", "mean"),
        matched_sku_count_promo_price_index=("matched_sku_count_promo_price_index", "mean"),
        matched_sku_count_regular_price_index=("matched_sku_count_regular_price_index", "mean"),
        price_index_promo_price_index=("price_index_promo_price_index", "mean"),
        price_index_regular_price_index=("price_index_regular_price_index", "mean"))


def build_tables(fact: pd.DataFrame) -> dict[str, pd.DataFrame]:
    part1 = assortment(fact)
    part2 = price_index(fact)
    part3 = promotion(fact, part2)
    catalog = fact.sort_values("data_date").drop_duplicates("sku", keep="last")[[
        "sku", "product_name", "brand", "category1", "category2", "category3"]]
    dates = pd.DataFrame({"Date": pd.date_range(fact.data_date.min(), fact.data_date.max())})
    dates["Year"] = dates.Date.dt.year; dates["MonthNo"] = dates.Date.dt.month
    dates["Month"] = dates.Date.dt.strftime("%Y-%m"); dates["MonthName"] = dates.Date.dt.strftime("%b")
    months = dates.drop_duplicates("Month")[["Month", "Year", "MonthNo", "MonthName"]].copy()
    months["MonthStart"] = pd.to_datetime(months.Month + "-01")
    months["YearMonthSort"] = months.Year * 100 + months.MonthNo
    months = months[["Month", "MonthStart", "Year", "MonthNo", "MonthName", "YearMonthSort"]]
    return {"dim_date": dates, "dim_month": months, "dim_sku_catalog": catalog,
            "fact_price_observations": fact, "part1_assortment": part1, "part2_price_index": part2,
            "part3_promotion_intensity": part3, "part4_retailer_positioning_matrix": positioning(part1, part2)}


def copy_and_patch_report() -> None:
    REPORT.mkdir(parents=True, exist_ok=True)
    for name in ["Dashboard.Report", "Dashboard.SemanticModel"]:
        target = REPORT / name
        if target.exists():
            shutil.rmtree(target)
        shutil.copytree(TEMPLATE / name, target)
    shutil.copy2(TEMPLATE / "Dashboard.pbip", REPORT / "Dashboard.pbip")
    expressions = REPORT / "Dashboard.SemanticModel" / "definition" / "expressions.tmdl"
    text = expressions.read_text(encoding="utf-8-sig")
    asset_path = str(ASSETS.resolve()).replace('"', '""')
    replacement = f'expression AssetsRoot = "{asset_path}"'
    text = re.sub(r'(?m)^expression AssetsRoot = ".*?"', lambda _: replacement, text)
    write_text(expressions, text)
    for path in (REPORT / "Dashboard.SemanticModel" / "definition").rglob("*.tmdl"):
        content = path.read_text(encoding="utf-8-sig")
        if "```" in content:
            write_text(path, content.replace("```", ""))
    ensure_requested_measures()
    normalize_report_layout()


def ensure_requested_measures() -> None:
    table_root = REPORT / "Dashboard.SemanticModel" / "definition" / "tables"
    additions = {
        "DimDate.tmdl": [
            ("Selected Month Count", "DISTINCTCOUNT ( DimDate[Month] )", "#,0"),
        ],
        "Part1Assortment.tmdl": [
            ("Retailer Count", "DISTINCTCOUNT ( Part1Assortment[retailer] )", "#,0"),
            ("SKU Count", "SUM ( Part1Assortment[sku_count] )", "#,0"),
            ("Brand Count", "SUM ( Part1Assortment[brand_count] )", "#,0"),
            ("Category Coverage %", "AVERAGE ( Part1Assortment[category_coverage_pct] )", "0.0%"),
            ("Exclusive SKU Count", "SUM ( Part1Assortment[exclusive_sku_count] )", "#,0"),
            ("Common SKU Count", "SUM ( Part1Assortment[common_sku_count] )", "#,0"),
            ("Coverage Gap %", "1 - [Category Coverage %]", "0.0%"),
        ],
    }
    for file_name, measures in additions.items():
        path = table_root / file_name
        content = path.read_text(encoding="utf-8-sig")
        insertion = []
        for name, expression, format_string in measures:
            pattern = rf"(?m)^[ \t]*measure[ \t]+(?:'{re.escape(name)}'|{re.escape(name)})[ \t]*="
            if re.search(pattern, content):
                continue
            insertion.append(f"\n\tmeasure '{name}' = {expression}\n\t\tformatString: {format_string}\n")
        if insertion:
            # Table scalar properties (for example lineageTag) must remain before
            # child objects. Inserting directly after `table ...` makes otherwise
            # valid table properties appear inside/after a measure and breaks TMDL.
            child = re.search(r"(?m)^(?=\t(?:measure|column|partition|hierarchy)\b)", content)
            offset = child.start() if child else len(content)
            write_text(path, content[:offset] + "".join(insertion) + content[offset:])


def validate_tmdl_structure() -> None:
    """Catch table-property ordering/indentation damage before Desktop is launched."""
    table_root = REPORT / "Dashboard.SemanticModel" / "definition" / "tables"
    issues = []
    child_pattern = re.compile(r"^\t(?:measure|column|partition|hierarchy)\b")
    table_property_pattern = re.compile(
        r"^\t(?:lineageTag|isHidden|isPrivate|dataCategory|description):"
    )
    for path in table_root.glob("*.tmdl"):
        child_seen = False
        for number, line in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), 1):
            if child_pattern.match(line):
                child_seen = True
            elif child_seen and table_property_pattern.match(line):
                issues.append(f"{path.name}:{number}: table property appears after a child object")
    if issues:
        raise ValueError("Invalid TMDL table structure:\n" + "\n".join(issues))


def normalize_report_layout() -> None:
    pages_root = REPORT / "Dashboard.Report" / "definition" / "pages"
    specs = {
        "1. Assortment": {"slicer_y": 72, "slicer_h": 72,
            "rows": {"cardVisual": [(24,160,400,96),(440,160,400,96),(856,160,400,96)],
                     "barChart": [(24,272,608,424)], "clusteredBarChart": [(648,272,608,424)]}},
        "2. Price Index": {"slicer_y": 72, "slicer_h": 72,
            "rows": {"tableEx": [(24,160,1232,160)],
                     "lineChart": [(24,336,608,360),(648,336,608,360)]}},
        "3. Promotion Intensity": {"slicer_y": 72, "slicer_h": 72,
            "rows": {"tableEx": [(24,160,1232,240)], "lineChart": [(24,416,1232,280)]}},
        "4. Retailer Positioning Matrix": {"slicer_y": 72, "slicer_h": 72,
            "rows": {"scatterChart": [(24,160,608,336),(648,160,608,336)],
                     "tableEx": [(24,512,1232,184)]}},
    }
    for page_dir in [path for path in pages_root.iterdir() if path.is_dir()]:
        page_doc = json.loads((page_dir / "page.json").read_text(encoding="utf-8-sig"))
        spec = specs.get(page_doc["displayName"])
        if not spec:
            continue
        visuals = []
        for visual_path in page_dir.rglob("visual.json"):
            doc = json.loads(visual_path.read_text(encoding="utf-8-sig"))
            visuals.append((visual_path, doc))
        slicers = sorted([(p,d) for p,d in visuals if d["visual"]["visualType"] == "slicer"],
                         key=lambda item: (item[1]["position"]["x"], item[1]["name"]))
        count = len(slicers)
        width = (1232 - (count - 1) * 16) / count
        for index, (path, doc) in enumerate(slicers):
            doc["position"].update({"x": 24 + index * (width + 16), "y": spec["slicer_y"],
                                    "width": width, "height": spec["slicer_h"], "z": index, "tabOrder": index})
            write_json(path, doc)
        tab_order = count
        for visual_type, positions in spec["rows"].items():
            matches = sorted([(p,d) for p,d in visuals if d["visual"]["visualType"] == visual_type],
                             key=lambda item: (item[1]["position"]["x"], item[1]["name"]))
            if len(matches) != len(positions):
                raise ValueError(f"{page_doc['displayName']}: expected {len(positions)} {visual_type}, found {len(matches)}")
            for (path, doc), (x,y,w,h) in zip(matches, positions):
                doc["position"].update({"x": x, "y": y, "width": w, "height": h,
                                        "z": tab_order, "tabOrder": tab_order})
                tab_order += 1
                write_json(path, doc)


def projection_binding(projection: dict) -> dict:
    field = projection["field"]
    if "Measure" in field:
        expression = field["Measure"]; kind = "measure"
    elif "Column" in field:
        expression = field["Column"]; kind = "column"
    else:
        expression = field["Aggregation"]["Expression"]["Column"]; kind = "aggregation"
    source = expression["Expression"]["SourceRef"]
    return {"role": "", "table": source.get("Entity", ""), "field": expression["Property"], "kind": kind}


def requirements_manifest() -> dict:
    model_root = REPORT / "Dashboard.SemanticModel" / "definition"
    measures = []
    for table_path in (model_root / "tables").glob("*.tmdl"):
        content = table_path.read_text(encoding="utf-8")
        for quoted, plain in re.findall(r"(?m)^\s*measure\s+(?:'([^']+)'|([^=\n]+?))\s*=", content):
            measures.append({"table": table_path.stem, "name": (quoted or plain).strip()})
    relationships = []
    relation_text = (model_root / "relationships.tmdl").read_text(encoding="utf-8")
    for block in re.split(r"(?m)(?=^relationship )", relation_text):
        refs = dict(re.findall(r"(?m)^\s*(fromColumn|toColumn):\s*([^\n]+)", block))
        if len(refs) != 2:
            continue
        from_table, from_column = refs["fromColumn"].strip().replace("'", "").rsplit(".", 1)
        to_table, to_column = refs["toColumn"].strip().replace("'", "").rsplit(".", 1)
        relationships.append({"fromTable": from_table, "fromColumn": from_column,
                              "toTable": to_table, "toColumn": to_column, "active": True,
                              "crossFilteringBehavior": "oneDirection"})
    visuals = []
    pages_root = REPORT / "Dashboard.Report" / "definition" / "pages"
    for page_dir in sorted(path for path in pages_root.iterdir() if path.is_dir()):
        page = json.loads((page_dir / "page.json").read_text(encoding="utf-8"))
        for visual_path in sorted(page_dir.rglob("visual.json")):
            doc = json.loads(visual_path.read_text(encoding="utf-8")); visual = doc.get("visual", {})
            bindings = []
            for role, state in visual.get("query", {}).get("queryState", {}).items():
                for projection in state.get("projections", []):
                    binding = projection_binding(projection); binding["role"] = role; bindings.append(binding)
            visuals.append({"page": page["displayName"], "visualId": doc["name"],
                            "visualType": visual.get("visualType"), "bindings": bindings})
    return {"measures": measures, "relationships": relationships, "visuals": visuals}


def write_docs(tables: dict[str, pd.DataFrame], profile: list[dict], requirements: dict) -> None:
    fact_dates = pd.to_datetime(tables["fact_price_observations"]["data_date"], errors="coerce")
    coverage_start = fact_dates.min().date()
    coverage_end = fact_dates.max().date()
    write_json(DOCS / "visual_requirements.json", requirements)
    write_text(BASE / "data_measures.dax", (TEMPLATE / "Dashboard.SemanticModel" / "DAXQueries" / "Query 1.dax").read_text(encoding="utf-8-sig"))
    shutil.copy2(TEMPLATE / "Dashboard.Report" / "StaticResources" / "RegisteredResources" /
                 "Retail_Price_Intelligence23104958600551417.json", BASE / "dashboard_theme.json")
    write_text(BASE / "page_layout_spec.md", "# Page layout specification\n\nThe copied Desktop-authored PBIR implements the four requested 1280×720 business pages with bound visuals.\n")
    lineage = "\n".join(f"| {item['file']} | {item['rows']:,} | `{item['sha256']}` |" for item in profile)
    write_text(DOCS / "build_manifest.md", f"""# Build manifest

- Mode: `full`
- Source template: `{TEMPLATE}`
- Output report: `{REPORT}`
- Normalized rows: {len(tables['fact_price_observations']):,}
- Date coverage: {coverage_start} to {coverage_end}
- Template source was copied and preserved.
- TMDL Markdown fence artifacts were removed in the output copy.
- Publication: disabled.

| Source | Rows | SHA-256 |
|---|---:|---|
{lineage}
""")
    rows = []
    for name, frame in tables.items():
        for column in frame.columns:
            rows.append(f"| {name} | {column} | {frame[column].dtype} | Generated reporting field |")
    write_text(DOCS / "data_dictionary.md", "# Data dictionary\n\n| Table | Column | Type | Meaning |\n|---|---|---|---|\n" + "\n".join(rows) + "\n")
    shutil.copy2(REPORT / "Dashboard.SemanticModel" / "definition" / "relationships.tmdl", DOCS / "model_relationships.tmdl")
    write_text(DOCS / "measure_list.md", "# Measure list\n\n" + "\n".join(
        f"- `{item['table']}[{item['name']}]`" for item in requirements["measures"]) + "\n")
    write_text(DOCS / "validation_report.md", f"""# Validation report

## Input and data

- Passed: {len(profile)} XLSX files with the required worksheet and schema.
- Passed: {len(tables['fact_price_observations']):,} normalized rows covering {coverage_start} to {coverage_end}.
- Warning: the request's historical 31-file acceptance baseline differs from the three files physically supplied.

## Output placement and PBIP integrity

- Passed: complete source `Dashboard.pbip`, `Dashboard.Report`, and `Dashboard.SemanticModel` copied to `output/report`.
- Passed: source template preserved.
- PBIX: not run pending Desktop save.

## Contract summary

- Requested/persisted measures: {len(requirements['measures'])}
- Persisted relationships: {len(requirements['relationships'])}
- PBIR visuals: {len(requirements['visuals'])}; visuals with semantic bindings: {sum(bool(v['bindings']) for v in requirements['visuals'])}
- Static, PBIR, contract, layout, and Desktop results are appended by the validation step.
""")


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True); ASSETS.mkdir(parents=True, exist_ok=True)
    fact, profile = load_fact()
    tables = build_tables(fact)
    for name, frame in tables.items():
        frame.to_csv(ASSETS / f"{name}.csv", index=False, encoding="utf-8")
    copy_and_patch_report()
    validate_tmdl_structure()
    requirements = requirements_manifest()
    write_docs(tables, profile, requirements)
    print(json.dumps({"rows": len(fact), "tables": {name: len(frame) for name, frame in tables.items()},
                      "measures": len(requirements["measures"]), "relationships": len(requirements["relationships"]),
                      "visuals": len(requirements["visuals"])}, indent=2))


if __name__ == "__main__":
    main()
