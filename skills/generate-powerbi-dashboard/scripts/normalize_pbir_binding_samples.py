#!/usr/bin/env python3
"""Extract schema-versioned PBIR role/query and formatting templates from Desktop-authored visuals."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
from collections import defaultdict
from pathlib import Path


DROP = object()


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def schema_version(uri: str) -> str:
    marker = "/visualContainer/"
    if marker not in uri or not uri.endswith("/schema.json"):
        raise ValueError(f"Unsupported visual-container schema URI: {uri}")
    return uri.split(marker, 1)[1].split("/", 1)[0]


def projection_kind(projection: dict) -> str:
    field = projection.get("field", {})
    if "Column" in field:
        return "column"
    if "Measure" in field:
        return "measure"
    if "Aggregation" in field:
        return "aggregation"
    return "unknown"


def normalize_projection(value):
    if isinstance(value, list):
        return [normalize_projection(item) for item in value]
    if not isinstance(value, dict):
        return value
    result = {}
    for key, child in value.items():
        if key == "Entity":
            result[key] = "{{TABLE}}"
        elif key == "Property":
            result[key] = "{{FIELD}}"
        elif key == "queryRef":
            result[key] = "{{QUERY_REF}}"
        elif key == "nativeQueryRef":
            result[key] = "{{NATIVE_QUERY_REF}}"
        elif key == "displayName":
            result[key] = "{{DISPLAY_NAME}}"
        elif key == "Function":
            result[key] = "{{AGGREGATION_FUNCTION}}"
        else:
            result[key] = normalize_projection(child)
    return result


def normalize_sort(value):
    if isinstance(value, list):
        return [normalize_sort(item) for item in value]
    if not isinstance(value, dict):
        return value
    result = {}
    for key, child in value.items():
        if key == "Entity":
            result[key] = "{{SORT_TABLE}}"
        elif key == "Property":
            result[key] = "{{SORT_FIELD}}"
        elif key == "Function":
            result[key] = "{{SORT_AGGREGATION_FUNCTION}}"
        else:
            result[key] = normalize_sort(child)
    return result


def normalize_format(value, replacements: dict[str, str], path: tuple[str, ...] = ()):
    if isinstance(value, list):
        return [normalized for item in value if (normalized := normalize_format(item, replacements, path)) is not DROP]
    if not isinstance(value, dict):
        if isinstance(value, str) and value in replacements:
            return replacements[value]
        return value
    result = {}
    for key, child in value.items():
        # Saved slicer selections and visual filters are business state, not formatting.
        if key == "filter":
            continue
        if key == "metadata":
            result[key] = replacements.get(str(child), "{{QUERY_REF}}")
            continue
        if key == "Value" and "text" in path:
            result[key] = "'{{TEXT}}'"
            continue
        result[key] = normalize_format(child, replacements, path + (key,))
    return result


def sample_score(doc: dict) -> tuple[int, int, int]:
    visual = doc.get("visual", {})
    query_state = visual.get("query", {}).get("queryState", {})
    projection_count = sum(len(role.get("projections", [])) for role in query_state.values())
    formatting = len(json.dumps(visual.get("objects", {}))) + len(json.dumps(visual.get("visualContainerObjects", {})))
    return len(query_state), projection_count, formatting


def build_asset(samples: list[tuple[Path, dict]]) -> dict:
    samples = sorted(samples, key=lambda item: (sample_score(item[1]), str(item[0])), reverse=True)
    source_path, representative = samples[0]
    visual = representative["visual"]
    roles: dict[str, dict] = {}
    role_observations = defaultdict(list)
    for _, doc in samples:
        for role, state in doc.get("visual", {}).get("query", {}).get("queryState", {}).items():
            role_observations[role].append(state.get("projections", []))
    for role in sorted(role_observations):
        templates = {}
        counts = []
        for projections in role_observations[role]:
            counts.append(len(projections))
            for projection in projections:
                kind = projection_kind(projection)
                templates.setdefault(kind, normalize_projection(copy.deepcopy(projection)))
        roles[role] = {
            "observedProjectionCount": {"min": min(counts), "max": max(counts)},
            "projectionTemplates": templates,
        }
    query = visual.get("query", {})
    format_replacements = {}
    for role, state in query.get("queryState", {}).items():
        for index, projection in enumerate(state.get("projections", [])):
            prefix = f"{{{{{role.upper()}_{index}"
            if projection.get("queryRef"):
                format_replacements[projection["queryRef"]] = prefix + "_QUERY_REF}}"
            if projection.get("nativeQueryRef"):
                format_replacements[projection["nativeQueryRef"]] = prefix + "_NATIVE_QUERY_REF}}"
            if projection.get("displayName"):
                format_replacements[projection["displayName"]] = prefix + "_DISPLAY_NAME}}"
    asset = {
        "$schema": "https://openai.local/schemas/pbir-binding-template/1.0/schema.json",
        "visualContainerSchema": representative["$schema"],
        "schemaVersion": schema_version(representative["$schema"]),
        "visualType": visual["visualType"],
        "source": {
            "kind": "Power BI Desktop-authored bound visual",
            "representativeSha256": hashlib.sha256(source_path.read_bytes()).hexdigest(),
            "sampleCount": len(samples),
        },
        "roles": roles,
        "queryExtras": {},
        "format": {},
        "defaults": {
            "drillFilterOtherVisuals": visual.get("drillFilterOtherVisuals", True)
        },
    }
    if "sortDefinition" in query:
        asset["queryExtras"]["sortDefinitionTemplate"] = normalize_sort(copy.deepcopy(query["sortDefinition"]))
    for key in ("objects", "visualContainerObjects"):
        if key in visual:
            asset["format"][key] = normalize_format(copy.deepcopy(visual[key]), format_replacements)
    return asset


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report-root", required=True, type=Path)
    parser.add_argument("--asset-root", required=True, type=Path)
    parser.add_argument("--registry", required=True, type=Path)
    parser.add_argument("--result", type=Path)
    args = parser.parse_args()

    samples_by_key = defaultdict(list)
    for path in sorted(args.report_root.rglob("visual.json")):
        doc = read_json(path)
        visual_type = doc.get("visual", {}).get("visualType")
        query_state = doc.get("visual", {}).get("query", {}).get("queryState")
        if not visual_type or not query_state:
            continue
        samples_by_key[(schema_version(doc["$schema"]), visual_type)].append((path, doc))

    registry = read_json(args.registry)
    generated = []
    registry_types = {entry["visualType"]: entry for entry in registry.get("visualTypes", [])}
    for (version, visual_type), samples in sorted(samples_by_key.items()):
        version_root = args.asset_root / f"visual-container-{version}"
        relative = Path("bindings") / f"{visual_type}.binding.json"
        asset = build_asset(samples)
        write_json(version_root / relative, asset)
        if version == registry["schemaVersion"] and visual_type not in registry_types:
            visual_relative = Path("visual-types") / f"{visual_type}.visual.json"
            write_json(version_root / visual_relative, {
                "$schema": asset["visualContainerSchema"],
                "visual": {
                    "visualType": visual_type,
                    "drillFilterOtherVisuals": asset["defaults"]["drillFilterOtherVisuals"],
                },
            })
            entry = {
                "visualType": visual_type,
                "sampleName": visual_type,
                "aliases": [visual_type],
                "asset": visual_relative.as_posix(),
            }
            registry.setdefault("visualTypes", []).append(entry)
            registry_types[visual_type] = entry
        generated.append({
            "schemaVersion": version,
            "visualType": visual_type,
            "asset": relative.as_posix(),
            "roles": sorted(asset["roles"]),
            "sampleCount": len(samples),
        })

    by_type = {item["visualType"]: item for item in generated if item["schemaVersion"] == registry["schemaVersion"]}
    for entry in registry.get("visualTypes", []):
        binding = by_type.get(entry["visualType"])
        if binding:
            entry["bindingStatus"] = "available"
            entry["bindingAsset"] = binding["asset"]
            entry["boundRoles"] = binding["roles"]
            entry["bindingSourceCount"] = binding["sampleCount"]
        else:
            entry["bindingStatus"] = "unavailable"
            entry.pop("bindingAsset", None)
            entry.pop("boundRoles", None)
            entry.pop("bindingSourceCount", None)
    registry["visualTypes"] = sorted(registry.get("visualTypes", []), key=lambda item: item["visualType"])
    sources = registry.setdefault("generatedFrom", [])
    marker = "Desktop-authored bound visuals from help/template"
    if marker not in sources:
        sources.append(marker)
    write_json(args.registry, registry)

    result = {
        "status": "Passed",
        "sourceReportName": args.report_root.name,
        "generatedBindingAssets": generated,
        "typesWithBindings": len(generated),
    }
    if args.result:
        write_json(args.result, result)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
