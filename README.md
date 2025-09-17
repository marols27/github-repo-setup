# github-repo-setup

Automates cloning, virtual environment creation, dependency installation, and VS Code configuration — with **GitHub Copilot disabled** at the workspace level by default.

---

## Contents

- [What the script does](#what-the-script-does)
- [Warnings & Prerequisites](#warnings--prerequisites)
- [Installation](#installation)
  - [Windows (PowerShell)](#windows-powershell)
  - [macOS / Linux (bash/zsh)](#macos--linux-bashzsh)
  - [Examples](#examples)
- [Verify](#verify)

---

## What the script does

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

> Workspace settings do not uninstall extensions. They disable Copilot features for this workspace and discourage enabling those extensions here.

---

## Warnings & Prerequisites

### Warnings
- The installation commands below **execute a remote script**. Use only with repositories you **trust** (e.g., your own organization).
- SSH cloning requires your GitHub SSH key to be set up and authorized for the target repo.

### Prerequisites
- **Git** installed (`git --version`)
- **Python 3.8+** on your PATH (Windows: `py -V`, macOS/Linux: `python3 -V`)
- **VS Code** with the official **Python** extension

---

## Installation

### Windows (PowerShell)

> PowerShell aliases `curl` to `Invoke-WebRequest`, which doesn’t support `-fsSL`. Use **`curl.exe`** explicitly.

**Clone + setup (recommended one‑liner):**
```powershell
curl.exe -fsSL https://raw.githubusercontent.com/<USER>/<REPO>/<BRANCH>/setup_workspace.py `
| py - --repo git@github.com:<ORG>/<PROJECT>.git --dest my-project
```

**Setup only (already in a cloned repo folder):**
```powershell
curl.exe -fsSL https://raw.githubusercontent.com/<USER>/<REPO>/<BRANCH>/setup_workspace.py | py -
```

If you don’t have real `curl.exe`, use this fallback:
```powershell
$u="https://raw.githubusercontent.com/<USER>/<REPO>/<BRANCH>/setup_workspace.py"; `
$f=Join-Path $env:TEMP ("setup_workspace_{0}.py" -f ([guid]::NewGuid())); `
Invoke-WebRequest -Uri $u -UseBasicParsing -OutFile $f; `
py $f --repo git@github.com:<ORG>/<PROJECT>.git --dest my-project; `
Remove-Item $f -Force
```

---

### macOS / Linux (bash/zsh)

**Clone + setup (recommended one‑liner):**
```bash
curl -fsSL https://raw.githubusercontent.com/<USER>/<REPO>/<BRANCH>/setup_workspace.py | python3 - --repo git@github.com:<ORG>/<PROJECT>.git --dest my-project
```

**Setup only (already in a cloned repo folder):**
```bash
curl -fsSL https://raw.githubusercontent.com/<USER>/<REPO>/<BRANCH>/setup_workspace.py | python3 -
```

---

### Examples

Replace placeholders with your values:
- `<USER>` = your GitHub username or org
- `<REPO>` = the repo that contains **setup_workspace.py**
- `<BRANCH>` = branch name (often `main`)
- `<ORG>/<PROJECT>` = the repo you want to **clone** when using `--repo`

**Example (clone + setup):**
```bash
# macOS / Linux
curl -fsSL https://raw.githubusercontent.com/myuser/github-repo-setup/main/setup_workspace.py | python3 - --repo git@github.com:myorg/myproject.git --dest my-project
```

```powershell
# Windows PowerShell
curl.exe -fsSL https://raw.githubusercontent.com/myuser/github-repo-setup/main/setup_workspace.py `
| py - --repo git@github.com:myorg/myproject.git --dest my-project
```

**Example (setup only, inside an existing repo folder):**
```bash
# macOS / Linux
curl -fsSL https://raw.githubusercontent.com/myuser/github-repo-setup/main/setup_workspace.py | python3 -
```
```powershell
# Windows PowerShell
curl.exe -fsSL https://raw.githubusercontent.com/myuser/github-repo-setup/main/setup_workspace.py | py -
```

> For extra safety, you can pin to a **specific commit** by replacing `<BRANCH>` with a commit SHA.

---

## Verify

After running the installer:
1. Open the project folder in VS Code (`code .`).
2. Check the interpreter in the status bar points to `.venv`  
   (or run *“Python: Select Interpreter”* → choose the one under `.venv`).
3. Open a new integrated terminal and confirm:
   ```bash
   python -V
   pip -V
   ```
4. Press **F5** (or Run ▶) on a Python file to debug with **debugpy**.
