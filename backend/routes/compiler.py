# ============================================================
# routes/compiler.py - Project Compiler
# ============================================================

import json
import logging
import re
from html import escape

from flask import Blueprint, jsonify, request

import os
import uuid

logger = logging.getLogger(__name__)

from flask_jwt_extended import jwt_required
from marshmallow import Schema, ValidationError, fields, validate

compiler_bp = Blueprint("compiler", __name__)

class CompileSchema(Schema):
    idea = fields.Str(required=False, load_default="")
    frontend = fields.Str(
        required=False,
        load_default="vanilla",
        validate=validate.OneOf(["vanilla", "react"]),
    )
    backend = fields.Str(
        required=False,
        load_default="flask",
        validate=validate.OneOf(["flask", "express", "go", "php", "none"]),
    )

compile_schema = CompileSchema()
@compiler_bp.route('/compile', methods=['POST'])
def compile_project():
    """Compile/generate a project blueprint.

    Returns a payload compatible with frontend/script.js expectations:
    {
      tree: str,
      files: { [path]: content },
      ai_generated: bool,
      ai_error?: str
    }
    """
    try:
        data = compile_schema.load(request.get_json(silent=True) or {})
    except ValidationError as exc:
        return jsonify({"error": "Validation failed", "details": exc.messages}), 422

    idea = data.get("idea", "")
    frontend = data.get("frontend", "vanilla")
    backend = data.get("backend", "flask")

    from backend.services.ai_service import ai_service

    # Hard limits for safety/perf
    MAX_FILES = int(os.getenv("MENDIFY_MAX_FILES", "200"))
    MAX_TOTAL_CHARS = int(os.getenv("MENDIFY_MAX_TOTAL_CHARS", "600000"))

    ai_generated = False
    ai_error = None

    if ai_service.is_available():
        try:
            raw = ai_service.generate_project(
                idea=idea,
                frontend=frontend,
                backend=backend,
            )
            logger.info(f"AI Service raw response length: {len(raw) if raw else 0}")
            logger.info(f"AI Service raw response preview: {raw[:500] if raw else 'None'}")
            parsed = _parse_ai_output(raw)

            logger.info(f"Parsed result keys: {parsed.keys() if isinstance(parsed, dict) else 'Not dict'}")
            logger.info(f"Parsed ai_generated: {parsed.get('ai_generated')}")
            logger.info(f"Parsed files count: {len(parsed.get('files', {})) if isinstance(parsed.get('files'), dict) else 0}")

            tree = parsed.get("tree", "")
            files = parsed.get("files", {}) or {}
            if not isinstance(files, dict) or not files:
                raise ValueError("AI compiler returned no files")

            # Apply caps
            if isinstance(files, dict) and len(files) > MAX_FILES:
                # Truncate deterministically
                items = list(files.items())[:MAX_FILES]
                files = {k: v for k, v in items}

            total_chars = 0
            for k, v in list(files.items()) if isinstance(files, dict) else []:
                s = str(v)
                total_chars += len(s)
                if total_chars > MAX_TOTAL_CHARS:
                    files[k] = s[:20000]

            ai_generated = True
            return jsonify({
                "tree": tree,
                "files": files,
                "ai_generated": ai_generated,
                "ai_error": ai_error,
            }), 200

        except Exception as e:
            ai_error = str(e)

    # If AI is unavailable or failed, return a proper local fallback project.
    fallback = build_fallback_project(idea, frontend, backend)
    return jsonify({
        "tree": fallback.get("tree", ""),
        "files": fallback.get("files", {}),
        "ai_generated": False,
        "ai_error": ai_error or "AI compiler offline",
    }), 200


def _clean_idea(idea: str) -> str:
    return (idea or "Mendify app").strip() or "Mendify app"


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", _clean_idea(value).lower()).strip("-")
    return (slug[:40].strip("-") or "mendify-app")


def _backend_label(backend: str) -> str:
    return f" and {backend} backend" if backend and backend != "none" else ""


