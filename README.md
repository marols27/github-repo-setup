# github-repo-setup

Automates cloning, venv creation, dependency install, and VS Code configuration — with **Copilot disabled** at the workspace level.

---

## What this script does

- **Clone via SSH** (optional): `--repo git@github.com:org/repo.git --dest my-project`
- **Create secrets & defaults**:
  - `secrets.toml` (empty if missing)
  - copy `initial_conditions_default.yaml` → `initial_conditions.yaml` (if present)
- **Create `.venv`** and install `requirements.txt` (if present)
- **Configure VS Code**:
  - `.vscode/settings.json` points Python to `.venv`
  - **Copilot completions + chat + codebase search/indexing disabled**
  - `.vscode/launch.json` uses **`debugpy`** for “Python: Current File”
  - `.vscode/extensions.json` recommends **Pylint** and flags Copilot extensions as **not recommended**

> Note: Workspace settings can’t *uninstall* or *force-disable* an already installed extension.  
> This setup disables Copilot **features** and clearly discourages enabling those extensions in this workspace.

---

## Prerequisites

- Git
- Python 3.8+ (the interpreter you want for the venv)
- VS Code + the official **Python** extension

---

## Quickstart

### A) Bootstrap (clone + setup)

```bash
# macOS / Linux
python3 setup_workspace.py --repo git@github.com:your-org/your-repo.git --dest my-project

# Windows (PowerShell)
py setup_workspace.py --repo git@github.com:your-org/your-repo.git --dest my-project
