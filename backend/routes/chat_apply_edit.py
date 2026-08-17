# ============================================================
# routes/chat_apply_edit.py – Apply AI-suggested edits
# ============================================================

import os
import re
from typing import Tuple

from flask import Blueprint, jsonify, request

chat_apply_edit_bp = Blueprint("chat_apply_edit", __name__)

# Keep edits limited to text files inside generated_projects
ALLOWED_TEXT_EXTS = (".py", ".js", ".html", ".css", ".json", ".md", ".yml", ".yaml", ".txt")


def _sandbox_root() -> str:
    base_path = os.path.realpath(os.path.join(os.path.dirname(__file__), "..", ".."))
    sandbox = os.path.join(base_path, "generated_projects")
    os.makedirs(sandbox, exist_ok=True)
    return sandbox


def _normalize_rel_path(file_path: str) -> str:
    return (file_path or "").replace("\\", "/").lstrip("/")


def _is_inside_sandbox(target_path: str) -> bool:
    try:
        base_real = os.path.realpath(_sandbox_root())
        target_real = os.path.realpath(target_path)
        return os.path.commonpath([base_real, target_real]) == base_real
    except ValueError:
        return False


def _safe_resolve_edit_target(rel_path: str) -> Tuple[str, str]:
    normalized = _normalize_rel_path(rel_path)
    full_path = os.path.join(_sandbox_root(), normalized)
    real_path = os.path.realpath(full_path)

    if not normalized or ".." in normalized.split("/"):
        raise ValueError("Access denied")

    if not _is_inside_sandbox(real_path):
        raise ValueError("Access denied")

    if not real_path.lower().endswith(ALLOWED_TEXT_EXTS):
        raise ValueError("Unsupported file type")

    return normalized, real_path


def _apply_search_replace(old_text: str, search: str, replace: str) -> Tuple[bool, str]:
    if search is None:
        return False, "Missing search"
    if replace is None:
        return False, "Missing replace"

    old_text = str(old_text or "")
    search = str(search)
    replace = str(replace)

    if search == "":
        return False, "Empty search pattern"

    if search not in old_text:
        return False, "Search pattern not found"

    return True, old_text.replace(search, replace, 1)


@chat_apply_edit_bp.route("/apply-edit", methods=["POST"])
def apply_edit():
    payload = request.get_json(silent=True) or {}
    file_path = payload.get("file", "")
    search = payload.get("search", "")
    replace = payload.get("replace", "")

    try:
        normalized, real_path = _safe_resolve_edit_target(file_path)
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 400

    try:
        if not os.path.exists(real_path):
            return jsonify({"success": False, "error": "File not found"}), 404

        with open(real_path, "r", encoding="utf-8", errors="ignore") as f:
            old_text = f.read()

        ok, result_or_err = _apply_search_replace(old_text, search, replace)
        if not ok:
            return jsonify({"success": False, "error": result_or_err}), 409

        # Backup before write
        backup_path = real_path + ".bak"
        try:
            with open(backup_path, "w", encoding="utf-8", errors="ignore") as bf:
                bf.write(old_text)
        except Exception:
            # backup failure should not block edit
            pass

        with open(real_path, "w", encoding="utf-8", errors="ignore") as f:
            f.write(result_or_err)

        return jsonify({"success": True, "file": normalized}), 200

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