def _backend_files(backend: str) -> dict:
    if backend == "flask":
        return {
            "backend/app.py": """from flask import Flask, jsonify, request
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

items = [
    {"id": 1, "text": "Plan the first release", "done": False},
    {"id": 2, "text": "Invite an early tester", "done": False},
]


def next_id():
    return max((item["id"] for item in items), default=0) + 1


@app.get("/api/health")
def health_check():
    return jsonify({"status": "ok"})


@app.get("/api/items")
def list_items():
    return jsonify({"items": items})


@app.post("/api/items")
def create_item():
    data = request.get_json(silent=True) or {}
    text = str(data.get("text", "")).strip()

    if not text:
        return jsonify({"error": "Text is required"}), 400

    item = {"id": next_id(), "text": text, "done": False}
    items.append(item)
    return jsonify(item), 201


@app.patch("/api/items/<int:item_id>")
def update_item(item_id):
    data = request.get_json(silent=True) or {}

    for item in items:
        if item["id"] == item_id:
            if "text" in data:
                item["text"] = str(data["text"]).strip()
            if "done" in data:
                item["done"] = bool(data["done"])
            return jsonify(item)

    return jsonify({"error": "Item not found"}), 404


@app.delete("/api/items/<int:item_id>")
def delete_item(item_id):
    for index, item in enumerate(items):
        if item["id"] == item_id:
            deleted = items.pop(index)
            return jsonify(deleted)

    return jsonify({"error": "Item not found"}), 404


if __name__ == "__main__":
    app.run(debug=True)
""",
            "backend/requirements.txt": "Flask==3.0.0\nflask-cors==4.0.0\n",
        }

    if backend == "express":
        return {
            "backend/package.json": json.dumps(
                {
                    "name": "mendify-api",
                    "version": "1.0.0",
                    "type": "module",
                    "private": True,
                    "scripts": {"dev": "node server.js"},
                    "dependencies": {"cors": "^2.8.5", "express": "^4.18.3"},
                },
                indent=2,
            ),
            "backend/server.js": """import express from 'express';
import cors from 'cors';

const app = express();
const port = process.env.PORT || 5000;

app.use(cors());
app.use(express.json());

let items = [
  { id: 1, text: 'Plan the first release', done: false },
  { id: 2, text: 'Invite an early tester', done: false }
];

function nextId() {
  return items.reduce((max, item) => Math.max(max, item.id), 0) + 1;
}

app.get('/api/health', (_req, res) => {
  res.json({ status: 'ok' });
});

app.get('/api/items', (_req, res) => {
  res.json({ items });
});

app.post('/api/items', (req, res) => {
  const text = String(req.body?.text || '').trim();

  if (!text) {
    res.status(400).json({ error: 'Text is required' });
    return;
  }

  const item = { id: nextId(), text, done: false };
  items.push(item);
  res.status(201).json(item);
});

app.patch('/api/items/:id', (req, res) => {
  const id = Number(req.params.id);
  const item = items.find(entry => entry.id === id);

  if (!item) {
    res.status(404).json({ error: 'Item not found' });
    return;
  }

  if (typeof req.body.text === 'string') item.text = req.body.text.trim();
  if (typeof req.body.done === 'boolean') item.done = req.body.done;

  res.json(item);
});

app.delete('/api/items/:id', (req, res) => {
  const id = Number(req.params.id);
  const existingLength = items.length;
  items = items.filter(item => item.id !== id);

  if (items.length === existingLength) {
    res.status(404).json({ error: 'Item not found' });
    return;
  }

  res.status(204).send();
});

app.listen(port, () => {
  console.log(`API listening on http://localhost:${port}`);
});
""",
        }

    if backend == "go":
        return {
            "backend/main.go": """package main

import (
	"encoding/json"
	"log"
	"net/http"
	"strconv"
	"strings"
)

type Item struct {
	ID   int    `json:"id"`
	Text string `json:"text"`
	Done bool   `json:"done"`
}

var items = []Item{
	{ID: 1, Text: "Plan the first release", Done: false},
	{ID: 2, Text: "Invite an early tester", Done: false},
}

func writeJSON(w http.ResponseWriter, status int, value any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	json.NewEncoder(w).Encode(value)
}

func nextID() int {
	maxID := 0
	for _, item := range items {
		if item.ID > maxID {
			maxID = item.ID
		}
	}
	return maxID + 1
}

func itemsHandler(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Access-Control-Allow-Origin", "*")
	w.Header().Set("Access-Control-Allow-Methods", "GET, POST, PATCH, DELETE, OPTIONS")
	w.Header().Set("Access-Control-Allow-Headers", "Content-Type")

	if r.Method == http.MethodOptions {
		w.WriteHeader(http.StatusNoContent)
		return
	}

	if r.Method == http.MethodGet {
		writeJSON(w, http.StatusOK, map[string]any{"items": items})
		return
	}

	if r.Method == http.MethodPost {
		var body struct {
			Text string `json:"text"`
		}
		json.NewDecoder(r.Body).Decode(&body)
		text := strings.TrimSpace(body.Text)

		if text == "" {
			writeJSON(w, http.StatusBadRequest, map[string]string{"error": "Text is required"})
			return
		}

		item := Item{ID: nextID(), Text: text, Done: false}
		items = append(items, item)
		writeJSON(w, http.StatusCreated, item)
		return
	}

	writeJSON(w, http.StatusMethodNotAllowed, map[string]string{"error": "Method not allowed"})
}

func itemHandler(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Access-Control-Allow-Origin", "*")
	w.Header().Set("Access-Control-Allow-Methods", "PATCH, DELETE, OPTIONS")
	w.Header().Set("Access-Control-Allow-Headers", "Content-Type")

	if r.Method == http.MethodOptions {
		w.WriteHeader(http.StatusNoContent)
		return
	}

	idText := strings.TrimPrefix(r.URL.Path, "/api/items/")
	id, err := strconv.Atoi(idText)
	if err != nil {
		writeJSON(w, http.StatusBadRequest, map[string]string{"error": "Invalid id"})
		return
	}

	for index := range items {
		if items[index].ID != id {
			continue
		}

		if r.Method == http.MethodPatch {
			var body struct {
				Text *string `json:"text"`
				Done *bool  `json:"done"`
			}
			json.NewDecoder(r.Body).Decode(&body)
			if body.Text != nil {
				items[index].Text = strings.TrimSpace(*body.Text)
			}
			if body.Done != nil {
				items[index].Done = *body.Done
			}
			writeJSON(w, http.StatusOK, items[index])
			return
		}

		if r.Method == http.MethodDelete {
			items = append(items[:index], items[index+1:]...)
			w.WriteHeader(http.StatusNoContent)
			return
		}
	}

	writeJSON(w, http.StatusNotFound, map[string]string{"error": "Item not found"})
}

func main() {
	http.HandleFunc("/api/health", func(w http.ResponseWriter, r *http.Request) {
		writeJSON(w, http.StatusOK, map[string]string{"status": "ok"})
	})
	http.HandleFunc("/api/items", itemsHandler)
	http.HandleFunc("/api/items/", itemHandler)

	log.Println("API listening on http://localhost:5000")
	log.Fatal(http.ListenAndServe(":5000", nil))
}
""",
        }

    if backend == "php":
        return {
            "backend/index.php": """<?php
header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: GET, POST, PATCH, DELETE, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type');

if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    http_response_code(204);
    exit;
}

$store = __DIR__ . '/items.json';

if (!file_exists($store)) {
    file_put_contents($store, json_encode([
        ['id' => 1, 'text' => 'Plan the first release', 'done' => false],
        ['id' => 2, 'text' => 'Invite an early tester', 'done' => false],
    ], JSON_PRETTY_PRINT));
}

$items = json_decode(file_get_contents($store), true) ?: [];
$method = $_SERVER['REQUEST_METHOD'];
$path = parse_url($_SERVER['REQUEST_URI'], PHP_URL_PATH);

function save_items($store, $items) {
    file_put_contents($store, json_encode(array_values($items), JSON_PRETTY_PRINT));
}

function json_response($value, $status = 200) {
    http_response_code($status);
    echo json_encode($value);
    exit;
}

if ($path === '/api/health') {
    json_response(['status' => 'ok']);
}

if ($path === '/api/items' && $method === 'GET') {
    json_response(['items' => $items]);
}

if ($path === '/api/items' && $method === 'POST') {
    $data = json_decode(file_get_contents('php://input'), true) ?: [];
    $text = trim($data['text'] ?? '');

    if ($text === '') {
        json_response(['error' => 'Text is required'], 400);
    }

    $ids = array_column($items, 'id');
    $item = ['id' => empty($ids) ? 1 : max($ids) + 1, 'text' => $text, 'done' => false];
    $items[] = $item;
    save_items($store, $items);
    json_response($item, 201);
}

if (preg_match('#^/api/items/(\\d+)$#', $path, $matches)) {
    $id = (int) $matches[1];

    foreach ($items as $index => $item) {
        if ((int) $item['id'] !== $id) {
            continue;
        }

        if ($method === 'PATCH') {
            $data = json_decode(file_get_contents('php://input'), true) ?: [];
            if (array_key_exists('text', $data)) {
                $items[$index]['text'] = trim((string) $data['text']);
            }
            if (array_key_exists('done', $data)) {
                $items[$index]['done'] = (bool) $data['done'];
            }
            save_items($store, $items);
            json_response($items[$index]);
        }

        if ($method === 'DELETE') {
            array_splice($items, $index, 1);
            save_items($store, $items);
            http_response_code(204);
            exit;
        }
    }

    json_response(['error' => 'Item not found'], 404);
}

json_response(['error' => 'Route not found'], 404);
""",
        }

    return {}


