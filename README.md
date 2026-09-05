# Data Shape Guard

**Detect breaking JSON / JSONL shape drift before it reaches production.**

Data Shape Guard is a dependency-free Python CLI that infers the real shape of JSON data and compares a baseline against current data. It catches type changes, removed fields, and meaningful presence-ratio drift, then produces machine-readable JSON plus a human-readable HTML report.

> 日本語: JSON / JSONL の実データから構造を推定し、型変更・フィールド消失・出現率ドリフトを検出する軽量OSSです。CIの失敗条件としても使えます。

## Need the dataset cleaned and checked for you?

For one bounded CSV or JSON dataset, there is a fixed-scope async service:

- **Data Cleanup & Validation Pack — USD 99:** https://book.stripe.com/4gM8wO7dce7caMNg4XgEg2d
- Direct international services: https://paper-daemon.github.io/direct.html

The service covers duplicate handling, structural checks, a concise issue report, and cleaned output where feasible. Larger datasets or custom automation are scoped separately.

## Why this exists

APIs and exports often change without a formal schema migration. A field quietly disappears, an integer becomes a string, or a formerly required property becomes sparse. Those changes are easy to miss in spot checks and painful to discover downstream.

Data Shape Guard turns representative data into a lightweight contract you can verify in local checks or CI.

## Quick start

```bash
python data_shape_guard.py infer sample.jsonl
python data_shape_guard.py compare before.jsonl after.jsonl
```

Outputs default to:

- `shape.json` + `shape.html` for `infer`
- `shape-drift.json` + `shape-drift.html` for `compare`

## Use it as a CI gate

Fail the build only for breaking changes such as removed fields or type changes:

```bash
python data_shape_guard.py compare baseline.jsonl current.jsonl --fail-on high
```

Fail for medium-or-higher drift too:

```bash
python data_shape_guard.py compare baseline.jsonl current.jsonl \
  --required-drift-threshold 0.15 \
  --fail-on medium
```

`--fail-on` supports:

- `never` — report only, exit 0 on detected drift (default)
- `high` — exit 1 on high-severity drift
- `medium` — exit 1 on medium or high drift
- `any` — exit 1 on any reported drift, including additions

Exit codes:

- `0`: command completed and the configured gate passed
- `1`: drift matched the configured failure policy
- `2`: invalid input or parsing/configuration error

Reports are written before exit code `1`, so CI artifacts can still explain the failure.

## What it detects

| Signal | Severity | Example |
| --- | --- | --- |
| Field removed | high | `$.customer.email` disappears |
| Type set changed | high | `int` → `string` |
| Presence-ratio drift | medium | 100% → 50% |
| Field added | info | new optional property |

The presence-ratio threshold defaults to `0.25` and can be changed with `--required-drift-threshold`.

## Reliability and safety details

- Handles nested objects and arrays.
- Scans **all array elements**, rather than silently sampling only the first N values.
- Escapes literal keys containing `.` / `[]` so they cannot collide with structural paths.
- Strictly rejects duplicate JSON object keys.
- Rejects non-standard non-finite numbers such as `NaN`, `Infinity`, and `-Infinity`.
- Redacts example values for secret-like paths such as tokens, passwords, API keys, authorization values, and cookies.
- Does not modify input data.
- Python 3.10+.
- Standard library only.
- MIT licensed.

## Example workflow

```yaml
- name: Check data contract drift
  run: |
    python data_shape_guard.py compare \
      fixtures/baseline.jsonl \
      build/current.jsonl \
      --fail-on high
```

This is intentionally small enough to drop into an existing repository without adding another runtime dependency.

## Test suite

```bash
python3 -m unittest -v tests.test_data_shape_guard
```

Regression coverage includes type and required-ratio drift, late array-element type changes, path collisions, secret redaction, strict JSON parsing, and CI failure-policy behavior.

## Good fits

- API response regression checks
- ETL / ELT pipelines
- AI-agent tool outputs
- webhook payload monitoring
- exported SaaS data
- fixture and integration-test validation

## Project links

- OSS: https://github.com/paper-daemon/data-shape-guard
- Builder portfolio: https://paper-daemon.github.io/
- BOOTH free distribution: https://amase-memo.booth.pm/items/8778557
- Direct services: https://paper-daemon.github.io/direct.html

If you need a stricter schema language such as JSON Schema or OpenAPI, use one. Data Shape Guard is for the earlier, messier stage where the real payload is the best source of truth.