# tutor-contrib-edunext-security-patches

Shared, versioned **security patches** for Open edX, packaged as a Tutor plugin so
they live in **one place** instead of being copy-pasted into every client monorepo
(`*-your-cluster-project`).

Scope: security patches only — edx-platform `git apply` diffs (pdfjs, mathjax,
exif, jQuery CVEs…) and MFE npm fixes (e.g. axios `CVE-2025-58754`).

> POC status: this is the proof-of-concept requested to decide whether a shared
> Tutor plugin is worth adopting. See `../POC-REPORT.md`.

## Why

Today each monorepo keeps its own `src/edx-platform/patches/*.patch` and wires them
by hand in `build/plugins/azimutcli-apply-src-plugin.yml`. Result: **drift** (a
patch lands in PRE but not PROD, or in SOA but not campus-agora) and a manual
copy-paste per client on every CVE. This plugin makes the patch set a single
auditable, versioned dependency.

## Model: branch-per-release

A security patch is a diff against an **exact** edx-platform revision — the same CVE
needs a different `.patch` per Open edX release. So:

- **The git branch IS the release.** `teak` branch → teak patch set, `sumac` →
  sumac set, etc. Mirrors how Open edX itself ships (`open-release/teak.*`).
- The plugin has **no release-detection logic**: `patches/` can only ever hold the
  correct set for its branch. Removes the "applied teak patch on sumac" class of bug.
- **Tags are release-qualified:** `teak/v1.0.0`, `sumac/v1.0.0`. Clients pin a tag.

```
tutorsecuritypatches/
├── plugin.py            # registers tutor hooks + `tutor security-patches list`
└── patches/
    ├── manifest.yml     # release, upstream ref (for CI), ordered patch list, MFE fixes
    └── 01-heartbeat-demo.patch   # (one .patch per fix)
```

## How it applies patches

- **edx-platform**: each `.patch` is base64-embedded INLINE into the Dockerfile at
  `openedx-dockerfile-post-git-checkout` and applied with `git apply --check` then
  `git apply`. The pip package carries the bytes — nothing is COPYed from the build
  context. base64 avoids BuildKit-heredoc requirements and shell interpolation of
  `$`/backticks inside diffs. `--check` first = build fails loud on an incompatible
  patch instead of silently skipping.
- **MFE**: per-app npm commands injected at `mfe-dockerfile-pre-npm-install-<app>`.
  Inert for MFEs a client doesn't build.

## Consume it from a monorepo

> **Do NOT** put this in `OPENEDX_EXTRA_PIP_REQUIREMENTS` — that installs the package
> *inside* the openedx image, but a Tutor plugin must be installed on the **build
> host** where `tutor` renders the Dockerfile, or its patches are never injected.
> `pip install git+...` in `PICASSO_EXTRA_COMMANDS` is also rejected by picasso's
> validator. The sanctioned path is a **tutor plugin index** (same as mfe/sentry/aspects).

This repo **self-hosts its own index** (`plugins.yml` at the root) so it is
consumable end-to-end without a separate index repo. In `<namespace>/build/config.yml`,
`PICASSO_EXTRA_COMMANDS`:

```yaml
PICASSO_EXTRA_COMMANDS:
- tutor plugins index add https://raw.githubusercontent.com/eduNEXT/tutor-contrib-edunext-security-patches/teak/
- tutor plugins install mfe mfe-extensions sentry aspects edunext-security-patches
- tutor plugins enable edunext-security-patches
- tutor config save
```

Then remove the corresponding `.patch` files and their `COPY/git apply` lines from
`build/plugins/azimutcli-apply-src-plugin.yml`. Rebuild with Picasso.

- The **version pin** (`@teak/v1.0.0`) lives in `plugins.yml`, not per-monorepo.
- **Prod rule:** pin an immutable **tag**, never a branch — a branch is mutable and
  breaks reproducible builds.
- **Production:** move the `plugins.yml` entry into the central index
  (`eduNEXT/tutor-plugin-indexes`) so all clients share one index; per-release index
  branches (e.g. `teak-soa`) enable staged rollout. The self-hosted index is a POC
  convenience.

## Update a monorepo on a new CVE

1. Add the patch here (see below), release a new tag on the release branch.
2. Bump the one-line pin in each client's `build/config.yml` (`@teak/v1.0.0` →
   `@teak/v1.1.0`).
3. Rebuild via Picasso → transfer image tag `build` → `manifest` (existing manual
   step) → deploy.

## Add a new security patch

1. `git checkout teak` (or the target release branch).
2. Drop the `.patch` in `tutorsecuritypatches/patches/` (numbered for order).
3. Add an entry under `edx_platform:` (or `mfe:`) in `patches/manifest.yml`.
4. CI (`patch-compat`) runs `git apply --check` against the upstream release ref.
5. Tag `teak/v1.1.0`, update `CHANGELOG`.

### Releasing / versioning

- Tag format `‹release›/v‹semver›` — e.g. `teak/v1.1.0`.
- MINOR = new CVE fix · PATCH = fix to an existing patch · MAJOR = breaking / needs
  operator action.
- A CVE affecting several releases = one PR/tag per affected branch (cherry-pick).

## Test locally (no publish needed)

```bash
pip install -e .                 # or: pip install git+https://…@teak/v1.0.0
tutor plugins enable edunext-security-patches
tutor security-patches list      # audit what will be applied
tutor config save
# inspect the rendered Dockerfile to confirm the RUN git apply lines are injected:
grep -n "git apply" "$(tutor config printroot)/env/build/openedx/Dockerfile"
```

## Compatibility

- Patch set is release-scoped; the `patch-compat` GitHub workflow `git apply
  --check`s every patch against `edx_platform_ref` from the manifest on each push/PR.
- `tutor_min` in the manifest records the validated Tutor version.