def _backend_tree(backend: str) -> str:
    if backend == "flask":
        return "|-- backend/\n|   |-- app.py\n|   `-- requirements.txt\n"
    if backend == "express":
        return "|-- backend/\n|   |-- package.json\n|   `-- server.js\n"
    if backend == "go":
        return "|-- backend/\n|   `-- main.go\n"
    if backend == "php":
        return "|-- backend/\n|   `-- index.php\n"
    return ""


def _vanilla_files(clean_idea: str, project_name: str, backend: str) -> dict:
    backend_label = _backend_label(backend)
    files = {
        "index.html": f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{escape(clean_idea)}</title>
  <link rel="stylesheet" href="css/style.css" />
</head>
<body>
  <div id="app">
    <header class="hero">
      <p class="eyebrow">Generated by Mendify</p>
      <h1>{escape(clean_idea)}</h1>
      <p class="hero-copy">A complete browser app starter with persistent state, filters, and clean UI structure.</p>
    </header>

    <main class="workspace">
      <section class="panel composer-panel" aria-labelledby="composerTitle">
        <div>
          <p class="section-kicker">Create</p>
          <h2 id="composerTitle">Add a new item</h2>
        </div>

        <form id="itemForm" class="composer">
          <label for="itemInput">Item text</label>
          <div class="input-row">
            <input id="itemInput" type="text" placeholder="Write something to track" autocomplete="off" />
            <button type="submit">Add</button>
          </div>
        </form>
      </section>

      <section class="panel list-panel" aria-labelledby="listTitle">
        <div class="list-header">
          <div>
            <p class="section-kicker">Dashboard</p>
            <h2 id="listTitle">Items</h2>
          </div>
          <p id="stats" class="stats">0 active / 0 complete</p>
        </div>

        <div class="filters" role="group" aria-label="Filter items">
          <button class="filter-btn active" type="button" data-filter="all">All</button>
          <button class="filter-btn" type="button" data-filter="active">Active</button>
          <button class="filter-btn" type="button" data-filter="done">Done</button>
        </div>

        <p id="emptyState" class="empty">No items yet. Add your first one above.</p>
        <ul id="itemList" class="item-list"></ul>

        <button id="clearDoneBtn" class="ghost-btn" type="button">Clear completed</button>
      </section>
    </main>
  </div>

  <script src="js/app.js"></script>
</body>
</html>""",
        "css/style.css": """*,
*::before,
*::after {
  box-sizing: border-box;
}

:root {
  color-scheme: dark;
  --bg: #10131a;
  --panel: #171c26;
  --panel-strong: #202837;
  --text: #eef2ff;
  --muted: #9aa7bd;
  --accent: #8dd3c7;
  --accent-strong: #54b6a7;
  --border: #2b3548;
  --danger: #ff7b8a;
}

body {
  margin: 0;
  font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  background: radial-gradient(circle at top left, rgba(141, 211, 199, 0.13), transparent 34%), var(--bg);
  color: var(--text);
  line-height: 1.6;
}

button,
input {
  font: inherit;
}

button {
  border: 0;
  cursor: pointer;
}

#app {
  width: min(1040px, calc(100% - 32px));
  margin: 0 auto;
  padding: 48px 0;
}

