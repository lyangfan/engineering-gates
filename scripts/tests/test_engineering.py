from __future__ import annotations

import contextlib
import hashlib
import io
import json
import pathlib
import subprocess
import sys
import tempfile
import unittest

SCRIPT_DIR = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPT_DIR))

import decision_coverage
import engineering
import snapshots
from digest_table import sha256_file


def digest(path: pathlib.Path) -> str:
    return sha256_file(path)


class Fixture:
    def __init__(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self.tmp.name)
        (self.root / "runs").mkdir()
        (self.root / "authority.txt").write_text("authority\n", encoding="utf-8")
        (self.root / "input.txt").write_text("input\n", encoding="utf-8")
        self.output_bytes = b"generated\n"
        self.output_digest = hashlib.sha256(self.output_bytes).hexdigest()
        self.contract_path = self.root / "contract.json"
        self.manifest_path = self.root / "manifest.json"
        requirements = [
            {"id": "A%d" % i, "title": "requirement %d" % i, "acceptance": "observable acceptance %d" % i, "status": "required"}
            for i in range(1, 10)
        ]
        contract = {
            "schema": "agent-gates.eng-contract/v1",
            "chain": "fixture",
            "gate": "A",
            "version": "1.0.0",
            "authority": {"path": "authority.txt", "sha256": digest(self.root / "authority.txt")},
            "requirements": requirements,
            "allowed_hosts": ["local"],
            "write_roots": ["runs"],
            "forbidden_paths": [".git", "production"],
            "actors": {
                "decision_owner": "owner",
                "coordinator": "coordinator",
                "implementer": "implementer",
                "reviewer": "reviewer",
            },
        }
        self.contract_path.write_text(json.dumps(contract, indent=2), encoding="utf-8")
        objects = [
            {
                "id": "source",
                "role": "authority",
                "path": "input.txt",
                "sha256": digest(self.root / "input.txt"),
                "source": "file:fixture",
                "preservation": "workspace",
                "scope": "contract",
            },
            {
                "id": "output",
                "role": "product",
                "path": "output.txt",
                "sha256": self.output_digest,
                "source": "step:generate",
                "preservation": "workspace",
                "scope": "implementation",
            },
        ]
        self.manifest = {
            "schema": "agent-gates.eng-manifest/v1",
            "chain": "fixture",
            "gate": "A",
            "stage": "baseline",
            "contract": {"path": "contract.json", "sha256": digest(self.contract_path)},
            "objects": objects,
            "steps": [
                {
                    "id": "generate",
                    "argv": [
                        sys.executable,
                        "-c",
                        "from pathlib import Path; Path('output.txt').write_bytes(b'generated\\n')",
                    ],
                    "cwd": ".",
                    "host": "local",
                    "inputs": ["source"],
                    "outputs": ["output"],
                }
            ],
            "acceptance": [
                {"id": "A%d" % i, "status": "evidenced", "evidence": ["source"]}
                for i in range(1, 10)
            ],
            "write_roots": ["runs"],
            "forbidden_paths": [".git", "production"],
        }
        self.write_manifest()

    def write_manifest(self) -> None:
        self.manifest_path.write_text(json.dumps(self.manifest, indent=2), encoding="utf-8")

    def close(self) -> None:
        self.tmp.cleanup()


