"""Hermes plugin entrypoint for StructKit."""

from __future__ import annotations

try:  # Normal package-style import when Hermes loads the plugin.
    from .plugin_tools import (
        STRUCTKIT_GENERATE_SCHEMA,
        STRUCTKIT_INFO_SCHEMA,
        STRUCTKIT_LIST_SCHEMA,
        STRUCTKIT_PREVIEW_SCHEMA,
        STRUCTKIT_VALIDATE_SCHEMA,
        STRUCTKIT_VARS_SCHEMA,
        check_structkit_available,
        handle_structkit_generate,
        handle_structkit_info,
        handle_structkit_list,
        handle_structkit_preview,
        handle_structkit_validate,
        handle_structkit_vars,
    )
except ImportError:  # Test/dev fallback when loaded directly from file.
    from plugin_tools import (  # type: ignore
        STRUCTKIT_GENERATE_SCHEMA,
        STRUCTKIT_INFO_SCHEMA,
        STRUCTKIT_LIST_SCHEMA,
        STRUCTKIT_PREVIEW_SCHEMA,
        STRUCTKIT_VALIDATE_SCHEMA,
        STRUCTKIT_VARS_SCHEMA,
        check_structkit_available,
        handle_structkit_generate,
        handle_structkit_info,
        handle_structkit_list,
        handle_structkit_preview,
        handle_structkit_validate,
        handle_structkit_vars,
    )


_TOOLS = [
    ("structkit_list", STRUCTKIT_LIST_SCHEMA, handle_structkit_list),
    ("structkit_info", STRUCTKIT_INFO_SCHEMA, handle_structkit_info),
    ("structkit_vars", STRUCTKIT_VARS_SCHEMA, handle_structkit_vars),
    ("structkit_validate", STRUCTKIT_VALIDATE_SCHEMA, handle_structkit_validate),
    ("structkit_preview", STRUCTKIT_PREVIEW_SCHEMA, handle_structkit_preview),
    ("structkit_generate", STRUCTKIT_GENERATE_SCHEMA, handle_structkit_generate),
]


def register(ctx) -> None:
    """Register StructKit tools with Hermes."""
    for name, schema, handler in _TOOLS:
        ctx.register_tool(
            name=name,
            toolset="structkit",
            schema=schema,
            handler=handler,
            check_fn=check_structkit_available,
            emoji="🏗️",
        )