.hero {
  padding: 32px 0 28px;
  border-bottom: 1px solid var(--border);
}

.eyebrow,
.section-kicker {
  margin: 0 0 8px;
  color: var(--accent);
  font-size: 0.78rem;
  font-weight: 800;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

h1,
h2,
p {
  margin-top: 0;
}

h1 {
  max-width: 780px;
  margin-bottom: 14px;
  font-size: clamp(2.2rem, 7vw, 4.8rem);
  line-height: 1;
}

.hero-copy {
  max-width: 680px;
  margin-bottom: 0;
  color: var(--muted);
}

.workspace {
  display: grid;
  grid-template-columns: minmax(260px, 0.85fr) minmax(0, 1.4fr);
  gap: 20px;
  padding-top: 28px;
}

.panel {
  border: 1px solid var(--border);
  border-radius: 16px;
  background: rgba(23, 28, 38, 0.86);
  padding: 22px;
}

.composer {
  display: grid;
  gap: 10px;
}

label {
  color: var(--muted);
  font-size: 0.9rem;
}

.input-row {
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 10px;
}

input {
  min-width: 0;
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 12px 14px;
  background: #111722;
  color: var(--text);
  outline: none;
}

input:focus {
  border-color: var(--accent);
  box-shadow: 0 0 0 3px rgba(141, 211, 199, 0.18);
}

.composer button,
.filter-btn.active {
  border-radius: 12px;
  padding: 12px 16px;
  background: var(--accent);
  color: #0e141d;
  font-weight: 800;
}

.list-header {
  display: flex;
  align-items: start;
  justify-content: space-between;
  gap: 16px;
}

.stats {
  margin: 0;
  color: var(--muted);
  font-size: 0.9rem;
}

.filters {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin: 14px 0 18px;
}

.filter-btn,
.ghost-btn {
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 10px 12px;
  background: transparent;
  color: var(--text);
}

.empty {
  margin: 24px 0;
  color: var(--muted);
}

.item-list {
  display: grid;
  gap: 10px;
  margin: 0;
  padding: 0;
  list-style: none;
}

.item {
  display: grid;
  grid-template-columns: auto 1fr auto;
  align-items: center;
  gap: 10px;
  border: 1px solid var(--border);
  border-radius: 14px;
  padding: 12px;
  background: var(--panel-strong);
}

.item input[type="checkbox"] {
  width: 18px;
  height: 18px;
}

.item.done .item-text {
  color: var(--muted);
  text-decoration: line-through;
}

.delete-btn {
  border-radius: 10px;
  padding: 8px 10px;
  background: rgba(255, 123, 138, 0.12);
  color: var(--danger);
}

.ghost-btn {
  margin-top: 18px;
}

@media (max-width: 760px) {
  #app {
    width: min(100% - 24px, 1040px);
    padding-top: 24px;
  }

  .workspace,
  .input-row {
    grid-template-columns: 1fr;
  }

  .list-header {
    display: block;
  }
}
""",
        "js/app.js": f"""'use strict';