class EngineeringTests(unittest.TestCase):
    def setUp(self) -> None:
        self.fx = Fixture()

    def tearDown(self) -> None:
        self.fx.close()

    def call(self, argv: list[str]) -> tuple[int, str, str]:
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = engineering.main(argv)
        return code, out.getvalue(), err.getvalue()

    def test_check_valid_and_mechanical_marker(self) -> None:
        code, out, err = self.call(["check", str(self.fx.manifest_path)])
        self.assertEqual(code, 0, err)
        self.assertIn("ENGINEERING_MECHANICAL_OK", out)
        self.assertEqual(err, "")

    def test_unknown_field_is_rejected(self) -> None:
        self.fx.manifest["unexpected"] = True
        self.fx.write_manifest()
        code, _, err = self.call(["check", str(self.fx.manifest_path)])
        self.assertEqual(code, 2)
        self.assertIn("unknown fields", err)

    def test_empty_evidence_is_rejected(self) -> None:
        self.fx.manifest["acceptance"][0]["evidence"] = []
        self.fx.write_manifest()
        code, _, err = self.call(["check", str(self.fx.manifest_path)])
        self.assertEqual(code, 2)
        self.assertIn("empty evidence", err)

    def test_forbidden_parent_path_is_rejected(self) -> None:
        self.fx.manifest["write_roots"] = ["../outside"]
        self.fx.write_manifest()
        code, _, err = self.call(["check", str(self.fx.manifest_path)])
        self.assertEqual(code, 2)
        self.assertIn("relative", err)

    def test_symlink_escape_is_rejected(self) -> None:
        outside = pathlib.Path(self.fx.tmp.name).parent / "engineering-gates-outside"
        outside.mkdir(exist_ok=True)
        try:
            (self.fx.root / "escaped").symlink_to(outside, target_is_directory=True)
            self.fx.manifest["objects"][0]["path"] = "escaped/secret"
            self.fx.write_manifest()
            code, _, err = self.call(["check", str(self.fx.manifest_path)])
            self.assertEqual(code, 2)
            self.assertIn("escapes project root", err)
        finally:
            outside.rmdir()

    def test_render_is_neutral_and_no_clobber(self) -> None:
        out_path = self.fx.root / "runs" / "dispatch.md"
        code, output, err = self.call(["render", str(self.fx.manifest_path), "--out", str(out_path)])
        self.assertEqual(code, 0, err)
        self.assertEqual(pathlib.Path(output.strip()).resolve(), out_path.resolve())
        text = out_path.read_text(encoding="utf-8")
        self.assertIn("neutral reviewer material", text)
        self.assertIn("does not create Engineering PASS", text)
        code, _, err = self.call(["render", str(self.fx.manifest_path), "--out", str(out_path)])
        self.assertEqual(code, 2)
        self.assertIn("overwrite", err)

    def test_run_preserves_receipt_and_output(self) -> None:
        attempt = self.fx.root / "runs" / "attempt-001"
        code, out, err = self.call([
            "run", str(self.fx.manifest_path), "--step", "generate",
            "--receipt-dir", str(attempt),
        ])
        self.assertEqual(code, 0, err)
        receipt = attempt / "receipt.json"
        value = json.loads(receipt.read_text(encoding="utf-8"))
        self.assertEqual(value["returncode"], 0)
        self.assertEqual(value["missing_outputs"], [])
        self.assertEqual(digest(self.fx.root / "output.txt"), self.fx.output_digest)
        self.assertTrue((attempt / "stdout.bin").is_file())
        self.assertIn("receipt", out)
        code, _, err = self.call([
            "run", str(self.fx.manifest_path), "--step", "generate",
            "--receipt-dir", str(attempt),
        ])
        self.assertEqual(code, 2)
        self.assertIn("reuse existing", err)

    def test_run_nonzero_keeps_raw_logs(self) -> None:
        self.fx.manifest["steps"][0]["argv"] = [
            sys.executable, "-c", "import sys; print('out'); print('err', file=sys.stderr); sys.exit(7)"
        ]
        self.fx.manifest["steps"][0]["outputs"] = []
        self.fx.write_manifest()
        attempt = self.fx.root / "runs" / "failed"
        code, _, err = self.call([
            "run", str(self.fx.manifest_path), "--step", "generate",
            "--receipt-dir", str(attempt),
        ])
        self.assertEqual(code, 7, err)
        value = json.loads((attempt / "receipt.json").read_text(encoding="utf-8"))
        self.assertEqual(value["returncode"], 7)
        self.assertIn(b"out", (attempt / "stdout.bin").read_bytes())
        self.assertIn(b"err", (attempt / "stderr.bin").read_bytes())

    def test_missing_output_is_failure_evidence(self) -> None:
        self.fx.manifest["steps"][0]["argv"] = [sys.executable, "-c", "pass"]
        self.fx.write_manifest()
        attempt = self.fx.root / "runs" / "missing"
        code, _, err = self.call([
            "run", str(self.fx.manifest_path), "--step", "generate",
            "--receipt-dir", str(attempt),
        ])
        self.assertEqual(code, 4, err)
        value = json.loads((attempt / "receipt.json").read_text(encoding="utf-8"))
        self.assertEqual(value["missing_outputs"], ["output"])

    def test_generated_receipt_schema_is_bound_to_raw_logs(self) -> None:
        attempt = self.fx.root / "runs" / "receipt-schema"
        code, _, err = self.call([
            "run", str(self.fx.manifest_path), "--step", "generate",
            "--receipt-dir", str(attempt),
        ])
        self.assertEqual(code, 0, err)
        receipt = json.loads((attempt / "receipt.json").read_text(encoding="utf-8"))
        engineering.validate_receipt(receipt, self.fx.root, attempt)

    def test_record_only_writes_candidate_ledger(self) -> None:
        review_path = self.fx.root / "runs" / "review.json"
        review = {
            "schema": "agent-gates.eng-review/v1",
            "chain": "fixture",
            "gate": "A",
            "stage": "baseline",
            "manifest": {"path": "manifest.json", "sha256": digest(self.fx.manifest_path)},
            "contract_sha256": digest(self.fx.contract_path),
            "reviewer_id": "reviewer",
            "verdict": "PASS",
            "checks": [
                {"id": "A%d" % i, "status": "PASS", "evidence": ["source"]}
                for i in range(1, 10)
            ],
            "findings": [],
            "scope": "full_chain",
        }
        review_path.write_text(json.dumps(review, indent=2), encoding="utf-8")
        ledger = self.fx.root / "runs" / "ledger.md"
        code, _, err = self.call([
            "record", str(self.fx.manifest_path),
            "--review", str(review_path), "--out", str(ledger),
        ])
        self.assertEqual(code, 0, err)
        text = ledger.read_text(encoding="utf-8")
        self.assertIn("ENGINEERING_CANDIDATE_PASS", text)
        self.assertIn("not a formal Engineering PASS", text)

    def test_requirement_coverage_detects_missing_and_duplicate(self) -> None:
        result = decision_coverage.coverage(
            [{"id": "A1"}, {"id": "A1"}, {"id": "A2"}], "A"
        )
        self.assertFalse(result["complete"])
        self.assertIn("A3", result["missing"])
        self.assertEqual(result["duplicates"], ["A1"])

    def test_snapshot_is_stable_and_skips_symlinks(self) -> None:
        value = snapshots.snapshot(self.fx.root, exclude=["runs"])
        paths = [row["path"] for row in value["files"]]
        self.assertIn("authority.txt", paths)
        self.assertNotIn("runs/attempt-001/stdout.bin", paths)

    def test_fixed_git_identity_rejects_dirty_and_wrong_commit(self) -> None:
        subprocess.run(["git", "-C", str(self.fx.root), "init", "-q"], check=True)
        subprocess.run(["git", "-C", str(self.fx.root), "config", "user.email", "test@example.invalid"], check=True)
        subprocess.run(["git", "-C", str(self.fx.root), "config", "user.name", "Engineering Test"], check=True)
        subprocess.run(["git", "-C", str(self.fx.root), "add", "authority.txt", "input.txt", "contract.json", "manifest.json"], check=True)
        subprocess.run(["git", "-C", str(self.fx.root), "commit", "-qm", "fixture"], check=True)
        head = subprocess.check_output(["git", "-C", str(self.fx.root), "rev-parse", "HEAD"], text=True).strip()
        self.fx.manifest["objects"][0]["source"] = "git:" + head
        self.fx.manifest["objects"][0]["preservation"] = "git"
        self.fx.write_manifest()
        code, _, err = self.call(["check", str(self.fx.manifest_path)])
        self.assertEqual(code, 0, err)
        (self.fx.root / "input.txt").write_text("changed\n", encoding="utf-8")
        self.fx.manifest["objects"][0]["sha256"] = digest(self.fx.root / "input.txt")
        self.fx.write_manifest()
        code, _, err = self.call(["check", str(self.fx.manifest_path)])
        self.assertEqual(code, 2)
        self.assertIn("dirty or untracked", err)
        (self.fx.root / "input.txt").write_text("input\n", encoding="utf-8")
        self.fx.manifest["objects"][0]["sha256"] = digest(self.fx.root / "input.txt")
        self.fx.manifest["objects"][0]["source"] = "git:" + "0" * 40
        self.fx.write_manifest()
        code, _, err = self.call(["check", str(self.fx.manifest_path)])
        self.assertEqual(code, 2)
        self.assertIn("fixed commit", err)


if __name__ == "__main__":
    unittest.main()
