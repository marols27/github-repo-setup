# github-repo-setup

Automates cloning, venv creation, dependency install, and VS Code configuration — with **Copilot disabled** at the workspace level.

---

## Installation (recommended)

You can run the setup script directly from GitHub **without downloading anything first**.  

Copy-paste this one-liner into your terminal (works on macOS, Linux, and Windows PowerShell):

```bash
curl -fsSL https://raw.githubusercontent.com/<USER>/<REPO>/<BRANCH>/setup_workspace.py | python -
```

Replace:
- `<USER>` with your GitHub username or org  
- `<REPO>` with your repository name  
- `<BRANCH>` with your branch (often `main` or `master`)  

Examples:

```bash
# clone + setup
curl -fsSL https://raw.githubusercontent.com/myuser/myrepo/main/setup_workspace.py | python - --repo git@github.com:myorg/myproject.git --dest my-project

# setup only (already cloned repo)
curl -fsSL https://raw.githubusercontent.com/myuser/myrepo/main/setup_workspace.py | python -
```

⚠️ **Security note:** Only use this method with repositories you trust (e.g., your own). It executes the remote script directly.

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
