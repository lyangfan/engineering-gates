#!/usr/bin/env python3
"""Independent engineering gates CLI.

The CLI is intentionally small and deterministic. It validates identities and
boundaries, runs only explicit local argv, and never declares a formal
Engineering PASS.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import signal
import subprocess
import sys
from pathlib import Path, PurePosixPath
from typing import Any

from decision_coverage import CoverageError, assert_complete
from digest_table import (
    IdentityError,
    git_head,
    git_path_status,
    is_sha256,
    read_json,
    require_sha256,
    sha256_file,
    write_json_no_clobber,
)


SCHEMA_CONTRACT = "agent-gates.eng-contract/v1"
SCHEMA_MANIFEST = "agent-gates.eng-manifest/v1"
SCHEMA_REVIEW = "agent-gates.eng-review/v1"
SCHEMA_RECEIPT = "agent-gates.eng-receipt/v1"
ROLES = {"authority", "candidate", "dependency", "product", "evidence"}
SEVERITIES = {"BLOCKER", "MAJOR", "MINOR", "OPINION"}
BLOCKING_SEVERITIES = {"BLOCKER", "MAJOR"}
VALID_VERDICTS = {"PASS", "NEEDS_USER_DECISION", "NON_CONVERGENT", "BLOCKED", "REJECT"}
HEX40 = re.compile(r"^[0-9a-fA-F]{40}$")
HEX64 = re.compile(r"^[0-9a-fA-F]{64}$")


class GateError(ValueError):
    """A user-facing validation or execution error."""


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def require_dict(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise GateError("%s must be an object" % label)
    return value


def require_list(value: Any, label: str) -> list[Any]:
    if not isinstance(value, list):
        raise GateError("%s must be an array" % label)
    return value


def require_string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise GateError("%s must be a non-empty string" % label)
    return value


def require_keys(value: dict[str, Any], required: set[str], allowed: set[str], label: str) -> None:
    missing = sorted(required - set(value))
    unknown = sorted(set(value) - allowed)
    if missing:
        raise GateError("%s missing fields: %s" % (label, ", ".join(missing)))
    if unknown:
        raise GateError("%s has unknown fields: %s" % (label, ", ".join(unknown)))


def relative_path(value: Any, label: str, forbidden: set[str] | None = None) -> str:
    value = require_string(value, label)
    if "\x00" in value or "\\" in value:
        raise GateError("%s must use a relative POSIX path" % label)
    if value.startswith("/") or re.match(r"^[A-Za-z]:", value):
        raise GateError("%s must be relative" % label)
    if value == ".":
        return "."
    parts = PurePosixPath(value).parts
    if not parts or any(part in {"..", ""} for part in parts):
        raise GateError("%s must be relative and cannot contain .. or empty components" % label)
    blocked = {".git"} | (forbidden or set())
    if any(part in blocked for part in parts):
        raise GateError("%s enters a forbidden path" % label)
    return PurePosixPath(*parts).as_posix()


def project_path(root: Path, value: Any, label: str, forbidden: set[str] | None = None) -> Path:
    rel = relative_path(value, label, forbidden)
    base = root.resolve()
    candidate = (base / rel).resolve(strict=False)
    try:
        candidate.relative_to(base)
    except ValueError as exc:
        raise GateError("%s escapes project root" % label) from exc
    return candidate


def path_is_under(path: Path, root: Path) -> bool:
    try:
        path.resolve(strict=False).relative_to(root.resolve())
    except ValueError:
        return False
    return True


def check_write_target(root: Path, value: str | Path, write_roots: list[str], label: str) -> Path:
    if isinstance(value, Path):
        raw = value
        if raw.is_absolute():
            target = raw.resolve(strict=False)
            try:
                rel = target.relative_to(root.resolve()).as_posix()
            except ValueError as exc:
                raise GateError("%s is outside project root" % label) from exc
        else:
            rel = value.as_posix()
    else:
        raw = Path(value)
        rel = raw.resolve(strict=False).relative_to(root.resolve()).as_posix() if raw.is_absolute() and path_is_under(raw, root) else str(value)
    target = project_path(root, rel, label)
    allowed = False
    for write_root in write_roots:
        wr = project_path(root, write_root, "write_roots")
        if path_is_under(target, wr) or target == wr:
            allowed = True
            break
    if not allowed:
        raise GateError("%s is outside declared write_roots" % label)
    return target


def verify_digest(path: Path, expected: str, label: str) -> str:
    expected = require_sha256(expected, label)
    if not path.is_file():
        raise GateError("%s does not exist as a file: %s" % (label, path))
    actual = sha256_file(path)
    if actual != expected:
        raise GateError("%s mismatch: expected %s, got %s" % (label, expected, actual))
    return actual


def validate_forbidden_and_roots(root: Path, write_roots: Any, forbidden_paths: Any, label: str) -> tuple[list[str], set[str]]:
    roots = require_list(write_roots, label + ".write_roots")
    if not roots:
        raise GateError(label + ".write_roots cannot be empty")
    forbidden_values = require_list(forbidden_paths, label + ".forbidden_paths")
    forbidden: set[str] = set()
    for item in forbidden_values:
        # A forbidden list is allowed to name .git itself; it is the one
        # place where the reserved component is intentionally declared.
        value = require_string(item, label + ".forbidden_paths item")
        if "\x00" in value or "\\" in value or value.startswith("/") or re.match(r"^[A-Za-z]:", value):
            raise GateError(label + ".forbidden_paths item must be relative")
        parts = PurePosixPath(value).parts
        if not parts or any(part in {"..", ""} for part in parts):
            raise GateError(label + ".forbidden_paths item cannot contain ..")
        normalized = PurePosixPath(*parts).as_posix()
        forbidden.add(PurePosixPath(normalized).parts[-1])
    normalized_roots = [relative_path(item, label + ".write_roots item", forbidden) for item in roots]
    for item in normalized_roots:
        project_path(root, item, label + ".write_roots item", forbidden)
    return normalized_roots, forbidden


def validate_authority(root: Path, authority: Any, forbidden: set[str]) -> None:
    authority = require_dict(authority, "contract.authority")
    require_keys(authority, {"path", "sha256"}, {"path", "sha256"}, "contract.authority")
    path = project_path(root, authority["path"], "contract.authority.path", forbidden)
    verify_digest(path, authority["sha256"], "contract.authority.sha256")


def validate_contract(contract: dict[str, Any], root: Path) -> tuple[list[str], set[str]]:
    require_keys(
        contract,
        {"schema", "chain", "gate", "version", "authority", "requirements", "allowed_hosts", "write_roots", "forbidden_paths", "actors"},
        {"schema", "chain", "gate", "version", "authority", "requirements", "allowed_hosts", "write_roots", "forbidden_paths", "actors"},
        "contract",
    )
    if contract["schema"] != SCHEMA_CONTRACT:
        raise GateError("unsupported contract schema")
    chain = require_string(contract["chain"], "contract.chain")
    if "/" in chain or "\\" in chain or chain in {".", ".."}:
        raise GateError("contract.chain must be a simple identifier")
    if contract["gate"] not in {"A", "B"}:
        raise GateError("contract.gate must be A or B")
    require_string(contract["version"], "contract.version")
    allowed_hosts = require_list(contract["allowed_hosts"], "contract.allowed_hosts")
    if not allowed_hosts or any(host != "local" for host in allowed_hosts):
        raise GateError("only the local host is supported in v1")
    roots, forbidden = validate_forbidden_and_roots(
        root, contract["write_roots"], contract["forbidden_paths"], "contract"
    )
    validate_authority(root, contract["authority"], forbidden)
    actors = require_dict(contract["actors"], "contract.actors")
    require_keys(
        actors,
        {"decision_owner", "coordinator", "implementer", "reviewer"},
        {"decision_owner", "coordinator", "implementer", "reviewer"},
        "contract.actors",
    )
    for key, value in actors.items():
        require_string(value, "contract.actors.%s" % key)
    requirements = require_list(contract["requirements"], "contract.requirements")
    seen: set[str] = set()
    for index, item in enumerate(requirements):
        item = require_dict(item, "contract.requirements[%d]" % index)
        require_keys(
            item,
            {"id", "title", "acceptance", "status"},
            {"id", "title", "acceptance", "status"},
            "contract.requirements[%d]" % index,
        )
        rid = require_string(item["id"], "requirement id")
        if rid in seen:
            raise GateError("duplicate requirement id: %s" % rid)
        seen.add(rid)
        require_string(item["title"], "requirement title")
        require_string(item["acceptance"], "requirement acceptance")
        if item["status"] != "required":
            raise GateError("requirement %s must have status required" % rid)
    try:
        assert_complete(requirements, contract["gate"])
    except CoverageError as exc:
        raise GateError("contract requirement coverage: %s" % exc) from exc
    return roots, forbidden


def validate_object(root: Path, item: dict[str, Any], index: int, forbidden: set[str]) -> None:
    label = "manifest.objects[%d]" % index
    require_keys(
        item,
        {"id", "role", "path", "sha256", "source", "preservation", "scope"},
        {"id", "role", "path", "sha256", "source", "preservation", "scope"},
        label,
    )
    require_string(item["id"], label + ".id")
    if item["role"] not in ROLES:
        raise GateError("%s.role is not a permitted object role" % label)
    path = project_path(root, item["path"], label + ".path", forbidden)
    sha = require_sha256(item["sha256"], label + ".sha256")
    require_string(item["source"], label + ".source")
    require_string(item["preservation"], label + ".preservation")
    require_string(item["scope"], label + ".scope")
    if path.exists():
        if path.is_symlink():
            raise GateError("%s.path cannot be a symlink" % label)
        if path.is_file() and sha256_file(path) != sha:
            raise GateError("%s.path digest does not match sha256" % label)
    elif item["role"] not in {"candidate", "product"}:
        raise GateError("%s.path is missing" % label)
    source = item["source"]
    if item["preservation"] == "git" or source.startswith("git:"):
        if not source.startswith("git:"):
            raise GateError("%s git preservation needs a git: source" % label)
        token = source[4:]
        if not token:
            raise GateError("%s git source is empty" % label)
        status = git_path_status(root, item["path"])
        if status.strip():
            raise GateError("%s is dirty or untracked in git: %s" % (label, status.strip()))
        if HEX40.fullmatch(token):
            head = git_head(root)
            if head != token.lower():
                raise GateError("%s is not at fixed commit %s" % (label, token))
    if item["preservation"] not in {"git", "external", "inline", "workspace"}:
        raise GateError("%s has unknown preservation policy" % label)


def validate_manifest(manifest: dict[str, Any], manifest_path: Path, root: Path) -> tuple[dict[str, Any], dict[str, Any], list[str], set[str]]:
    require_keys(
        manifest,
        {"schema", "chain", "gate", "stage", "contract", "objects", "steps", "acceptance", "write_roots", "forbidden_paths"},
        {"schema", "chain", "gate", "stage", "contract", "objects", "steps", "acceptance", "write_roots", "forbidden_paths", "closure_findings"},
        "manifest",
    )
    if manifest["schema"] != SCHEMA_MANIFEST:
        raise GateError("unsupported manifest schema")
    require_string(manifest["chain"], "manifest.chain")
    if manifest["gate"] not in {"A", "B"}:
        raise GateError("manifest.gate must be A or B")
    if manifest["stage"] not in {"baseline", "closure"}:
        raise GateError("manifest.stage must be baseline or closure")
    roots, forbidden = validate_forbidden_and_roots(
        root, manifest["write_roots"], manifest["forbidden_paths"], "manifest"
    )
    contract_ref = require_dict(manifest["contract"], "manifest.contract")
    require_keys(contract_ref, {"path", "sha256"}, {"path", "sha256"}, "manifest.contract")
    contract_path = project_path(root, contract_ref["path"], "manifest.contract.path", forbidden)
    verify_digest(contract_path, contract_ref["sha256"], "manifest.contract.sha256")
    contract = read_json(contract_path)
    contract_roots, contract_forbidden = validate_contract(contract, root)
    if contract["chain"] != manifest["chain"] or contract["gate"] != manifest["gate"]:
        raise GateError("manifest and contract chain/gate do not agree")
    forbidden |= contract_forbidden
    if set(roots) != set(contract_roots):
        raise GateError("manifest and contract write_roots do not agree")
    objects = require_list(manifest["objects"], "manifest.objects")
    object_map: dict[str, dict[str, Any]] = {}
    for index, raw in enumerate(objects):
        item = require_dict(raw, "manifest.objects[%d]" % index)
        validate_object(root, item, index, forbidden)
        if item["id"] in object_map:
            raise GateError("duplicate object id: %s" % item["id"])
        object_map[item["id"]] = item
    steps = require_list(manifest["steps"], "manifest.steps")
    step_ids: set[str] = set()
    for index, raw in enumerate(steps):
        item = require_dict(raw, "manifest.steps[%d]" % index)
        allowed = {"id", "argv", "cwd", "host", "inputs", "outputs", "timeout_seconds"}
        require_keys(item, {"id", "argv", "cwd", "host", "inputs", "outputs"}, allowed, "manifest.steps[%d]" % index)
        sid = require_string(item["id"], "step id")
        if sid in step_ids:
            raise GateError("duplicate step id: %s" % sid)
        step_ids.add(sid)
        argv = require_list(item["argv"], "step argv")
        if not argv or any(not isinstance(arg, str) or not arg for arg in argv):
            raise GateError("step argv must be a non-empty string array")
        if item["host"] != "local":
            raise GateError("only local step hosts are supported")
        project_path(root, item["cwd"], "step cwd", forbidden)
        if not (root / item["cwd"]).is_dir():
            raise GateError("step cwd does not exist: %s" % item["cwd"])
        for field in ("inputs", "outputs"):
            refs = require_list(item[field], "step " + field)
            if any(ref not in object_map for ref in refs):
                raise GateError("step %s references an unknown object" % field)
        if "timeout_seconds" in item:
            timeout = item["timeout_seconds"]
            if not isinstance(timeout, (int, float)) or timeout <= 0:
                raise GateError("timeout_seconds must be positive")
    acceptance = require_list(manifest["acceptance"], "manifest.acceptance")
    acceptance_ids: set[str] = set()
    requirement_ids = {item["id"] for item in contract["requirements"]}
    for index, raw in enumerate(acceptance):
        item = require_dict(raw, "manifest.acceptance[%d]" % index)
        require_keys(
            item,
            {"id", "status", "evidence"},
            {"id", "status", "evidence", "reason"},
            "manifest.acceptance[%d]" % index,
        )
        rid = require_string(item["id"], "acceptance id")
        if rid in acceptance_ids:
            raise GateError("duplicate acceptance id: %s" % rid)
        if rid not in requirement_ids:
            raise GateError("acceptance id is not in contract: %s" % rid)
        acceptance_ids.add(rid)
        if item["status"] not in {"evidenced", "not_applicable", "deferred", "blocked"}:
            raise GateError("invalid acceptance status: %s" % item["status"])
        evidence = require_list(item["evidence"], "acceptance evidence")
        if any(not isinstance(ref, str) or ref not in object_map for ref in evidence):
            raise GateError("acceptance evidence must reference known objects")
        if item["status"] == "evidenced" and not evidence:
            raise GateError("evidenced acceptance cannot have empty evidence")
        if item["status"] in {"not_applicable", "deferred", "blocked"}:
            require_string(item.get("reason"), "acceptance reason")
    if manifest["stage"] == "baseline" and acceptance_ids != requirement_ids:
        raise GateError("baseline acceptance must cover every contract requirement")
    if manifest["stage"] == "closure":
        closure = require_list(manifest.get("closure_findings"), "manifest.closure_findings")
        if not closure:
            raise GateError("closure requires closure_findings")
        if any(not isinstance(item, str) or not item for item in closure):
            raise GateError("closure_findings must be non-empty strings")
    return manifest, contract, roots, forbidden


def load_context(manifest_path: Path, root_arg: Path | None) -> tuple[dict[str, Any], dict[str, Any], Path, list[str], set[str]]:
    manifest_path = manifest_path.resolve()
    root = (root_arg.resolve() if root_arg else manifest_path.parent.resolve())
    if not manifest_path.is_file():
        raise GateError("manifest does not exist: %s" % manifest_path)
    if not path_is_under(manifest_path, root):
        raise GateError("manifest must be within project root")
    manifest = read_json(manifest_path)
    manifest, contract, roots, forbidden = validate_manifest(manifest, manifest_path, root)
    return manifest, contract, root, roots, forbidden


def write_text_no_clobber(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() or path.is_symlink():
        raise GateError("refusing to overwrite existing path: %s" % path)
    with path.open("x", encoding="utf-8") as handle:
        handle.write(content)


def render_dispatch(
    manifest_path: Path,
    manifest: dict[str, Any],
    contract: dict[str, Any],
    root: Path,
    output: Path,
) -> None:
    contract_path = project_path(root, manifest["contract"]["path"], "manifest.contract.path")
    lines = [
        "# Engineering Gate dispatch",
        "",
        "This is neutral reviewer material generated from frozen JSON inputs.",
        "",
        "## Identity",
        "",
        "- schema: %s" % manifest["schema"],
        "- chain: %s" % manifest["chain"],
        "- gate: %s" % manifest["gate"],
        "- stage: %s" % manifest["stage"],
        "- manifest: %s" % sha256_file(manifest_path),
        "- contract: %s" % sha256_file(contract_path),
        "",
        "## Reviewer role",
        "",
        "Review the listed requirements and evidence. Do not infer missing semantics and do not treat this dispatch as a PASS.",
        "",
        "## Requirements",
        "",
    ]
    for item in contract["requirements"]:
        lines.append("- %s: %s — acceptance: %s" % (item["id"], item["title"], item["acceptance"]))
    lines.extend(["", "## Objects", ""])
    for item in manifest["objects"]:
        lines.append("- %s [%s] %s — sha256 %s — source %s — preservation %s — scope %s" % (
            item["id"], item["role"], item["path"], item["sha256"], item["source"],
            item["preservation"], item["scope"],
        ))
    lines.extend(["", "## Steps", ""])
    for item in manifest["steps"]:
        lines.append("- %s: argv=%s; cwd=%s; host=%s; outputs=%s" % (
            item["id"], json.dumps(item["argv"], ensure_ascii=False),
            item["cwd"], item["host"], ", ".join(item["outputs"]) or "(none)",
        ))
    lines.extend([
        "",
        "## Boundaries",
        "",
        "- declared write roots: %s" % ", ".join(manifest["write_roots"]),
        "- forbidden paths: %s" % ", ".join(manifest["forbidden_paths"]),
        "- CLI result: reviewer must create an eng-review JSON; this file does not create Engineering PASS.",
        "",
    ])
    write_text_no_clobber(output, "\n".join(lines))


def review_validation(
    review: dict[str, Any],
    review_path: Path,
    manifest_path: Path,
    manifest: dict[str, Any],
    root: Path,
) -> tuple[dict[str, Any], list[str]]:
    require_keys(
        review,
        {"schema", "chain", "gate", "stage", "manifest", "contract_sha256", "reviewer_id", "verdict", "checks", "findings", "scope"},
        {"schema", "chain", "gate", "stage", "manifest", "contract_sha256", "reviewer_id", "verdict", "checks", "findings", "scope", "budget"},
        "review",
    )
    if review["schema"] != SCHEMA_REVIEW:
        raise GateError("unsupported review schema")
    if review["chain"] != manifest["chain"] or review["gate"] != manifest["gate"]:
        raise GateError("review and manifest chain/gate do not agree")
    if review["stage"] != manifest["stage"]:
        raise GateError("review and manifest stage do not agree")
    require_string(review["reviewer_id"], "review.reviewer_id")
    if review["verdict"] not in VALID_VERDICTS:
        raise GateError("invalid review verdict")
    manifest_ref = require_dict(review["manifest"], "review.manifest")
    require_keys(manifest_ref, {"path", "sha256"}, {"path", "sha256"}, "review.manifest")
    review_manifest_path = project_path(root, manifest_ref["path"], "review.manifest.path")
    if review_manifest_path != manifest_path.resolve():
        raise GateError("review.manifest.path does not identify the command manifest")
    verify_digest(review_manifest_path, manifest_ref["sha256"], "review.manifest.sha256")
    require_sha256(review["contract_sha256"], "review.contract_sha256")
    if review["contract_sha256"] != sha256_file(project_path(root, manifest["contract"]["path"], "manifest.contract.path")):
        raise GateError("review contract_sha256 does not match manifest contract")
    checks = require_list(review["checks"], "review.checks")
    accepted_ids = {item["id"] for item in manifest["acceptance"]}
    check_ids: set[str] = set()
    for index, raw in enumerate(checks):
        item = require_dict(raw, "review.checks[%d]" % index)
        require_keys(item, {"id", "status", "evidence"}, {"id", "status", "evidence", "note"}, "review.check")
        cid = require_string(item["id"], "review check id")
        if cid in check_ids:
            raise GateError("duplicate review check id: %s" % cid)
        if cid not in accepted_ids:
            raise GateError("review check id is not in manifest acceptance: %s" % cid)
        check_ids.add(cid)
        if item["status"] not in {"PASS", "FAIL", "NA", "DEFERRED", "NEEDS_USER_DECISION"}:
            raise GateError("invalid review check status")
        evidence = require_list(item["evidence"], "review check evidence")
        if any(not isinstance(ref, str) or not ref for ref in evidence):
            raise GateError("review check evidence references must be strings")
    if manifest["stage"] == "baseline" and check_ids != accepted_ids:
        raise GateError("baseline review checks must cover every acceptance")
    findings = require_list(review["findings"], "review.findings")
    blocking: list[str] = []
    finding_ids: set[str] = set()
    for index, raw in enumerate(findings):
        item = require_dict(raw, "review.findings[%d]" % index)
        require_keys(
            item,
            {"id", "severity", "status", "owner", "message"},
            {"id", "severity", "status", "owner", "message"},
            "review.finding",
        )
        fid = require_string(item["id"], "finding id")
        if fid in finding_ids:
            raise GateError("duplicate finding id: %s" % fid)
        finding_ids.add(fid)
        if item["severity"] not in SEVERITIES:
            raise GateError("invalid finding severity")
        if item["status"] not in {"OPEN", "RESOLVED", "ACCEPTED", "CLOSED"}:
            raise GateError("invalid finding status")
        require_string(item["owner"], "finding owner")
        require_string(item["message"], "finding message")
        if item["severity"] in BLOCKING_SEVERITIES and item["status"] not in {"RESOLVED", "CLOSED"}:
            blocking.append(fid)
    return review, blocking


def validate_receipt(receipt: dict[str, Any], root: Path, attempt: Path) -> None:
    """Validate a generated receipt and its byte-level evidence bindings."""
    require_keys(
        receipt,
        {
            "schema", "step_id", "attempt_dir", "argv", "cwd", "host", "start", "end",
            "returncode", "signal", "stdout", "stderr", "inputs", "outputs", "missing_outputs", "error",
        },
        {
            "schema", "step_id", "attempt_dir", "argv", "cwd", "host", "start", "end",
            "returncode", "signal", "stdout", "stderr", "inputs", "outputs", "missing_outputs", "error",
        },
        "receipt",
    )
    if receipt["schema"] != SCHEMA_RECEIPT:
        raise GateError("unsupported receipt schema")
    require_string(receipt["step_id"], "receipt.step_id")
    require_string(receipt["attempt_dir"], "receipt.attempt_dir")
    require_list(receipt["argv"], "receipt.argv")
    require_string(receipt["cwd"], "receipt.cwd")
    if receipt["host"] != "local":
        raise GateError("receipt host must be local")
    require_string(receipt["start"], "receipt.start")
    require_string(receipt["end"], "receipt.end")
    if receipt["returncode"] is not None and not isinstance(receipt["returncode"], int):
        raise GateError("receipt.returncode must be an integer or null")
    if receipt["signal"] is not None and not isinstance(receipt["signal"], (str, int)):
        raise GateError("receipt.signal must be a string, integer, or null")
    for key in ("stdout", "stderr"):
        row = require_dict(receipt[key], "receipt." + key)
        require_keys(row, {"path", "sha256"}, {"path", "sha256"}, "receipt." + key)
        path = attempt / relative_path(row["path"], "receipt." + key + ".path")
        if not path_is_under(path, attempt) or not path.is_file():
            raise GateError("receipt %s bytes are missing" % key)
        verify_digest(path, row["sha256"], "receipt." + key + ".sha256")
    require_list(receipt["inputs"], "receipt.inputs")
    require_list(receipt["outputs"], "receipt.outputs")
    missing = require_list(receipt["missing_outputs"], "receipt.missing_outputs")
    if any(not isinstance(item, str) for item in missing):
        raise GateError("receipt.missing_outputs must contain strings")
    if receipt["error"] is not None and not isinstance(receipt["error"], str):
        raise GateError("receipt.error must be a string or null")


def cmd_check(args: argparse.Namespace) -> int:
    manifest_path = Path(args.manifest)
    manifest, contract, root, roots, _ = load_context(manifest_path, Path(args.root) if args.root else None)
    print(json.dumps({
        "status": "ENGINEERING_MECHANICAL_OK",
        "schema": manifest["schema"],
        "chain": manifest["chain"],
        "gate": manifest["gate"],
        "stage": manifest["stage"],
        "manifest_sha256": sha256_file(manifest_path.resolve()),
        "contract_sha256": sha256_file(project_path(root, manifest["contract"]["path"], "manifest.contract.path")),
        "objects": len(manifest["objects"]),
        "steps": len(manifest["steps"]),
        "write_roots": roots,
    }, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


def cmd_render(args: argparse.Namespace) -> int:
    manifest_path = Path(args.manifest)
    manifest, contract, root, roots, _ = load_context(manifest_path, Path(args.root) if args.root else None)
    if args.out:
        output = check_write_target(root, args.out, roots, "render output")
    else:
        output = check_write_target(
            root,
            Path(roots[0]) / manifest["gate"] / "dispatch-001.md",
            roots,
            "render output",
        )
    render_dispatch(manifest_path.resolve(), manifest, contract, root, output)
    print(output)
    return 0


def object_path(root: Path, item: dict[str, Any]) -> Path:
    return project_path(root, item["path"], "object.path")


def run_step(
    manifest: dict[str, Any],
    root: Path,
    roots: list[str],
    step_id: str,
    receipt_dir_arg: str | None,
) -> int:
    steps = {item["id"]: item for item in manifest["steps"]}
    if step_id not in steps:
        raise GateError("unknown step: %s" % step_id)
    step = steps[step_id]
    objects = {item["id"]: item for item in manifest["objects"]}
    for ref in step["inputs"]:
        path = object_path(root, objects[ref])
        expected = objects[ref]["sha256"]
        verify_digest(path, expected, "input %s" % ref)
    if receipt_dir_arg:
        attempt = check_write_target(root, receipt_dir_arg, roots, "receipt directory")
    else:
        stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        attempt = check_write_target(
            root,
            Path(roots[0]) / manifest["gate"] / "evidence" / (stamp + "-" + step_id),
            roots,
            "receipt directory",
        )
    if attempt.exists() or attempt.is_symlink():
        raise GateError("refusing to reuse existing attempt directory: %s" % attempt)
    attempt.mkdir(parents=True, exist_ok=False)
    attempt_rel = attempt.relative_to(root.resolve()).as_posix()
    start = utc_now()
    start_payload = {
        "schema": "agent-gates.eng-start/v1",
        "step_id": step_id,
        "attempt_dir": attempt_rel,
        "argv": step["argv"],
        "cwd": step["cwd"],
        "host": step["host"],
        "start": start,
    }
    write_json_no_clobber(attempt / "start.json", start_payload)
    cwd = project_path(root, step["cwd"], "step cwd")
    process_error: str | None = None
    stdout = b""
    stderr = b""
    returncode: int | None = None
    signal_name: str | int | None = None
    try:
        process = subprocess.Popen(
            step["argv"],
            cwd=str(cwd),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=False,
        )
        try:
            timeout = step.get("timeout_seconds")
            stdout, stderr = process.communicate(timeout=timeout)
            returncode = process.returncode
        except subprocess.TimeoutExpired as exc:
            process.kill()
            stdout, stderr = process.communicate()
            returncode = None
            signal_name = "TIMEOUT"
            process_error = "step exceeded timeout_seconds"
        if returncode is not None and returncode < 0:
            signal_number = abs(returncode)
            signal_name = signal.Signals(signal_number).name if signal_number in signal.Signals._value2member_map_ else signal_number
    except OSError as exc:
        process_error = str(exc)
        returncode = None
    with (attempt / "stdout.bin").open("xb") as handle:
        handle.write(stdout)
    with (attempt / "stderr.bin").open("xb") as handle:
        handle.write(stderr)
    output_rows = []
    missing_outputs = []
    for ref in step["outputs"]:
        item = objects[ref]
        path = object_path(root, item)
        exists = path.is_file()
        digest = sha256_file(path) if exists else None
        if not exists:
            missing_outputs.append(ref)
        output_rows.append({"id": ref, "path": item["path"], "exists": exists, "sha256": digest})
    receipt = {
        "schema": SCHEMA_RECEIPT,
        "step_id": step_id,
        "attempt_dir": attempt_rel,
        "argv": step["argv"],
        "cwd": step["cwd"],
        "host": step["host"],
        "start": start,
        "end": utc_now(),
        "returncode": returncode,
        "signal": signal_name,
        "stdout": {"path": "stdout.bin", "sha256": sha256_file(attempt / "stdout.bin")},
        "stderr": {"path": "stderr.bin", "sha256": sha256_file(attempt / "stderr.bin")},
        "inputs": [
            {"id": ref, "path": objects[ref]["path"], "sha256": objects[ref]["sha256"]}
            for ref in step["inputs"]
        ],
        "outputs": output_rows,
        "missing_outputs": missing_outputs,
        "error": process_error,
    }
    validate_receipt(receipt, root, attempt)
    write_json_no_clobber(attempt / "receipt.json", receipt)
    print(json.dumps({
        "receipt": str(attempt / "receipt.json"),
        "returncode": returncode,
        "signal": signal_name,
        "missing_outputs": missing_outputs,
    }, ensure_ascii=False, indent=2, sort_keys=True))
    if returncode is None:
        return 124 if signal_name == "TIMEOUT" else 125
    if returncode < 0:
        return 128 + abs(returncode)
    if returncode == 0 and missing_outputs:
        return 4
    return returncode


def cmd_run(args: argparse.Namespace) -> int:
    manifest, _, root, roots, _ = load_context(Path(args.manifest), Path(args.root) if args.root else None)
    return run_step(manifest, root, roots, args.step, args.receipt_dir)


def cmd_record(args: argparse.Namespace) -> int:
    manifest_path = Path(args.manifest).resolve()
    manifest, _, root, roots, _ = load_context(manifest_path, Path(args.root) if args.root else None)
    review_path = Path(args.review)
    if not review_path.is_absolute():
        review_path = root / review_path
    review_path = review_path.resolve()
    if not path_is_under(review_path, root):
        raise GateError("review must be inside project root")
    review = read_json(review_path)
    review, blocking = review_validation(review, review_path, manifest_path, manifest, root)
    output = check_write_target(root, args.out, roots, "ledger output")
    check_failures = [
        item["id"] for item in review["checks"]
        if item["status"] in {"FAIL", "NEEDS_USER_DECISION"}
    ]
    if review["verdict"] == "PASS" and not blocking and not check_failures:
        candidate_status = "ENGINEERING_CANDIDATE_PASS"
    elif review["verdict"] == "NEEDS_USER_DECISION" or check_failures:
        candidate_status = "NEEDS_USER_DECISION"
    elif review["verdict"] == "NON_CONVERGENT":
        candidate_status = "NON_CONVERGENT"
    else:
        candidate_status = "ENGINEERING_CANDIDATE_BLOCKED"
    lines = [
        "# Candidate engineering ledger",
        "",
        "This fragment is not a formal Engineering PASS.",
        "",
        "- candidate status: %s" % candidate_status,
        "- schema: %s" % manifest["schema"],
        "- chain: %s" % manifest["chain"],
        "- gate: %s" % manifest["gate"],
        "- stage: %s" % manifest["stage"],
        "- manifest sha256: %s" % sha256_file(manifest_path),
        "- review sha256: %s" % sha256_file(review_path),
        "- reviewer: %s" % review["reviewer_id"],
        "- verdict: %s" % review["verdict"],
        "- blocking findings: %s" % (", ".join(blocking) if blocking else "(none)"),
        "- failed checks: %s" % (", ".join(check_failures) if check_failures else "(none)"),
        "",
        "## Findings",
        "",
    ]
    if review["findings"]:
        for finding in review["findings"]:
            lines.append("- %s [%s/%s] owner=%s: %s" % (
                finding["id"], finding["severity"], finding["status"],
                finding["owner"], finding["message"],
            ))
    else:
        lines.append("- (none)")
    lines.extend(["", "## Scope", "", "- %s" % review["scope"], ""])
    write_text_no_clobber(output, "\n".join(lines))
    print(output)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="engineering.py")
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("render", "check", "run", "record"):
        command = sub.add_parser(name)
        command.add_argument("manifest")
        command.add_argument("--root")
        if name == "render":
            command.add_argument("--out")
        elif name == "run":
            command.add_argument("--step", required=True)
            command.add_argument("--receipt-dir")
        elif name == "record":
            command.add_argument("--review", required=True)
            command.add_argument("--out", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "render":
            return cmd_render(args)
        if args.command == "check":
            return cmd_check(args)
        if args.command == "run":
            return cmd_run(args)
        if args.command == "record":
            return cmd_record(args)
        raise GateError("unknown command")
    except (GateError, IdentityError, OSError, json.JSONDecodeError) as exc:
        print("ENGINEERING_ERROR: %s" % exc, file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
