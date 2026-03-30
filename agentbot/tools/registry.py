"""Tool registry for the current minimal agent."""

from __future__ import annotations

from importlib import import_module
from pkgutil import iter_modules

from langchain_core.tools import BaseTool

import agentbot.tools as tools_package


def _discover_tools() -> list[BaseTool]:
    discovered: list[BaseTool] = []

    for module_info in iter_modules(tools_package.__path__):
        module_name = module_info.name
        if module_name.startswith("_") or module_name == "registry":
            continue

        module = import_module(f"{tools_package.__name__}.{module_name}")
        module_tools = getattr(module, "TOOLS", None)
        if module_tools is None:
            continue

        discovered.extend(module_tools)

    return discovered


def get_registered_tools() -> list[BaseTool]:
    """Return the tool list used by the current graph."""
    return _discover_tools()


def get_registered_tool_names() -> list[str]:
    """Return the registered tool names for debug output."""
    return [tool.name for tool in get_registered_tools()]