const appIdea = {json.dumps(clean_idea)};
const storageKey = 'mendify:' + appIdea.toLowerCase().replace(/[^a-z0-9]+/g, '-');

const state = {{
  filter: 'all',
  items: loadItems()
}};

function loadItems() {{
  try {{
    const saved = window.localStorage.getItem(storageKey);
    if (saved) return JSON.parse(saved);
  }} catch (error) {{
    console.warn('Could not read saved items:', error);
  }}

  return [
    {{ id: crypto.randomUUID(), text: 'Customize this starter app', done: false }},
    {{ id: crypto.randomUUID(), text: 'Connect the backend API when ready', done: false }}
  ];
}}

function saveItems() {{
  window.localStorage.setItem(storageKey, JSON.stringify(state.items));
}}

function visibleItems() {{
  if (state.filter === 'active') return state.items.filter(item => !item.done);
  if (state.filter === 'done') return state.items.filter(item => item.done);
  return state.items;
}}

function renderStats() {{
  const active = state.items.filter(item => !item.done).length;
  const done = state.items.length - active;
  document.querySelector('#stats').textContent = `${{active}} active / ${{done}} complete`;
}}

function renderItems() {{
  const list = document.querySelector('#itemList');
  const emptyState = document.querySelector('#emptyState');
  const items = visibleItems();

  list.textContent = '';
  emptyState.hidden = items.length > 0;

  items.forEach(item => {{
    const li = document.createElement('li');
    li.className = `item${{item.done ? ' done' : ''}}`;

    const checkbox = document.createElement('input');
    checkbox.type = 'checkbox';
    checkbox.checked = item.done;
    checkbox.setAttribute('aria-label', `Mark "${{item.text}}" complete`);
    checkbox.addEventListener('change', () => toggleItem(item.id));

    const text = document.createElement('span');
    text.className = 'item-text';
    text.textContent = item.text;

    const deleteButton = document.createElement('button');
    deleteButton.type = 'button';
    deleteButton.className = 'delete-btn';
    deleteButton.textContent = 'Delete';
    deleteButton.addEventListener('click', () => deleteItem(item.id));

    li.append(checkbox, text, deleteButton);
    list.appendChild(li);
  }});

  renderStats();
}}

function addItem(text) {{
  state.items.unshift({{
    id: crypto.randomUUID(),
    text,
    done: false
  }});
  saveItems();
  renderItems();
}}

function toggleItem(id) {{
  state.items = state.items.map(item =>
    item.id === id ? {{ ...item, done: !item.done }} : item
  );
  saveItems();
  renderItems();
}}

function deleteItem(id) {{
  state.items = state.items.filter(item => item.id !== id);
  saveItems();
  renderItems();
}}

function clearCompleted() {{
  state.items = state.items.filter(item => !item.done);
  saveItems();
  renderItems();
}}

function setFilter(filter) {{
  state.filter = filter;
  document.querySelectorAll('.filter-btn').forEach(button => {{
    button.classList.toggle('active', button.dataset.filter === filter);
  }});
  renderItems();
}}

document.addEventListener('DOMContentLoaded', () => {{
  document.querySelector('#itemForm').addEventListener('submit', event => {{
    event.preventDefault();
    const input = document.querySelector('#itemInput');
    const text = input.value.trim();
    if (!text) return;

    addItem(text);
    input.value = '';
    input.focus();
  }});

  document.querySelectorAll('.filter-btn').forEach(button => {{
    button.addEventListener('click', () => setFilter(button.dataset.filter));
  }});

  document.querySelector('#clearDoneBtn').addEventListener('click', clearCompleted);

  renderItems();
}});
""",
        "README.md": f"""# {project_name}

