"""eduNEXT shared security patches — Tutor plugin.

This package holds the cross-monorepo security patches (edx-platform diffs and
MFE npm fixes) for a single Open edX release. The Open edX release is defined by
the git BRANCH (branch-per-release model): the ``teak`` branch carries the teak
patch set, ``sumac`` the sumac set, etc.

The plugin version follows PEP 440 (e.g. ``1.0.0``); the release is encoded in
the git ref clients pin, e.g. ``git+https://.../...@teak/v1.0.0``.
"""

__version__ = "1.0.0"
