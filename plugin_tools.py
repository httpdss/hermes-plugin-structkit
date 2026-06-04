"""Hermes tool schemas and handlers for StructKit."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

def tool_result(data: dict[str, Any]) -> str:
    """Return a Hermes-compatible JSON tool result.

    We keep this local instead of importing ``tools.registry`` so an external
    plugin checkout with its own ``tools.py`` never shadows Hermes' core
    ``tools`` package during development or plugin discovery.
    """
    return json.dumps({"success": True, "data": data})


def tool_error(message: str) -> str:
    """Return a Hermes-compatible JSON tool error."""
    return json.dumps({"success": False, "error": message})

try:  # Normal package import when installed as a Hermes plugin.
    from .plugin_client import (
        StructKitResult,
        build_generate_command,
        build_info_command,
        build_list_command,
        build_validate_command,
        build_vars_command,
        is_structkit_available,
        run_structkit,
    )
except ImportError:  # Test/dev fallback when loaded directly from file.
    from plugin_client import (  # type: ignore
        StructKitResult,
        build_generate_command,
        build_info_command,
        build_list_command,
        build_validate_command,
        build_vars_command,
        is_structkit_available,
        run_structkit,
    )


MAX_OUTPUT_CHARS = 20_000
FILE_STRATEGIES = {"overwrite", "skip", "append", "rename", "backup"}
OUTPUT_FORMATS = {"text", "json"}


def _schema(name: str, description: str, properties: dict[str, Any], required: list[str] | None = None) -> dict[str, Any]:
    return {
        "name": name,
        "description": description,
        "parameters": {
            "type": "object",
            "properties": properties,
            "required": required or [],
            "additionalProperties": False,
        },
    }


STRUCTKIT_LIST_SCHEMA = _schema(
    "structkit_list",
    "List available StructKit structures/templates.",
    {
        "structures_path": {"type": "string", "description": "Optional custom structures directory."},
        "output": {"type": "string", "enum": sorted(OUTPUT_FORMATS), "default": "text"},
    },
)

STRUCTKIT_INFO_SCHEMA = _schema(
    "structkit_info",
    "Inspect a StructKit structure/template definition.",
    {
        "structure_name": {"type": "string", "description": "Structure name or local structure path."},
        "structures_path": {"type": "string", "description": "Optional custom structures directory."},
        "output": {"type": "string", "enum": sorted(OUTPUT_FORMATS), "default": "text"},
    },
    ["structure_name"],
)

STRUCTKIT_VARS_SCHEMA = _schema(
    "structkit_vars",
    "Inspect variables required by a StructKit structure/template.",
    {
        "structure_definition": {"type": "string", "description": "Structure name or local YAML path."},
        "structures_path": {"type": "string", "description": "Optional custom structures directory."},
        "output": {"type": "string", "enum": sorted(OUTPUT_FORMATS), "default": "text"},
    },
    ["structure_definition"],
)

STRUCTKIT_VALIDATE_SCHEMA = _schema(
    "structkit_validate",
    "Validate a StructKit YAML structure file.",
    {"yaml_file": {"type": "string", "description": "Path to a .struct.yaml or StructKit YAML file."}},
    ["yaml_file"],
)

_GENERATE_COMMON_PROPERTIES: dict[str, Any] = {
    "structure_definition": {"type": "string", "description": "Structure name or local YAML path."},
    "output_dir": {"type": "string", "description": "Directory where StructKit should generate files."},
    "variables": {"type": "object", "description": "StructKit variable values as key/value pairs."},
    "mappings_files": {
        "type": "array",
        "items": {"type": "string"},
        "description": "Optional mapping files passed as repeated --mappings-file flags.",
    },
    "structures_path": {"type": "string", "description": "Optional custom structures directory."},
    "file_strategy": {"type": "string", "enum": sorted(FILE_STRATEGIES)},
    "backup": {"type": "boolean", "default": False},
    "allow_network": {
        "type": "boolean",
        "default": True,
        "description": "If false, sets STRUCTKIT_DENY_NETWORK=1 for the command.",
    },
    "timeout": {"type": "integer", "minimum": 1, "maximum": 600, "default": 120},
}

STRUCTKIT_PREVIEW_SCHEMA = _schema(
    "structkit_preview",
    "Preview StructKit generation with --dry-run --diff. This tool is non-mutating.",
    _GENERATE_COMMON_PROPERTIES,
    ["structure_definition", "output_dir"],
)

STRUCTKIT_GENERATE_SCHEMA = _schema(
    "structkit_generate",
    "Generate files with StructKit. This mutates the filesystem and requires confirm_write=true.",
    {
        **_GENERATE_COMMON_PROPERTIES,
        "confirm_write": {
            "type": "boolean",
            "description": "Must be true to allow filesystem writes.",
            "default": False,
        },
        "allow_outside_workspace": {
            "type": "boolean",
            "description": "Allow absolute output paths outside the active workspace.",
            "default": False,
        },
    },
    ["structure_definition", "output_dir", "confirm_write"],
)


def check_structkit_available() -> bool:
    return is_structkit_available()


def _string_arg(args: dict[str, Any], key: str, *, required: bool = False) -> str | None:
    value = args.get(key)
    if value is None or value == "":
        if required:
            raise ValueError(f"Missing required argument: {key}")
        return None
    if not isinstance(value, str):
        raise ValueError(f"{key} must be a string")
    return value


def _bool_arg(args: dict[str, Any], key: str, default: bool = False) -> bool:
    value = args.get(key, default)
    if not isinstance(value, bool):
        raise ValueError(f"{key} must be a boolean")
    return value


def _int_arg(args: dict[str, Any], key: str, default: int) -> int:
    value = args.get(key, default)
    if not isinstance(value, int):
        raise ValueError(f"{key} must be an integer")
    if value < 1 or value > 600:
        raise ValueError(f"{key} must be between 1 and 600")
    return value


def _output_arg(args: dict[str, Any]) -> str | None:
    output = _string_arg(args, "output")
    if output and output not in OUTPUT_FORMATS:
        raise ValueError(f"output must be one of: {', '.join(sorted(OUTPUT_FORMATS))}")
    return output


def _variables_arg(args: dict[str, Any]) -> dict[str, Any]:
    value = args.get("variables") or {}
    if not isinstance(value, dict):
        raise ValueError("variables must be an object")
    for key in value:
        if not isinstance(key, str):
            raise ValueError("variables keys must be strings")
    return value


def _string_list_arg(args: dict[str, Any], key: str) -> list[str]:
    value = args.get(key) or []
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ValueError(f"{key} must be an array of strings")
    return value


def _file_strategy_arg(args: dict[str, Any]) -> str | None:
    value = _string_arg(args, "file_strategy")
    if value and value not in FILE_STRATEGIES:
        raise ValueError(f"file_strategy must be one of: {', '.join(sorted(FILE_STRATEGIES))}")
    return value


def _command_data(result: StructKitResult, *, mutating: bool) -> dict[str, Any]:
    stdout = _truncate(result.stdout)
    stderr = _truncate(result.stderr)
    data: dict[str, Any] = {
        "command": result.command,
        "returncode": result.returncode,
        "stdout": stdout,
        "stderr": stderr,
        "mutating": mutating,
    }
    parsed = _try_parse_json(stdout)
    if parsed is not None:
        data["json"] = parsed
    return data


def _truncate(text: str) -> str:
    if len(text) <= MAX_OUTPUT_CHARS:
        return text
    omitted = len(text) - MAX_OUTPUT_CHARS
    return text[:MAX_OUTPUT_CHARS] + f"\n...[truncated {omitted} chars]"


def _try_parse_json(text: str) -> Any | None:
    stripped = text.strip()
    if not stripped:
        return None
    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        return None


def _result_or_error(result: StructKitResult, *, mutating: bool) -> str:
    data = _command_data(result, mutating=mutating)
    if result.returncode == 0:
        return tool_result(data)
    return tool_error(
        f"StructKit command failed with exit code {result.returncode}: {data.get('stderr') or data.get('stdout') or 'no output'}"
    )


def _workdir_from_kwargs(kwargs: dict[str, Any]) -> str:
    workdir = kwargs.get("workdir") or kwargs.get("cwd") or os.getcwd()
    return str(workdir)


def _ensure_output_dir_is_safe(output_dir: str, *, workdir: str, allow_outside_workspace: bool) -> None:
    if allow_outside_workspace:
        return
    output_path = Path(output_dir)
    if not output_path.is_absolute():
        return
    resolved_output = output_path.resolve()
    resolved_workdir = Path(workdir).resolve()
    try:
        resolved_output.relative_to(resolved_workdir)
    except ValueError as exc:
        raise ValueError(
            f"output_dir is outside the workspace ({resolved_workdir}). "
            "Use a relative path or set allow_outside_workspace=true."
        ) from exc


def handle_structkit_list(args: dict[str, Any], **kwargs: Any) -> str:
    try:
        command = build_list_command(
            structures_path=_string_arg(args, "structures_path"),
            output=_output_arg(args),
        )
        result = run_structkit(command, cwd=_workdir_from_kwargs(kwargs))
        return _result_or_error(result, mutating=False)
    except ValueError as exc:
        return tool_error(str(exc))


def handle_structkit_info(args: dict[str, Any], **kwargs: Any) -> str:
    try:
        command = build_info_command(
            structure_name=_string_arg(args, "structure_name", required=True) or "",
            structures_path=_string_arg(args, "structures_path"),
            output=_output_arg(args),
        )
        result = run_structkit(command, cwd=_workdir_from_kwargs(kwargs))
        return _result_or_error(result, mutating=False)
    except ValueError as exc:
        return tool_error(str(exc))


def handle_structkit_vars(args: dict[str, Any], **kwargs: Any) -> str:
    try:
        command = build_vars_command(
            structure_definition=_string_arg(args, "structure_definition", required=True) or "",
            structures_path=_string_arg(args, "structures_path"),
            output=_output_arg(args),
        )
        result = run_structkit(command, cwd=_workdir_from_kwargs(kwargs))
        return _result_or_error(result, mutating=False)
    except ValueError as exc:
        return tool_error(str(exc))


def handle_structkit_validate(args: dict[str, Any], **kwargs: Any) -> str:
    try:
        command = build_validate_command(yaml_file=_string_arg(args, "yaml_file", required=True) or "")
        result = run_structkit(command, cwd=_workdir_from_kwargs(kwargs))
        return _result_or_error(result, mutating=False)
    except ValueError as exc:
        return tool_error(str(exc))


def _generate_command_from_args(args: dict[str, Any], *, dry_run: bool, diff: bool) -> list[str]:
    return build_generate_command(
        structure_definition=_string_arg(args, "structure_definition", required=True) or "",
        output_dir=_string_arg(args, "output_dir", required=True) or "",
        dry_run=dry_run,
        diff=diff,
        variables=_variables_arg(args),
        mappings_files=_string_list_arg(args, "mappings_files"),
        structures_path=_string_arg(args, "structures_path"),
        file_strategy=_file_strategy_arg(args),
        backup=_bool_arg(args, "backup"),
    )


def handle_structkit_preview(args: dict[str, Any], **kwargs: Any) -> str:
    try:
        command = _generate_command_from_args(args, dry_run=True, diff=True)
        result = run_structkit(
            command,
            cwd=_workdir_from_kwargs(kwargs),
            allow_network=_bool_arg(args, "allow_network", True),
            timeout=_int_arg(args, "timeout", 120),
        )
        return _result_or_error(result, mutating=False)
    except ValueError as exc:
        return tool_error(str(exc))


def handle_structkit_generate(args: dict[str, Any], **kwargs: Any) -> str:
    try:
        if not _bool_arg(args, "confirm_write", False):
            return tool_error("structkit_generate writes files and requires confirm_write=true. Run structkit_preview first.")

        workdir = _workdir_from_kwargs(kwargs)
        output_dir = _string_arg(args, "output_dir", required=True) or ""
        _ensure_output_dir_is_safe(
            output_dir,
            workdir=workdir,
            allow_outside_workspace=_bool_arg(args, "allow_outside_workspace", False),
        )

        command = _generate_command_from_args(args, dry_run=False, diff=False)
        result = run_structkit(
            command,
            cwd=workdir,
            allow_network=_bool_arg(args, "allow_network", True),
            timeout=_int_arg(args, "timeout", 120),
        )
        return _result_or_error(result, mutating=True)
    except ValueError as exc:
        return tool_error(str(exc))