{clean_idea}

Generated by Mendify with vanilla frontend{backend_label}.

## Features

- Responsive HTML, CSS, and JavaScript app shell
- Create, complete, delete, filter, and clear items
- Persistent browser state with localStorage
- Accessible labels and keyboard-friendly controls
- Optional backend files when a backend stack is selected

## Run

Open `index.html` in your browser.
""",
    }

    files.update(_backend_files(backend))
    return files


def _react_files(clean_idea: str, project_name: str, backend: str) -> dict:
    backend_label = _backend_label(backend)
    files = {
        "public/index.html": f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{escape(clean_idea)}</title>
</head>
<body>
  <div id="root"></div>
</body>
</html>""",
        "src/App.jsx": f"""import {{ useEffect, useMemo, useState }} from 'react';
import './App.css';

const appIdea = {json.dumps(clean_idea)};
const storageKey = 'mendify:' + appIdea.toLowerCase().replace(/[^a-z0-9]+/g, '-');

const starterItems = [
  {{ id: crypto.randomUUID(), text: 'Customize this starter app', done: false }},
  {{ id: crypto.randomUUID(), text: 'Connect the backend API when ready', done: false }}
];

function loadItems() {{
  try {{
    const saved = window.localStorage.getItem(storageKey);
    return saved ? JSON.parse(saved) : starterItems;
  }} catch {{
    return starterItems;
  }}
}}

export default function App() {{
  const [draft, setDraft] = useState('');
  const [filter, setFilter] = useState('all');
  const [items, setItems] = useState(loadItems);

  useEffect(() => {{
    window.localStorage.setItem(storageKey, JSON.stringify(items));
  }}, [items]);

  const visibleItems = useMemo(() => {{
    if (filter === 'active') return items.filter(item => !item.done);
    if (filter === 'done') return items.filter(item => item.done);
    return items;
  }}, [filter, items]);

  const activeCount = items.filter(item => !item.done).length;
  const doneCount = items.length - activeCount;

  function addItem(event) {{
    event.preventDefault();
    const text = draft.trim();
    if (!text) return;

    setItems(current => [
      {{ id: crypto.randomUUID(), text, done: false }},
      ...current
    ]);
    setDraft('');
  }}

  function toggleItem(id) {{
    setItems(current =>
      current.map(item => item.id === id ? {{ ...item, done: !item.done }} : item)
    );
  }}

  function deleteItem(id) {{
    setItems(current => current.filter(item => item.id !== id));
  }}

  function clearCompleted() {{
    setItems(current => current.filter(item => !item.done));
  }}

  return (
    <div className="app">
      <header className="hero">
        <p className="eyebrow">Generated by Mendify</p>
        <h1>{{appIdea}}</h1>
        <p>A complete React starter with persistent state, filters, and accessible controls.</p>
      </header>

      <main className="workspace">
        <section className="panel composer-panel" aria-labelledby="composerTitle">
          <p className="section-kicker">Create</p>
          <h2 id="composerTitle">Add a new item</h2>

          <form className="composer" onSubmit={{addItem}}>
            <label htmlFor="itemInput">Item text</label>
            <div className="input-row">
              <input
                id="itemInput"
                value={{draft}}
                onChange={{event => setDraft(event.target.value)}}
                placeholder="Write something to track"
              />
              <button type="submit">Add</button>
            </div>
          </form>
        </section>

        <section className="panel list-panel" aria-labelledby="listTitle">
          <div className="list-header">
            <div>
              <p className="section-kicker">Dashboard</p>
              <h2 id="listTitle">Items</h2>
            </div>
            <p className="stats">{{activeCount}} active / {{doneCount}} complete</p>
          </div>

          <div className="filters" role="group" aria-label="Filter items">
            {{['all', 'active', 'done'].map(option => (
              <button
                key={{option}}
                className={{`filter-btn ${{filter === option ? 'active' : ''}}`}}
                type="button"
                onClick={{() => setFilter(option)}}
              >
                {{option[0].toUpperCase() + option.slice(1)}}
              </button>
            ))}}
          </div>

          {{visibleItems.length === 0 ? (
            <p className="empty">No items match this filter.</p>
          ) : (
            <ul className="item-list">
              {{visibleItems.map(item => (
                <li className={{`item ${{item.done ? 'done' : ''}}`}} key={{item.id}}>
                  <input
                    type="checkbox"
                    checked={{item.done}}
                    onChange={{() => toggleItem(item.id)}}
                    aria-label={{`Mark "${{item.text}}" complete`}}
                  />
                  <span className="item-text">{{item.text}}</span>
                  <button className="delete-btn" type="button" onClick={{() => deleteItem(item.id)}}>
                    Delete
                  </button>
                </li>
              ))}}
            </ul>
          )}}

          <button className="ghost-btn" type="button" onClick={{clearCompleted}}>
            Clear completed
          </button>
        </section>
      </main>
    </div>
  );
}}
""",
        "src/index.jsx": """import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
""",
        "src/App.css": _vanilla_files(clean_idea, project_name, "none")["css/style.css"]
        .replace("#app", ".app")
        .replace(".composer button,\n.filter-btn.active", ".composer button"),
        "package.json": json.dumps(
            {
                "name": project_name,
                "version": "1.0.0",
                "private": True,
                "dependencies": {
                    "@vitejs/plugin-react": "^5.0.0",
                    "vite": "^7.0.0",
                    "react": "^18.2.0",
                    "react-dom": "^18.2.0",
                },
                "devDependencies": {},
                "scripts": {
                    "dev": "vite",
                    "build": "vite build",
                    "preview": "vite preview",
                },
            },
            indent=2,
        ),
        "README.md": f"""# {project_name}

{clean_idea}

Generated by Mendify with React frontend{backend_label}.

## Features

- Vite + React app structure
- Persistent browser state with localStorage
- Create, complete, delete, filter, and clear items
- Responsive CSS and accessible controls
- Optional backend files when a backend stack is selected

## Run

```bash
npm install
npm run dev
```"""
    }

    files.update(_backend_files(backend))
    return files


