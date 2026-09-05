# Changelog

## 1.1.0
- Add `--fail-on` CI policy with `never`, `high`, `medium`, and `any` modes.
- Add configurable `--required-drift-threshold` for presence-ratio drift.
- Preserve JSON and HTML reports when CI exits with code 1 for detected drift.
- Add regression coverage for threshold overrides and CLI failure policies.
- Expand English-first documentation with CI, safety, and exit-code guidance.
- Redact examples for secret-like bracketed JSON paths, including keys such as `api key` and `auth token`.

## 1.0.0
- Initial public OSS release.
