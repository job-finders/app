from typing import TypedDict
import inspect
from typing import Any, get_type_hints

class ParamSchema(TypedDict):
    name: str
    type: str
    required: bool


class MethodSchema(TypedDict):
    description: str
    arguments: list[ParamSchema]
    returns: str


class BillingServiceRouterException(Exception):
    """ raise this exception for errors with routing"""
    pass

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
            action (str): The name of the method to execute (must be present in `_interface_schema`).
            *args: Positional arguments for the method.
            **kwargs: Keyword arguments for the method.

        Returns:
            Any: The result of the invoked method.

        Raises:
            ValueError: If the action does not exist in this service's schema
                        or if the found entry is not a callable method.
            RuntimeError: If an unexpected error occurs during the execution
                          of the target method.
        """
        try:
            # 1. Safely retrieve the method from the schema using .get()
            # This prevents a KeyError if 'action' is not found.
            method_to_execute = self._interface_schema.get(action)

            # 2. Check if the action was found at all.
            if method_to_execute is None:
                raise ValueError(f"Action '{action}' not found in {self.__class__.__name__}.")

            # 3. Check if the retrieved item is actually callable.
            if not callable(method_to_execute):
                raise ValueError(f"Configured action '{action}' is not a callable method.")

            # 4. Determine if the method is a coroutine function and await it if necessary.
            if inspect.iscoroutinefunction(method_to_execute):
                return await method_to_execute(*args, **kwargs)
            else:
                return method_to_execute(*args, **kwargs)

        # Catch specific exceptions that might be raised by the lookup or the method itself.
        except ValueError as e:
            # Re-raise the ValueError if it's one of the ones we explicitly raised.
            raise e
        except BillingServiceRouterException as e:
            # Re-raise your custom exception as is.
            raise e
        except Exception as e:
            # Catch any other unexpected exceptions and wrap them in a RuntimeError.
            # Using 'from e' maintains the original exception's traceback, which is crucial for debugging.
            raise RuntimeError(f"Error executing action '{action}': {e}") from e

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


