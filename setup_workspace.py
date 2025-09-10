#!/usr/bin/env python3
"""
VS Code Python workspace setup script (Windows/macOS/Linux)

Usage:
  - Bootstrap + setup:
      python setup_workspace.py --repo git@github.com:your-org/your-repo.git --dest my-project

  - Setup only (already inside repo):
      python setup_workspace.py
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
        subprocess.run(
            ["git", "--version"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True,
        )
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

    term_env_windows = {
        "VIRTUAL_ENV": "${workspaceFolder}\\.venv",
        "PATH": "${workspaceFolder}\\.venv\\Scripts;${env:PATH}",
    }
    term_env_unix = {
        "VIRTUAL_ENV": "${workspaceFolder}/.venv",
        "PATH": "${workspaceFolder}/.venv/bin:${env:PATH}",
    }

    # FULL Copilot shutdown + Python defaults
    settings = {
        # ── Disable ALL Copilot completions ──
        "github.copilot.enable": {
            "*": False,
            "plaintext": False,
            "markdown": False,
            "scminput": False,
        },
        "github.copilot.nextEditSuggestions.enabled": False,
        "editor.inlineSuggest.edits.allowCodeShifting": "never",
        "github.copilot.inlineSuggest.enable": False,

        # ── Disable Copilot Chat & indexing ──
        "chat.commandCenter.enabled": False,
        "chat.agent.enabled": False,
        "chat.mcp.enabled": False,
        "github.copilot.chat.enable": False,
        "github.copilot.chat.codesearch.enabled": False,
        "github.copilot.chat.editor.temporalContext.enabled": False,
        "github.copilot.chat.edits.suggestRelatedFilesFromGitHistory": False,
        "github.copilot.chat.newWorkspaceCreation.enabled": False,
        "github.copilot.chat.startDebugging.enabled": False,
        "github.copilot.chat.copilotDebugCommand.enabled": False,
        "github.copilot.chat.generateTests.codeLens": False,
        "github.copilot.chat.setupTests.enabled": False,
        "github.copilot.chat.codeGeneration.useInstructionFiles": False,
        "chat.promptFiles": False,
        "chat.modeFilesLocations": {},

        # ── Hide AI-related settings in UI ──
        "workbench.settings.showAISearchToggle": False,
        "search.searchView.semanticSearchBehavior": "manual",

        # ── Python / venv config ──
        "python.defaultInterpreterPath": str(venv_python).replace(str(repo_root), "${workspaceFolder}"),
        "python.terminal.activateEnvironment": True,
        "terminal.integrated.env.windows": term_env_windows,
        "terminal.integrated.env.osx": term_env_unix,
        "terminal.integrated.env.linux": term_env_unix,
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

    # Basic Python launch config
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
                "env": {"VIRTUAL_ENV": "${workspaceFolder}/.venv"},
            }
        ],
    }
    launch_path.write_text(json.dumps(launch, indent=2), encoding="utf-8")
    print(f"✅ Wrote {launch_path.relative_to(repo_root)}")


def main():
    parser = argparse.ArgumentParser(description="VS Code Python workspace setup")
    parser.add_argument("--repo", help="SSH repo URL (e.g., git@github.com:org/repo.git)")
    parser.add_argument("--dest", help="Destination folder for clone (defaults to repo name)")
    args = parser.parse_args()

    if args.repo:
        if args.dest:
            dest = Path(args.dest).resolve()
        else:
            name = args.repo.rstrip("/").split("/")[-1]
            if name.endswith(".git"):
                name = name[:-4]
            dest = (Path.cwd() / name).resolve()
        repo_root = clone_repo(args.repo, dest)
    else:
        repo_root = detect_repo_root(Path.cwd())
        if not repo_root:
            sys.exit("Error: Not inside a Git repository and no --repo was provided.")

    print(f"📁 Working in repo: {repo_root}")
    ensure_secrets(repo_root)
    copy_initial_conditions(repo_root)
    create_venv_and_install(repo_root)
    write_vscode(repo_root)

    print("\n🎉 Workspace setup complete.")
    print("Open the folder in VS Code and it should auto-select .venv and have Copilot disabled for this workspace.")


if __name__ == "__main__":
    main()
