# StructKit plugin installed

The StructKit Hermes plugin is installed.

## Next steps

1. Install StructKit if it is not already available:

   ```bash
   uv tool install structkit
   # or
   pipx install structkit
   ```

2. Enable the toolset:

   ```bash
   hermes tools enable structkit
   ```

3. Start a fresh Hermes session, then ask:

   ```text
   List available StructKit templates.
   ```

Use `structkit_preview` before `structkit_generate` to review dry-run diffs before writing files.
