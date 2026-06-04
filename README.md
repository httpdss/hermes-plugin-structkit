# hermes-plugin-structkit

Hermes plugin for [StructKit](https://structkit.app/) project scaffolding workflows.

This plugin exposes StructKit's YAML-based scaffolding capabilities as Hermes-native tools with safety-first defaults: inspect templates, validate YAML, preview dry-run diffs, and only generate files after explicit confirmation.

## Tools

- `structkit_list` — list available StructKit structures/templates.
- `structkit_info` — inspect a structure definition.
- `structkit_vars` — show variables required by a structure before generation.
- `structkit_validate` — validate a StructKit YAML structure file.
- `structkit_preview` — run `structkit generate --dry-run --diff` without mutating files.
- `structkit_generate` — generate files; requires `confirm_write=true` and guards absolute output paths by default.

## Install

Install StructKit first so the plugin can find the `structkit` CLI:

```bash
uv tool install structkit
# or
pipx install structkit
```

Install this Hermes plugin:

```bash
hermes plugins install httpdss/hermes-plugin-structkit
```

Enable the `structkit` toolset if Hermes prompts you, or enable it manually:

```bash
hermes tools enable structkit
```

Start a fresh Hermes session after enabling tools.

## Example workflow

Ask Hermes:

```text
List available StructKit templates.
```

Then:

```text
Inspect variables for project/python.
```

Then preview safely:

```text
Preview generating project/python into ./demo with project_name Demo.
```

Only after reviewing the preview, request generation explicitly:

```text
Generate it into ./demo and confirm the write.
```

## Safety model

`structkit_preview` is non-mutating and always adds `--dry-run --diff`.

`structkit_generate` is mutating and rejects calls unless:

- `confirm_write=true` is provided.
- Absolute `output_dir` paths are inside the active workspace, unless `allow_outside_workspace=true` is provided.

The plugin never invokes StructKit through a shell; commands are built as argv lists and executed with `subprocess.run(..., shell=False)`.

If `allow_network=false`, the plugin sets `STRUCTKIT_DENY_NETWORK=1` for the command. StructKit templates may include remote content or hooks, so preview first and review template details before generating.

## Development

Run tests:

```bash
python3 -m pytest tests/ -q -o 'addopts='
```

The tests monkeypatch subprocess execution and do not require StructKit to be installed.

## Repository layout

```text
plugin.yaml        Hermes plugin manifest
__init__.py        Hermes register(ctx) entrypoint
plugin_client.py     StructKit CLI command builder/runner
plugin_tools.py      Hermes tool schemas and handlers
tests/             Unit tests
```
