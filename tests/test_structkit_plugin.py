from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]


def load_module(module_name: str, relative_path: str):
    spec = importlib.util.spec_from_file_location(module_name, REPO_ROOT / relative_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FakeContext:
    def __init__(self):
        self.tools = []

    def register_tool(self, **kwargs):
        self.tools.append(kwargs)


def parse_result(result: str) -> dict:
    return json.loads(result)


def test_register_exposes_structkit_toolset_tools():
    plugin = load_module("structkit_plugin", "__init__.py")
    ctx = FakeContext()

    plugin.register(ctx)

    names = {tool["name"] for tool in ctx.tools}
    assert names == {
        "structkit_list",
        "structkit_info",
        "structkit_vars",
        "structkit_validate",
        "structkit_preview",
        "structkit_generate",
    }
    assert {tool["toolset"] for tool in ctx.tools} == {"structkit"}
    assert all(callable(tool["handler"]) for tool in ctx.tools)
    assert all(callable(tool["check_fn"]) for tool in ctx.tools)


def test_client_builds_preview_command_without_shell():
    client = load_module("structkit_client", "plugin_client.py")

    command = client.build_generate_command(
        structure_definition="project/python",
        output_dir="./demo",
        dry_run=True,
        diff=True,
        variables={"project_name": "Demo App"},
        mappings_files=["team.yaml"],
        structures_path="./structures",
        file_strategy="backup",
        backup=True,
    )

    assert command == [
        "structkit",
        "generate",
        "--structures-path",
        "./structures",
        "--dry-run",
        "--diff",
        "--backup",
        "--file-strategy",
        "backup",
        "--var",
        "project_name=Demo App",
        "--mappings-file",
        "team.yaml",
        "project/python",
        "./demo",
    ]


def test_preview_handler_runs_dry_run_diff(monkeypatch):
    tools = load_module("structkit_tools", "plugin_tools.py")
    captured = {}

    def fake_run(command, **kwargs):
        captured["command"] = command
        captured["kwargs"] = kwargs
        return tools.StructKitResult(
            command=command,
            returncode=0,
            stdout="would create README.md",
            stderr="",
        )

    monkeypatch.setattr(tools, "run_structkit", fake_run)

    result = parse_result(
        tools.handle_structkit_preview(
            {
                "structure_definition": "project/python",
                "output_dir": "./demo",
                "variables": {"project_name": "Demo"},
            }
        )
    )

    assert result["success"] is True
    assert "--dry-run" in captured["command"]
    assert "--diff" in captured["command"]
    assert result["data"]["stdout"] == "would create README.md"
    assert result["data"]["mutating"] is False


def test_generate_handler_rejects_without_explicit_confirmation(monkeypatch):
    tools = load_module("structkit_tools", "plugin_tools.py")

    def fail_if_called(*args, **kwargs):  # pragma: no cover - should not happen
        raise AssertionError("structkit CLI should not run without confirm_write")

    monkeypatch.setattr(tools, "run_structkit", fail_if_called)

    result = parse_result(
        tools.handle_structkit_generate(
            {
                "structure_definition": "project/python",
                "output_dir": "./demo",
            }
        )
    )

    assert result["success"] is False
    assert "confirm_write" in result["error"]


def test_generate_handler_rejects_absolute_paths_outside_workspace(monkeypatch, tmp_path):
    tools = load_module("structkit_tools", "plugin_tools.py")

    def fail_if_called(*args, **kwargs):  # pragma: no cover - should not happen
        raise AssertionError("structkit CLI should not run for unsafe path")

    monkeypatch.setattr(tools, "run_structkit", fail_if_called)

    result = parse_result(
        tools.handle_structkit_generate(
            {
                "structure_definition": "project/python",
                "output_dir": "/tmp/outside-hermes-structkit-test",
                "confirm_write": True,
            },
            workdir=str(tmp_path),
        )
    )

    assert result["success"] is False
    assert "outside the workspace" in result["error"]


def test_validate_handler_wraps_structkit_validate(monkeypatch):
    tools = load_module("structkit_tools", "plugin_tools.py")
    captured = {}

    def fake_run(command, **kwargs):
        captured["command"] = command
        return tools.StructKitResult(command=command, returncode=0, stdout="valid", stderr="")

    monkeypatch.setattr(tools, "run_structkit", fake_run)

    result = parse_result(tools.handle_structkit_validate({"yaml_file": "template.struct.yaml"}))

    assert result["success"] is True
    assert captured["command"] == ["structkit", "validate", "template.struct.yaml"]
