"""Herramientas Ghidra disponibles para la API Responses."""

from .main_set_schemas import tools_schemas as main_tools_schemas
from .companion_set_schemas import tools_schemas as companion_tools_schemas

tools_schemas = [*main_tools_schemas, *companion_tools_schemas]

__all__ = ["tools_schemas"]
