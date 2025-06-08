from typing import TypedDict


class ParamSchema(TypedDict):
    name: str
    type: str
    required: bool


class MethodSchema(TypedDict):
    description: str
    arguments: list[ParamSchema]
    returns: str

import inspect
from typing import Any, get_type_hints


class BillingServiceInterface:
    """
    Abstract base interface for all billing-related services, providing a dynamic method execution
    layer for AI agents and unified schema description.
    """

    def __init__(self):
        # Each concrete class must define this: {"action_name": bound_method}
        self.__interface_map: dict[str, Any] = {}

    async def execute(self, action: str, *args, **kwargs):
        """
        Dynamically executes a method based on the provided action name.

        Args:
            action (str): The name of the method to execute (must be present in `__interface_map`)
            *args: Positional arguments for the method
            **kwargs: Keyword arguments for the method

        Returns:
            Any: The result of the invoked method

        Raises:
            ValueError: If the action does not exist in this service
        """
        try:
            return await self.__interface_map[action](*args, **kwargs)
        except KeyError:
            raise ValueError(f"Action '{action}' not found in {self.__class__.__name__}")
        except Exception as e:
            raise RuntimeError(f"Error executing action '{action}': {e}")

    def _interface_schema(self):
        """
        Returns a machine-readable interface specification for AI agents.

        Returns:
            dict: A schema describing all available actions, their arguments, and documentation.
        """
        schema = {}
        for name, method in self.__class__.__dict__.items():
            if name.startswith('_') and callable(method):
                doc = inspect.getdoc(method) or ""
                sig = inspect.signature(method)
                hints = get_type_hints(method)

                params = []
                for param_name, param in sig.parameters.items():
                    if param_name == "self":
                        continue
                    param_type = str(hints.get(param_name, "Any"))
                    params.append({
                        "name": param_name,
                        "type": param_type,
                        "required": param.default == inspect.Parameter.empty
                    })

                schema[name] = {
                    "description": doc,
                    "arguments": params,
                    "returns": str(hints.get("return", "Any"))
                }

        return schema

    async def _describe_actions(self) -> dict[str, str]:
        """
        Returns a dictionary describing available executable actions in this service.

        Returns:
            dict[str, str]: Mapping of method names to docstring descriptions.
        """
        return {
            name: method.__doc__ or ""
            for name, method in self.__class__.__dict__.items()
            if callable(method) and name.startswith('_')
        }


