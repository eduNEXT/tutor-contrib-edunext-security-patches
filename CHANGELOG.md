# Changelog

All notable changes to this patch set are documented here. Versions are
release-qualified git tags: `‹openedx-release›/v‹semver›` (e.g. `teak/v1.0.0`).

- MINOR = new CVE / security patch added
- PATCH = fix to an existing patch (rebased context, corrected diff)
- MAJOR = breaking change / requires operator action

## [teak/v1.0.0] - 2026-09-15

### Added
- Initial teak patch set.
- `01-heartbeat-demo.patch` — POC demo patch (heartbeat endpoint), migrated from
  the santodomingo strain. Placeholder for real edx-platform security patches
  (pdfjs / mathjax / exif / jQuery CVEs).
- MFE npm fixes for `CVE-2025-58754` (axios) on `learning` (override) and
  `discussions` (direct dep bump).
