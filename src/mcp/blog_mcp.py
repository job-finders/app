from __future__ import annotations

import os
from flask import Blueprint, request, jsonify, current_app

from src.services.hashnode import HashnodeService
from src.services.hashnode.hashnode_agemt_interface import HashnodeAgentCommandRegistry
from src.routes import flask_error_handler

bp = Blueprint("hashnode_mcp", __name__, url_prefix="/api/mcp/hashnode/v1")


# TODO investifate the proper Authentication Method which will support both LLM' and local users
# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------
def _get_registry() -> HashnodeAgentCommandRegistry:
    """Return a registry instance wired to the current token."""
    token = os.getenv("HASHNODE_TOKEN")
    if not token:
        # 404 instead of 500 keeps the contract clean for clients
        raise RuntimeError("HASHNODE_TOKEN environment variable not set")
    service = HashnodeService(token)
    return HashnodeAgentCommandRegistry(service)


# ------------------------------------------------------------------
# Discovery route (optional but useful)
# ------------------------------------------------------------------
@bp.route("/commands", methods=["GET"])
@flask_error_handler
async def list_commands():
    """Return the command catalogue (name, description, JSON-Schema)."""
    registry = _get_registry()
    cat = {
        name: {
            "description": meta["description"],
            "schema": (
                meta["input_model"].schema()
                if meta["input_model"] and hasattr(meta["input_model"], "schema")
                else None
            ),
        }
        for name, meta in registry.get_commands().items()
    }
    return jsonify(cat), 200


# ------------------------------------------------------------------
# Universal dispatcher
# ------------------------------------------------------------------
@bp.route("/<command>", methods=["POST"])
@flask_error_handler
async def dispatch(command: str):
    """
    POST /api/mcp/hashnode/v1/<command>
    Body: JSON matching the command's input model (empty object `{}` when none).
    """
    registry = _get_registry()
    payload = request.get_json(silent=True) or {}

    try:
        result = await registry.run_service(command, **payload)
        return jsonify(result), 200
    except KeyError:
        return jsonify({"error": f"Unknown command '{command}'"}), 404
    except Exception as exc:
        # Let flask_error_handler wrap the rest
        raise exc