def build_fallback_project(idea: str, frontend: str, backend: str) -> dict:
    """Generate useful non-AI starter files from the user's prompt."""
    clean_idea = _clean_idea(idea)
    project_name = _slugify(clean_idea)

    if frontend == "react":
        backend_tree = _backend_tree(backend)
        readme_branch = "|-- README.md" if backend_tree else "`-- README.md"
        return {
            "tree": (
                f"{project_name}/\n"
                "|-- public/\n"
                "|   `-- index.html\n"
                "|-- src/\n"
                "|   |-- App.jsx\n"
                "|   |-- App.css\n"
                "|   `-- index.jsx\n"
                "|-- package.json\n"
                f"{readme_branch}\n"
                f"{backend_tree.rstrip()}"
            ),
            "files": _react_files(clean_idea, project_name, backend),
        }

    backend_tree = _backend_tree(backend)
    readme_branch = "|-- README.md" if backend_tree else "`-- README.md"
    return {
        "tree": (
            f"{project_name}/\n"
            "|-- index.html\n"
            "|-- css/\n"
            "|   `-- style.css\n"
            "|-- js/\n"
            "|   `-- app.js\n"
            f"{readme_branch}\n"
            f"{backend_tree.rstrip()}"
        ),
        "files": _vanilla_files(clean_idea, project_name, backend),
    }


# Trace / debug helpers — populated inside _looks_like_incomplete_project
_TRACE_AI_RESULT       = None   # raw AI result dict
_TRACE_QUALITY_RESULT  = None   # (demo, incmp) tuple
_TRACE_QUALITY_LOG     = []


def _looks_like_demo_project(result: dict, idea: str) -> bool:
    files = result.get("files") or {}
    combined = "\n".join(
        [result.get("tree", ""), *(str(value) for value in files.values())]
    ).lower()
    prompt = (idea or "").strip().lower()
    return "hello, world" in combined or (
        prompt and "my-app/" in combined and prompt not in combined
    )



def _line_count(files: dict, path: str) -> int:
    return len(str(files.get(path, "")).splitlines())


def _find_match(files: dict, endings: list) -> str | None:
    """Return the first file key whose *last segment* matches any ending in `endings`."""
    for key in files:
        seg = key.split("/")[-1]
        if seg in endings:
            return key
    return None


