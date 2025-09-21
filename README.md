# github-repo-setup

Automates virtual environment creation, dependency installation, and VS Code configuration — with **GitHub Copilot disabled** at the workspace level.

---

## Contents

- [What the script does](#what-the-script-does)
- [Warnings & Prerequisites](#warnings--prerequisites)
- [Installation](#installation)
- [Verify](#verify)

---

## What the script does

- **Create secrets & defaults**:
  - `secrets.toml` (empty if missing)
  - copy any `initial_conditions_default.yaml` → `initial_conditions.yaml` in the same folder
- **Create `.venv`** and install `requirements.txt` (if present)
- **Configure VS Code**:
  - `.vscode/settings.json` points Python to `.venv`
  - **Copilot completions + chat + indexing disabled**
  - `.vscode/launch.json` uses **`debugpy`**
  - `.vscode/extensions.json` recommends **Pylint** and discourages Copilot extensions

---

## Warnings & Prerequisites

### Warnings
- This script modifies `.vscode/` configs and may overwrite existing settings.
- Copilot is disabled for this workspace, but the extension itself is not uninstalled.

### Prerequisites
- **Git** (to clone your repo)
- **Python 3.8+**
- **VS Code** with the **Python** extension

---

## Installation

Clone your repo as normal, then run the script inside the repo root:

```bash
git clone git@github.com:<ORG>/<PROJECT>.git
cd <PROJECT>
python3 setup_workspace.py
