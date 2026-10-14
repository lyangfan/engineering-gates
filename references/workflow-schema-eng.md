# Engineering workflow schemas

所有文档是 UTF-8 JSON。实现拒绝未知顶层字段和未知对象角色；字段值必须符合下面的约束。

## agent-gates.eng-contract/v1

    {
      "schema": "agent-gates.eng-contract/v1",
      "chain": "string",
      "gate": "A",
      "version": "string",
      "authority": {"path": "relative path", "sha256": "64 hex"},
      "requirements": [
        {"id": "A1", "title": "string", "acceptance": "string", "status": "required"}
      ],
      "allowed_hosts": ["local"],
      "write_roots": ["runs/chain/reviews"],
      "forbidden_paths": [".git"],
      "actors": {
        "decision_owner": "string",
        "coordinator": "string",
        "implementer": "string",
        "reviewer": "string"
      }
    }

gate 为 A 或 B。A 的 requirements ID 必须恰好覆盖 A1–A9；B 必须恰好覆盖 B1–B7。authority 是合同上游的固定身份。requirements 不允许用未决语义替代正式验收。

## agent-gates.eng-manifest/v1

    {
      "schema": "agent-gates.eng-manifest/v1",
      "chain": "string",
      "gate": "A",
      "stage": "baseline",
      "contract": {"path": "contract.json", "sha256": "64 hex"},
      "objects": [
        {
          "id": "source",
          "role": "authority",
          "path": "src/input.txt",
          "sha256": "64 hex",
          "source": "git:commit",
          "preservation": "git",
          "scope": "contract"
        }
      ],
      "steps": [
        {
          "id": "test",
          "argv": ["python3", "-B", "-m", "unittest"],
          "cwd": ".",
          "host": "local",
          "inputs": ["source"],
          "outputs": ["test-report"]
        }
      ],
      "acceptance": [
        {"id": "A1", "status": "evidenced", "evidence": ["test-receipt"]}
      ],
      "write_roots": ["runs/chain/reviews"],
      "forbidden_paths": [".git"]
    }

对象 role 只能是 authority、candidate、dependency、product、evidence。每个 path、source、preservation 和 scope 都是必填。manifest 的 acceptance ID 必须覆盖对应 contract 的 requirements；Closure 可以只列上一轮 finding 对应的要求，但必须在 stage 中写明。

## agent-gates.eng-review/v1

    {
      "schema": "agent-gates.eng-review/v1",
      "chain": "string",
      "gate": "A",
      "stage": "baseline",
      "manifest": {"path": "manifest.json", "sha256": "64 hex"},
      "contract_sha256": "64 hex",
      "reviewer_id": "string",
      "verdict": "PASS",
      "checks": [
        {"id": "A1", "status": "PASS", "evidence": ["receipt.json"]}
      ],
      "findings": [
        {
          "id": "F-001",
          "severity": "MAJOR",
          "status": "OPEN",
          "owner": "string",
          "message": "string"
        }
      ],
      "scope": "full_chain"
    }

verdict 为 PASS、NEEDS_USER_DECISION、NON_CONVERGENT、BLOCKED 或 REJECT。Closure 的 scope 必须是 closure，并列出上一轮 finding 或直接依赖。正式 PASS 仍由项目 reviewer 登记。

## agent-gates.eng-receipt/v1

    {
      "schema": "agent-gates.eng-receipt/v1",
      "step_id": "test",
      "attempt_dir": "runs/chain/reviews/B/evidence/001/test",
      "argv": ["python3", "-c", "print('ok')"],
      "cwd": ".",
      "host": "local",
      "start": "2026-01-01T00:00:00Z",
      "end": "2026-01-01T00:00:01Z",
      "returncode": 0,
      "signal": null,
      "stdout": {"path": "stdout.bin", "sha256": "64 hex"},
      "stderr": {"path": "stderr.bin", "sha256": "64 hex"},
    "inputs": [],
    "outputs": [],
    "missing_outputs": [],
    "error": null
  }

Receipt 必须在成功和失败时都保存。returncode 为整数或 null；若进程被信号终止，signal 写信号名或编号。stdout 和 stderr 指向 attempt 内不可变字节文件。缺失声明输出会使对应 step 无法成为证据。
