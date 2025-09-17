# github-repo-setup

Automated cloning, virtualenv, VS Code configuration (Copilot disabled), and initial file preparation.

---

## What this script does
- Clones a repo via `git@` (SSH) when a repo URL is provided.
- Creates an empty `secrets.toml` (if missing).
- Copies `initial_conditions_default.yaml` → `initial_conditions.yaml` (if source exists).
- Creates `.vscode/settings.json` that disables Copilot and points VS Code to `.venv`.
- Creates `.venv`, installs `requirements.txt` (if present), and wires terminals to use it.
- Works on Windows, macOS, and Linux from any path. Safe to re-run.

---

## Prerequisites
- **Git** (in your PATH)  
- **Python 3.8+** (the interpreter you want for the venv)  
- **VS Code** + the official *Python* extension  
- **SSH access** to your repo (e.g., GitHub SSH keys set up)  

---

## Quickstart

### Option A — Bootstrap (clone + setup)
From any folder, run the script to clone via SSH and fully set up the workspace:

```bash
# macOS / Linux
python3 setup_workspace.py --repo git@github.com:your-org/your-repo.git --dest my-project

# Windows (PowerShell)
py setup_workspace.py --repo git@github.com:your-org/your-repo.git --dest my-project
