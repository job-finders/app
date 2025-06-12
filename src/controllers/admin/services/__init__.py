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
        method_to_execute = self.__interface_map[action]

        if method_to_execute is None:
            raise ValueError(f"Action '{action}' not found in {self.__class__.__name__}.")

        if inspect.iscoroutinefunction(method_to_execute):
            return await method_to_execute(*args, **kwargs)
        else:
            return method_to_execute(*args, **kwargs)

    # Catch specific exceptions that might be raised by the lookup or the method itself.
    except ValueError as e:
        # Re-raise the ValueError if it's one of the ones we explicitly raised.
        raise e
    except Exception as e:
        # Catch any other unexpected exceptions and wrap them in a RuntimeError.
        # Using 'from e' maintains the original exception's traceback, which is crucial for debugging.
        raise RuntimeError(f"Error executing action '{action}': {str(e)}") from e
