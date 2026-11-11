# Development instructions

## Branch and baseline

- Develop the WeCom cloud knowledge migration on `codex/wecom-cloud-knowledge`.
- Baseline: release `v1.4.9`, commit `6c15e45d4735e48c44860cac8bfa2f1119ab28de`.
- Keep `main` as the existing release line until an explicit merge instruction.
- This checkout contains public source. Installed profiles, candidate records, local state, credentials, and publisher keys belong outside this repository.
- Do not copy the installed skill directory wholesale into Git. Follow the existing sanitized-source and signed-release workflow for releases.

## Migration scope

- Read `docs/WECOM-KNOWLEDGE-MIGRATION.md` before implementing the migration.
- Separate knowledge distribution from program installation and runtime dependency downloads.
- Do not infer that a successful WeCom authorization grants read/write access to a particular shared space; validate the intended operations.
- Preserve local user modifications and historical run snapshots. A cloud update must not silently rewrite either.
- This branch does not authorize sending BOSS messages, uploading local private data, installing a development build over the active version, or publishing a release.

## Exploration

- Keep routine exploration shallow: at most five shell commands, directly relevant files, and no generated/dependency directory inspection.
- Broaden only when implementation, debugging, or an explicit review requires it.
