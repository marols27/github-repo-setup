#!/usr/bin/env python3
"""
VS Code Python workspace setup script (Windows/macOS/Linux)

Usage:
  - Bootstrap + setup:
      python setup_workspace.py --repo git@github.com:your-org/your-repo.git --dest my-project

  - Setup only (already inside repo):
      python setup_workspace.py

What it does:
  * Optionally clones the repo via SSH to --dest (or repo name) if --repo is given
  * Ensures an empty secrets.toml exists
  * Copies initial_conditions_default.yaml -> initial_conditions.yaml if source exists
  * Creates .vscode/settings.json:
      - Disables all GitHub Copilot features in this workspace
      - Points Python extension at the .venv interpreter
      - Makes integrated terminals use the .venv by default
  * Creates .venv and installs requirements.txt if present
"""

import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

def run(cmd, cwd=None, check=True):
    print(f"→ Running: {' '.join(cmd)}" + (f"  (cwd={cwd})" if cwd else ""))
    result = subprocess.run(cmd, cwd=cwd, check=check)
    return result.returncode

def have_git():
    try:
        subprocess.run(["git", "--version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        return True
    except Exception:
        return False

def clone_repo(repo_ssh: str, dest_dir: Path) -> Path:
    if not have_git():
        sys.exit("Error: 'git' not found on PATH. Please install Git and try again.")

    if dest_dir.exists() and any(dest_dir.iterdir()):
        print(f"⚠️ Destination '{dest_dir}' already exists and is not empty; skipping clone.")
        return dest_dir

    dest_dir.parent.mkdir(parents=True, exist_ok=True)
    run(["git", "clone", repo_ssh, str(dest_dir)])
    return dest_dir

def detect_repo_root(start: Path) -> Path | None:
    p = start.resolve()
    for _ in range(5):
        if (p / ".git").is_dir():
            return p
        if p.parent == p:
            break
        p = p.parent
    return None

def ensure_secrets(repo_root: Path):
    secrets = repo_root / "secrets.toml"
    if not secrets.exists():
        secrets.write_text("", encoding="utf-8")
        print(f"✅ Created empty {secrets.relative_to(repo_root)}")
    else:
        print(f"ℹ️ {secrets.relative_to(repo_root)} already exists; leaving it as-is.")

def copy_initial_conditions(repo_root: Path):
    src = repo_root / "initial_conditions_default.yaml"
    dst = repo_root / "initial_conditions.yaml"
    if src.exists():
        if not dst.exists():
            shutil.copy2(src, dst)
            print(f"✅ Copied {src.name} → {dst.name}")
        else:
            print(f"ℹ️ {dst.name} already exists; leaving it as-is.")
    else:
        print("ℹ️ initial_conditions_default.yaml not found; skipping copy.")

def python_in_venv(repo_root: Path) -> Path:
    if platform.system().lower().startswith("win"):
        return repo_root / ".venv" / "Scripts" / "python.exe"
    else:
        return repo_root / ".venv" / "bin" / "python"

def create_venv_and_install(repo_root: Path):
    venv_python = python_in_venv(repo_root)
    venv_dir = venv_python.parent.parent

    if not venv_dir.exists():
        # Prefer the same interpreter running this script
        base_py = Path(sys.executable)
        print(f"Creating venv with {base_py}")
        run([str(base_py), "-m", "venv", str(venv_dir)])
        print(f"✅ Created virtual environment at {venv_dir.relative_to(repo_root)}")
    else:
        print(f"ℹ️ Virtual environment already exists at {venv_dir.relative_to(repo_root)}")

    req = repo_root / "requirements.txt"
    if req.exists():
        print("Installing requirements...")
        run([str(venv_python), "-m", "pip", "install", "--upgrade", "pip", "wheel", "setuptools"])
        run([str(venv_python), "-m", "pip", "install", "-r", str(req)])
        print("✅ Installed requirements")
    else:
        print("ℹ️ No requirements.txt found; skipping dependency install.")

def write_vscode(repo_root: Path):
    vscode = repo_root / ".vscode"
    vscode.mkdir(exist_ok=True)
    settings_path = vscode / "settings.json"

    venv_python = python_in_venv(repo_root)
    # terminal env so any new terminal picks up the venv by default
    term_env_windows = {
        "VIRTUAL_ENV": "${workspaceFolder}\\.venv",
        "PATH": "${workspaceFolder}\\.venv\\Scripts;${env:PATH}"
    }
    term_env_unix = {
        "VIRTUAL_ENV": "${workspaceFolder}/.venv",
        "PATH": "${workspaceFolder}/.venv/bin:${env:PATH}"
    }

    # Disable Copilot features for this workspace
    settings = {
      # ── Disable ALL Copilot code suggestions ─────────────────────────────────────
      "github.copilot.enable": { "*": false, "plaintext": false, "markdown": false, "scminput": false },
      "github.copilot.nextEditSuggestions.enabled": false,
      "editor.inlineSuggest.edits.allowCodeShifting": "never",
    
      # ── Hide Copilot UI entry points ─────────────────────────────────────────────
      "chat.commandCenter.enabled": false,                           // remove Copilot menu from title bar
      "github.copilot.inlineSuggest.enable": false,                  // legacy toggle (belt + suspenders)
    
      # ── Turn OFF Copilot Chat and anything that could reach your files ──────────
      "chat.agent.enabled": false,                                   // disable Agent mode entirely
      "chat.mcp.enabled": false,                                     // block MCP tool integrations
      "github.copilot.chat.codesearch.enabled": false,               // prevent #codebase remote/local search
      "github.copilot.chat.editor.temporalContext.enabled": false,   // no “recent files” context
      "github.copilot.chat.edits.suggestRelatedFilesFromGitHistory": false,
      "github.copilot.chat.newWorkspaceCreation.enabled": false,
      "github.copilot.chat.startDebugging.enabled": false,
      "github.copilot.chat.copilotDebugCommand.enabled": false,
      "github.copilot.chat.generateTests.codeLens": false,
      "github.copilot.chat.setupTests.enabled": false,
      "github.copilot.chat.codeGeneration.useInstructionFiles": false,
      "chat.promptFiles": false,
      "chat.modeFilesLocations": {},
    
      # ── Optional: keep the Copilot/AI stuff out of Settings UX & noise ──────────
      "workbench.settings.showAISearchToggle": false,
      "search.searchView.semanticSearchBehavior": "manual",
    
      # ── Your existing Python/venv settings (keep these) ──────────────────────────
      "python.defaultInterpreterPath": "${workspaceFolder}/.venv/bin/python",
      "python.terminal.activateEnvironment": true,
      "terminal.integrated.env.linux":   { "VIRTUAL_ENV": "${workspaceFolder}/.venv", "PATH": "${workspaceFolder}/.venv/bin:${env:PATH}" },
      "terminal.integrated.env.osx":     { "VIRTUAL_ENV": "${workspaceFolder}/.venv", "PATH": "${workspaceFolder}/.venv/bin:${env:PATH}" },
      "terminal.integrated.env.windows": { "VIRTUAL_ENV": "${workspaceFolder}\\.venv", "PATH": "${workspaceFolder}\\.venv\\Scripts;${env:PATH}" }
    }


    # Merge with existing settings if present
    if settings_path.exists():
        try:
            existing = json.loads(settings_path.read_text(encoding="utf-8"))
        except Exception:
            existing = {}
        merged = {**existing, **settings}
    else:
        merged = settings

    settings_path.write_text(json.dumps(merged, indent=2), encoding="utf-8")
    print(f"✅ Wrote {settings_path.relative_to(repo_root)}")

    # Provide a Python launch config that uses the chosen interpreter for "Run/Debug"
    launch_path = vscode / "launch.json"
    launch = {
        "version": "0.2.0",
        "configurations": [
            {
                "name": "Python: Current File",
                "type": "python",
                "request": "launch",
                "program": "${file}",
                "console": "integratedTerminal",
                "justMyCode": True,
                # The Python extension respects python.defaultInterpreterPath,
                # but we also set env to ensure venv is active when running.
                "env": {
                    "VIRTUAL_ENV": "${workspaceFolder}/.venv"
                }
            }
        ]
    }
    launch_path.write_text(json.dumps(launch, indent=2), encoding="utf-8")
    print(f"✅ Wrote {launch_path.relative_to(repo_root)}")

def maybe_copy_self_into_repo(repo_root: Path):
    """
    If this script is NOT already in the repo root, copy it there as setup_workspace.py
    so the project always ships with it.
    """
    here = Path(__file__).resolve()
    dest = repo_root / "setup_workspace.py"
    try:
        if here != dest.resolve():
            if not dest.exists():
                shutil.copy2(here, dest)
                print(f"✅ Placed a copy of this script at {dest.relative_to(repo_root)}")
    except Exception as e:
        print(f"ℹ️ Could not copy script into repo: {e}")

def main():
    parser = argparse.ArgumentParser(description="VS Code Python workspace setup")
    parser.add_argument("--repo", help="SSH repo URL (e.g., git@github.com:org/repo.git)")
    parser.add_argument("--dest", help="Destination folder for clone (defaults to repo name)")
    args = parser.parse_args()

    if args.repo:
        # Determine dest directory
        if args.dest:
            dest = Path(args.dest).resolve()
        else:
            # derive folder name from repo URL
            name = args.repo.rstrip("/").split("/")[-1]
            if name.endswith(".git"):
                name = name[:-4]
            dest = (Path.cwd() / name).resolve()
        repo_root = clone_repo(args.repo, dest)
    else:
        # No repo provided—assume we're inside a repo or below one.
        repo_root = detect_repo_root(Path.cwd())
        if not repo_root:
            sys.exit("Error: Not inside a Git repository and no --repo was provided.")

    print(f"📁 Working in repo: {repo_root}")
    maybe_copy_self_into_repo(repo_root)
    ensure_secrets(repo_root)
    copy_initial_conditions(repo_root)
    create_venv_and_install(repo_root)
    write_vscode(repo_root)

    print("\n🎉 Workspace setup complete.")
    print("Open the folder in VS Code and it should auto-select .venv and have Copilot disabled for this workspace.")

if __name__ == "__main__":
    main()
