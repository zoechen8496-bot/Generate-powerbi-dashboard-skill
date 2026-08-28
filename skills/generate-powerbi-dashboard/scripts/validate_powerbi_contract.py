#!/usr/bin/env python3
"""Validate requested TMDL measures/relationships and PBIR field bindings."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


def norm(value: str) -> str:
    return re.sub(r"[\s'\[\]]+", "", value or "").casefold()


def all_strings(value):
    if isinstance(value, dict):
        for key, child in value.items():
            yield str(key)
            yield from all_strings(child)
    elif isinstance(value, list):
        for child in value:
            yield from all_strings(child)
    elif isinstance(value, (str, int, float, bool)):
        yield str(value)


def tmdl_text(root: Path) -> str:
    return "\n".join(p.read_text(encoding="utf-8-sig") for p in root.rglob("*.tmdl"))


def tmdl_structure_issues(root: Path) -> list[dict]:
    """Detect table scalar properties incorrectly emitted after child objects."""
    issues = []
    child_pattern = re.compile(r"^\t(?:measure|column|partition|hierarchy)\b")
    table_property_pattern = re.compile(
        r"^\t(?:lineageTag|isHidden|isPrivate|dataCategory|description):"
    )
    for path in root.rglob("tables/*.tmdl"):
        child_seen = False
        for line_number, line in enumerate(
            path.read_text(encoding="utf-8-sig").splitlines(), 1
        ):
            if child_pattern.match(line):
                child_seen = True
            elif child_seen and table_property_pattern.match(line):
                issues.append({
                    "code": "TMDL_TABLE_PROPERTY_AFTER_CHILD",
                    "path": str(path),
                    "line": line_number,
                    "content": line.strip(),
                })
    return issues


def measure_names(text: str, table: str) -> set[str]:
    blocks = re.split(r"(?m)^table\s+", text)
    for block in blocks[1:]:
        if norm(block.splitlines()[0]) == norm(table):
            return {norm(a or b) for a, b in re.findall(r"(?m)^\s*measure\s+(?:'([^']+)'|([^=\n]+?))\s*=", block)}
    return set()


def column_names(text: str, table: str) -> set[str]:
    blocks = re.split(r"(?m)^table\s+", text)
    for block in blocks[1:]:
        if norm(block.splitlines()[0]) == norm(table):
            return {norm(a or b) for a, b in re.findall(r"(?m)^\s*column\s+(?:'([^']+)'|([^\n]+?))\s*$", block)}
    return set()


def relationship_blocks(text: str) -> list[str]:
    starts = list(re.finditer(r"(?m)^relationship\s+[^\n]+", text))
    result = []
    for index, match in enumerate(starts):
        end = starts[index + 1].start() if index + 1 < len(starts) else len(text)
        result.append(text[match.start():end])
    return result


def has_relationship(text: str, req: dict) -> bool:
    expected = [norm(req[k]) for k in ("fromTable", "fromColumn", "toTable", "toColumn")]
    for block in relationship_blocks(text):
        values = dict(re.findall(r"(?m)^\s*(fromColumn|toColumn):\s*(.+?)\s*$", block))
        if "fromColumn" not in values or "toColumn" not in values:
            continue
        def split_ref(value):
            clean = value.strip().replace("'", "")
            if "." not in clean:
                return "", clean
            return clean.rsplit(".", 1)
        actual = [*split_ref(values["fromColumn"]), *split_ref(values["toColumn"])]
        if [norm(x) for x in actual] == expected:
            props = {k: v.strip() for k, v in re.findall(r"(?m)^\s*(isActive|crossFilteringBehavior|fromCardinality|toCardinality):\s*(.+?)\s*$", block)}
            actual_active = props.get("isActive", "true").casefold() == "true"
            if "active" in req and actual_active != bool(req["active"]):
                continue
            actual_filter = props.get("crossFilteringBehavior", "oneDirection")
            if req.get("crossFilteringBehavior") and norm(actual_filter) != norm(req["crossFilteringBehavior"]):
                continue
            if req.get("fromCardinality") and norm(props.get("fromCardinality", "many")) != norm(req["fromCardinality"]):
                continue
            if req.get("toCardinality") and norm(props.get("toCardinality", "one")) != norm(req["toCardinality"]):
                continue
            return True
    return False


def visual_files(report_root: Path) -> dict[str, tuple[Path, dict, str]]:
    found = {}
    for path in report_root.rglob("visual.json"):
        doc = json.loads(path.read_text(encoding="utf-8-sig"))
        page_path = path.parents[2] / "page.json"
        page_name = ""
        if page_path.exists():
            page_doc = json.loads(page_path.read_text(encoding="utf-8-sig"))
            page_name = str(page_doc.get("displayName") or page_doc.get("name") or "")
        found[str(doc.get("name", path.parent.name))] = (path, doc, page_name)
    return found


def binding_present(doc: dict, binding: dict) -> tuple[bool, str]:
    visual = doc.get("visual", {})
    query = visual.get("query") or doc.get("query")
    if not query:
        return False, "visual has no semantic query"
    query_state = query.get("queryState", {}) if isinstance(query, dict) else {}
    role = binding["role"]
    role_node = next((v for k, v in query_state.items() if norm(k) == norm(role)), None)
    if role_node is None:
        return False, f"queryState role '{role}' is missing"
    role_blob = "|".join(norm(s) for s in all_strings(role_node))
    field = norm(binding["field"])
    table = norm(binding["table"])
    full = norm(f"{binding['table']}.{binding['field']}")
    whole_blob = "|".join(norm(s) for s in all_strings(doc))
    if field not in role_blob and full not in role_blob:
        return False, f"role '{role}' does not project {binding['table']}.{binding['field']}"
    if table not in whole_blob and full not in whole_blob:
        return False, f"semantic query does not resolve table '{binding['table']}'"
    if norm(binding.get("kind", "")) not in role_blob:
        return False, f"role '{role}' does not contain a {binding.get('kind')} expression"
    return True, ""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report-root", required=True, type=Path)
    parser.add_argument("--semantic-model-root", required=True, type=Path)
    parser.add_argument("--requirements", required=True, type=Path)
    parser.add_argument("--result", type=Path)
    args = parser.parse_args()
    requirements = json.loads(args.requirements.read_text(encoding="utf-8-sig"))
    text = tmdl_text(args.semantic_model_root)
    issues = tmdl_structure_issues(args.semantic_model_root)
    for item in requirements.get("measures", []):
        if norm(item["name"]) not in measure_names(text, item["table"]):
            issues.append({"code":"TMDL_MEASURE_MISSING", "item":item})
    for item in requirements.get("relationships", []):
        if not has_relationship(text, item):
            issues.append({"code":"TMDL_RELATIONSHIP_MISSING", "item":item})
    visuals = visual_files(args.report_root)
    for item in requirements.get("visuals", []):
        found = visuals.get(item["visualId"])
        if not found:
            issues.append({"code":"PBIR_VISUAL_MISSING", "item":item}); continue
        path, doc, page_name = found
        if norm(page_name) != norm(item["page"]):
            issues.append({"code":"PBIR_VISUAL_PAGE_MISMATCH", "path":str(path), "expected":item["page"], "actual":page_name})
        actual_type = doc.get("visual", {}).get("visualType")
        if actual_type != item["visualType"]:
            issues.append({"code":"PBIR_VISUAL_TYPE_MISMATCH", "path":str(path), "expected":item["visualType"], "actual":actual_type})
        for binding in item.get("bindings", []):
            available = measure_names(text, binding["table"]) if binding.get("kind") == "measure" else column_names(text, binding["table"])
            if norm(binding["field"]) not in available:
                issues.append({"code":"TMDL_BOUND_FIELD_MISSING", "path":str(path), "binding":binding})
            ok, message = binding_present(doc, binding)
            if not ok:
                issues.append({"code":"PBIR_FIELD_MAPPING_MISSING", "path":str(path), "binding":binding, "message":message})
    result = {"status":"Passed" if not issues else "Failed", "errors":len(issues), "issues":issues}
    payload = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.result:
        args.result.parent.mkdir(parents=True, exist_ok=True)
        args.result.write_text(payload, encoding="utf-8")
    print(payload, end="")
    return 0 if not issues else 1


if __name__ == "__main__":
    sys.exit(main())