def _looks_like_incomplete_project(result: dict, frontend: str, backend: str) -> bool:
    files = result.get("files") or {}

    # ── Presence + completeness checks ─────────────────────────
    # Accept file names at any directory depth (AI may nest under
    # a project-name folder:  "myapp/src/App.jsx", "myapp/static/...").
    if frontend == "react":
        # ── React: need all five React entry-point files ──
        required_matches = {
            "index.html": _find_match(files, ["index.html"]),
            "package.json": _find_match(files, ["package.json"]),
            "App component": _find_match(files, ["App.jsx", "App.js"]),
            "App styles": _find_match(files, ["App.css", "style.css", "styles.css"]),
            "React entry": _find_match(files, ["index.jsx", "main.jsx", "index.js", "main.js"]),
        }
        missing = [label for label, match in required_matches.items() if not match]
        app_path = required_matches["App component"]
        style_path = required_matches["App styles"]
        if not missing:
            if _line_count(files, app_path) < 20 or _line_count(files, style_path) < 10:
                missing.append("(short App files)")
        if missing:
            return True
    else:
        # ── Vanilla: flexible about where files sit in the tree ──
        index_html  = _find_match(files, ["index.html"])
        app_js      = _find_match(files, ["app.js", "main.js", "script.js"])
        style_css   = _find_match(files, ["style.css", "styles.css"])

        if not index_html or not app_js:
            return True

        # Minimal line count checks (AI may return compact output)
        if _line_count(files, index_html) < 5:
            return True
        if _line_count(files, app_js) < 5:
            return True
        if style_css and _line_count(files, style_css) < 5:
            return True

    # ── Backend check: also flexible about path depth ──
    backend_requirements = {
        "flask":  (["app.py", "run.py", "main.py"],  10),
        "express": (["server.js", "index.js"],  10),
        "go":     ("main.go",           20),
        "php":    ("index.php",         15),
    }
    if backend in backend_requirements:
        expected_names, min_lines = backend_requirements[backend]
        # Normalize to list
        if isinstance(expected_names, str):
            expected_names = [expected_names]
        match = _find_match(files, expected_names)
        if not match or _line_count(files, match) < min_lines:
            return True

    return False


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


def _safe_write_generated_files(project_id: str, files: dict) -> str:
    """Write generated files into generated_projects/<project_id>/ with traversal protection."""
    project_dir = os.path.join(_sandbox_root(), project_id)
    os.makedirs(project_dir, exist_ok=True)

    # Hard cap to avoid abuse
    max_files = 200
    if isinstance(files, dict):
        if len(files) > max_files:
            raise ValueError(f"Too many files requested: {len(files)} > {max_files}")
    else:
        raise ValueError("Invalid files payload")

    for rel_path, content in files.items():
        rel_norm = _normalize_rel_path(rel_path)
        if not rel_norm or rel_norm.startswith("."):
            continue

        # Block traversal
        if ".." in rel_norm.split("/"):
            continue

        full_path = os.path.join(project_dir, rel_norm)
        if not _is_inside_sandbox(full_path):
            continue

        # Ensure directory exists
        parent = os.path.dirname(full_path)
        if parent:
            os.makedirs(parent, exist_ok=True)

        # Write as text
        with open(full_path, "w", encoding="utf-8", errors="ignore") as f:
            f.write(str(content))

    return project_dir

def _parse_ai_output(raw_result: any) -> dict:
    """
    Safely parses raw text or dictionary output from AIService,
    normalizing unstructured markdown files into structural JSON targets.
    """
    if isinstance(raw_result, dict):
        return raw_result

    if not isinstance(raw_result, str):
        return {"tree": "", "files": {}, "ai_generated": False}

    cleaned = raw_result.strip()

    # 1. Attempt to resolve raw JSON output if formatted/wrapped in backticks
    json_str = cleaned
    
    # FIX: Stripped triple-backticks from start/end without using dangerous MULTILINE flag
    if json_str.startswith("```"):
        json_str = re.sub(r'^```(?:json)?\s*|\s*```$', '', json_str, flags=re.IGNORECASE).strip()
    try:
        parsed = json.loads(json_str)
        if isinstance(parsed, dict) and "files" in parsed:
            return parsed
    except json.JSONDecodeError:
        pass

    # 2. Fallback to extracting directory structures and markdown file demarcations
    result_dict = {
        "tree": "",
        "files": {},
        "ai_generated": True
    }

    # Extract tree structure if placed before the first file block
    first_file_pos = cleaned.find("## File:")
    if first_file_pos == -1:
        first_file_pos = cleaned.find("### File:")

    # FIX: If no file blocks exist, search the entire text for a tree structure
    header_text = cleaned[:first_file_pos].strip() if first_file_pos != -1 else cleaned
    
    # FIX: Replaced broken regex with a valid snippet block extractor
    tree_match = re.search(r'```(?:[\w+-]+)?\r?\n([\s\S]*?)```', header_text)
    if tree_match:
        result_dict["tree"] = tree_match.group(1).strip()

    if first_file_pos != -1:
        # Parse individual file blocks
        file_blocks = re.findall(r'(?:##|###) File: ([\s\S]*?)(?=(?:##|###) File:|$)', cleaned)
        for block in file_blocks:
            lines = block.strip().splitlines()
            if len(lines) > 1:
                # FIX: Cleaned up potential trailing markdown formatting from filename line
                filename = lines[0].replace('`', '').strip()
                content = '\n'.join(lines[1:]).strip()
                
                # FIX: Swapped out aggressive MULTILINE regex to safely preserve nested markdown code blocks
                content = re.sub(r'^```\w*\r?\n|```$', '', content).strip()
                result_dict["files"][filename] = content
                
    return result_dict
