"""Small subprocess client for the StructKit CLI.

The client builds argv lists only and never invokes through a shell. This keeps
Hermes tool calls predictable and avoids shell-injection risk when users pass
structure names, paths, or variables from chat.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path
from typing import Any, NamedTuple


STRUCTKIT_BIN = os.getenv("STRUCTKIT_BIN", "structkit")
DEFAULT_TIMEOUT_SECONDS = int(os.getenv("STRUCTKIT_TIMEOUT_SECONDS", "120"))


class StructKitResult(NamedTuple):
    command: list[str]
    returncode: int
    stdout: str
    stderr: str


def is_structkit_available() -> bool:
    """Return True when the StructKit executable is available on PATH."""
    return shutil.which(STRUCTKIT_BIN) is not None


def _append_optional(command: list[str], flag: str, value: str | None) -> None:
    if value:
        command.extend([flag, value])


def _append_output(command: list[str], output: str | None) -> None:
    if output and output != "text":
        command.extend(["--output", output])


def build_list_command(*, structures_path: str | None = None, output: str | None = None) -> list[str]:
    command = [STRUCTKIT_BIN, "list"]
    _append_optional(command, "--structures-path", structures_path)
    _append_output(command, output)
    return command


def build_info_command(
    *, structure_name: str, structures_path: str | None = None, output: str | None = None
) -> list[str]:
    command = [STRUCTKIT_BIN, "info"]
    _append_optional(command, "--structures-path", structures_path)
    _append_output(command, output)
    command.append(structure_name)
    return command


def build_vars_command(
    *, structure_definition: str, structures_path: str | None = None, output: str | None = None
) -> list[str]:
    command = [STRUCTKIT_BIN, "vars"]
    _append_optional(command, "--structures-path", structures_path)
    _append_output(command, output)
    command.append(structure_definition)
    return command


def build_validate_command(*, yaml_file: str) -> list[str]:
    return [STRUCTKIT_BIN, "validate", yaml_file]


def build_generate_command(
    *,
    structure_definition: str,
    output_dir: str,
    dry_run: bool = False,
    diff: bool = False,
    variables: dict[str, Any] | None = None,
    mappings_files: list[str] | None = None,
    structures_path: str | None = None,
    file_strategy: str | None = None,
    backup: bool = False,
) -> list[str]:
    """Build a `structkit generate` argv list.

    StructKit's CLI supports repeated mapping files. This plugin also passes
    simple variables as repeated `--var key=value` pairs. If future StructKit
    versions change variable injection, only this function should need updates.
    """
    command = [STRUCTKIT_BIN, "generate"]
    _append_optional(command, "--structures-path", structures_path)
    if dry_run:
        command.append("--dry-run")
    if diff:
        command.append("--diff")
    if backup:
        command.append("--backup")
    _append_optional(command, "--file-strategy", file_strategy)

    for key, value in sorted((variables or {}).items()):
        command.extend(["--var", f"{key}={value}"])

    for mappings_file in mappings_files or []:
        command.extend(["--mappings-file", mappings_file])

    command.extend([structure_definition, output_dir])
    return command


def build_generate_schema_command(
    *, structures_path: str | None = None, output_file: str | None = None
) -> list[str]:
    command = [STRUCTKIT_BIN, "generate-schema"]
    _append_optional(command, "--structures-path", structures_path)
    _append_optional(command, "--output", output_file)
    return command


def build_lint_command(
    *,
    targets: list[str] | None = None,
    structures_path: str | None = None,
    lint_all: bool = False,
    output: str | None = None,
) -> list[str]:
    command = [STRUCTKIT_BIN, "lint"]
    _append_optional(command, "--structures-path", structures_path)
    if lint_all:
        command.append("--all")
    _append_output(command, output)
    command.extend(targets or [])
    return command


def build_graph_command(
    *,
    structure_definition: str | None = None,
    structures_path: str | None = None,
    graph_all: bool = False,
    output: str | None = None,
) -> list[str]:
    command = [STRUCTKIT_BIN, "graph"]
    _append_optional(command, "--structures-path", structures_path)
    if graph_all:
        command.append("--all")
    _append_output(command, output)
    if structure_definition:
        command.append(structure_definition)
    return command


def run_structkit(
    command: list[str],
    *,
    cwd: str | None = None,
    allow_network: bool = True,
    timeout: int = DEFAULT_TIMEOUT_SECONDS,
) -> StructKitResult:
    """Run StructKit and return captured output."""
    env = os.environ.copy()
    if not allow_network:
        env["STRUCTKIT_DENY_NETWORK"] = "1"

    try:
        completed = subprocess.run(
            command,
            cwd=str(Path(cwd).resolve()) if cwd else None,
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        return StructKitResult(
            command=command,
            returncode=completed.returncode,
            stdout=completed.stdout or "",
            stderr=completed.stderr or "",
        )
    except FileNotFoundError:
        return StructKitResult(
            command=command,
            returncode=127,
            stdout="",
            stderr="StructKit CLI not found. Install it with `uv tool install structkit` or `pipx install structkit`.",
        )
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout.decode() if isinstance(exc.stdout, bytes) else (exc.stdout or "")
        return StructKitResult(
            command=command,
            returncode=124,
            stdout=stdout,
            stderr=f"StructKit command timed out after {timeout} seconds.",
        )
