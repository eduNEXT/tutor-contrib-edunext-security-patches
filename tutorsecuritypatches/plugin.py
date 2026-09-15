"""Tutor plugin: apply eduNEXT shared security patches at image build time.

How it works
------------
The plugin ships a ``patches/`` directory (Python package data) and a
``patches/manifest.yml`` describing, for THIS release branch:

  * ``edx_platform``: ordered list of ``.patch`` files to ``git apply`` inside the
    edx-platform checkout (hook: ``openedx-dockerfile-post-git-checkout``).
  * ``mfe``: per-MFE npm fix commands (hook: ``mfe-dockerfile-pre-npm-install-<app>``).

edx-platform patches are injected INLINE (base64) into the Dockerfile — the pip
package carries the ``.patch`` bytes, so nothing needs to be COPYed from the build
context. base64 avoids heredoc/BuildKit requirements and shell interpolation of
``$``/backticks inside diffs.

There is deliberately NO release-detection logic: the branch IS the release, so
``patches/`` can only ever contain the correct set. That removes a whole class of
"applied teak patch on sumac" bugs — important for security.
"""
from __future__ import annotations

import base64
from pathlib import Path

import click
import yaml
from tutor import hooks

PACKAGE_ROOT = Path(__file__).parent
PATCHES_DIR = PACKAGE_ROOT / "patches"
MANIFEST_PATH = PATCHES_DIR / "manifest.yml"


def _load_manifest() -> dict:
    if not MANIFEST_PATH.is_file():
        return {}
    with open(MANIFEST_PATH, encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def _render_edx_platform_block(manifest: dict) -> str:
    """Return Dockerfile lines that apply every edx-platform patch, in order."""
    lines: list[str] = []
    for entry in manifest.get("edx_platform", []):
        patch_path = PATCHES_DIR / entry["file"]
        encoded = base64.b64encode(patch_path.read_bytes()).decode("ascii")
        cve = entry.get("cve", "n/a")
        lines.append(f"# eduNEXT security patch: {entry['file']} ({cve})")
        # `git apply --check` first so the build fails LOUD if the patch no longer
        # matches upstream context, instead of silently skipping.
        lines.append(
            f'RUN printf %s "{encoded}" | base64 -d | git apply --check - '
            f'&& printf %s "{encoded}" | base64 -d | git apply --verbose -'
        )
    return "\n".join(lines)


def _register_edx_platform_patches(manifest: dict) -> None:
    block = _render_edx_platform_block(manifest)
    if block:
        hooks.Filters.ENV_PATCHES.add_item(
            ("openedx-dockerfile-post-git-checkout", block)
        )


def _register_mfe_patches(manifest: dict) -> None:
    for app, entries in (manifest.get("mfe") or {}).items():
        lines: list[str] = []
        for entry in entries:
            lines.append(f"# eduNEXT security patch: {entry.get('cve', 'n/a')}")
            lines.append("RUN " + entry["run"])
        if lines:
            hooks.Filters.ENV_PATCHES.add_item(
                (f"mfe-dockerfile-pre-npm-install-{app}", "\n".join(lines))
            )


_MANIFEST = _load_manifest()
_register_edx_platform_patches(_MANIFEST)
_register_mfe_patches(_MANIFEST)


# ---------------------------------------------------------------------------
# CLI: `tutor security-patches list` — audit what this build will apply.
# ---------------------------------------------------------------------------
@click.group(name="security-patches", help="Inspect eduNEXT shared security patches.")
def security_patches() -> None:
    pass


@security_patches.command(name="list", help="List patches bundled for this release.")
def _list() -> None:
    manifest = _load_manifest()
    click.echo(f"release:      {manifest.get('release', 'unknown')}")
    click.echo(f"tutor_min:    {manifest.get('tutor_min', 'n/a')}")
    click.echo(f"edx ref (CI): {manifest.get('edx_platform_ref', 'n/a')}")
    click.echo("edx-platform patches:")
    for entry in manifest.get("edx_platform", []):
        click.echo(f"  - {entry['file']:<32} {entry.get('cve', '')}")
    click.echo("MFE npm patches:")
    for app, entries in (manifest.get("mfe") or {}).items():
        for entry in entries:
            click.echo(f"  - {app:<20} {entry.get('cve', '')}")


hooks.Filters.CLI_COMMANDS.add_item(security_patches)
