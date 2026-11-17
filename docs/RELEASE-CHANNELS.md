# Release channels

The repository has two release lines:

- `main` is the stable release line. Its published version and archive name use the normal numeric version, for example `1.4.12` and `boss-recruiting-1.4.12.zip`.
- `codex/wecom-cloud-knowledge` is the test line for the current migration build. The release builder keeps the numeric version in `SKILL.md` for runtime compatibility, but publishes the archive and signed manifest with the `-beta` suffix, for example `1.4.13-beta`.

The beta suffix is derived from the checked-out branch during `release_builder.py build`; it is not added to stable `main` builds. Beta builds must be treated as test releases and should not be selected by the stable auto-update path.
