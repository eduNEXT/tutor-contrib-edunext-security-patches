# POC test runbook — complete end-to-end

Repo: `eduNEXT/tutor-contrib-edunext-security-patches` (this repo).
Consumer strain: `eduNEXT/testazimutcli` → `santodomingo`.

Each phase states what it proves and its pass criteria. Phases 1–3 need no picasso;
Phase 4 is the real deploy path; Phase 5 proves the release story.

---

## Phase 0 — publish (prerequisite for 2/4/5)

```bash
cd tutor-contrib-edunext-security-patches
git push -u origin teak
git tag teak/v1.0.0 && git push origin teak/v1.0.0
```

Needed because: the self-hosted index URL resolves to
`raw.githubusercontent.com/…/teak/plugins.yml` (branch must be pushed), and the
index `src` pins `@teak/v1.0.0` (tag must be pushed).

---

## Phase 1 — package builds & ships patches (local, no picasso)

Proves what the single-file drop-in could NOT: `package_data` ships the `.patch`
files in the wheel, and the `tutor.plugin.v1` entrypoint registers.

```bash
python -m build --wheel                       # -> dist/*.whl
python -m zipfile -l dist/*.whl | grep patches   # 01-heartbeat-demo.patch + manifest.yml present
python -m pip install dist/*.whl              # non-editable install (real wheel)
tutor plugins list | grep edunext-security-patches
tutor plugins enable edunext-security-patches
tutor security-patches list                  # lists teak patch + MFE CVEs
tutor config save
grep -n "git apply" "$(tutor config printroot)/env/build/openedx/Dockerfile"
```

PASS: wheel contains patches; `plugins list` shows it; Dockerfile has the
`base64 -d | git apply` line.

---

## Phase 2 — versioning & branch-per-release isolation

Proves tag pinning and that a release branch carries only its own set.

```bash
# tag install
python -m venv /tmp/v1 && /tmp/v1/bin/pip install "git+https://github.com/eduNEXT/tutor-contrib-edunext-security-patches@teak/v1.0.0"

# add a 2nd patch -> teak/v1.1.0, confirm both listed (MINOR release flow)
# ... add patch file + manifest entry + CHANGELOG, then:
git tag teak/v1.1.0 && git push origin teak teak/v1.1.0

# isolation: a sumac branch with a sumac-only set
git checkout -b sumac                          # edit patches/manifest.yml -> release: sumac
git tag sumac/v1.0.0 && git push origin sumac sumac/v1.0.0
```

PASS: `@teak/v1.0.0` venv has only teak patches; `@sumac/v1.0.0` venv only sumac.
No cross-contamination — the branch physically can't hold the wrong set.

---

## Phase 3 — CI compat gate

Proves drift detection before it reaches a client build.

- Push to `teak`/`sumac` triggers `.github/workflows/patch-compat.yml`, which
  `git apply --check`s every patch against `edx_platform_ref` from the manifest.
- Negative test: corrupt a patch context line, push → CI must go RED.

PASS: green on valid set, red on broken patch.

---

## Phase 4 — index + picasso end-to-end (real deploy path)

Already wired in `santodomingo/build/config.yml`:

```yaml
- tutor plugins index add https://raw.githubusercontent.com/eduNEXT/tutor-contrib-edunext-security-patches/teak/
- tutor plugins install mfe mfe-extensions sentry aspects edunext-security-patches
- tutor plugins enable edunext-security-patches
```

Steps:
```bash
cd testazimutcli
git add santodomingo/build && git commit -m "poc: consume edunext-security-patches via index" && git push origin <branch>
# GitHub Actions -> "Build Service Image": SERVICE=openedx, STRAIN_REPOSITORY_BRANCH=<branch>
```

Verify, three layers:

| Layer | Check | PASS |
|---|---|---|
| picasso logs | `tutor plugins install … edunext-security-patches` + render | install from index OK; `git apply` with no `patch does not apply` |
| image | `docker run --rm <img> grep -n 'check_results\["azimut"\]' openedx/core/djangoapps/heartbeat/views.py` | line present |
| runtime | `GET /heartbeat` | JSON has `"azimut": true` |
| MFE | learning/discussions image `package-lock.json` | axios bumped (^1.15.0 / ^0.30.2) |

Silent-failure watch: build green but azimut line absent ⇒ plugin not
enabled/discovered on host — check the enable step in logs.

---

## Phase 5 — release / rollback drill

Proves the update story: one index bump rolls to clients.

```bash
# bump plugins.yml src -> @teak/v1.1.0 on branch teak, push
# rebuild santodomingo -> new patch present in image
# rollback: plugins.yml src -> @teak/v1.0.0, push, rebuild -> old set restored
```

PASS: image content tracks the pinned tag both forward and back.

---

## Acceptance criteria met when

Phase 1 (wheel ships patches) + Phase 2 (branch isolation) + Phase 4 (heartbeat
`"azimut": true` via index) are green. That validates the real packaged scaffold and
its release model — not just the hook mechanism.
