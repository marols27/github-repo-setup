#!/usr/bin/env python3
"""
VS Code Python workspace setup script (Windows/macOS/Linux)

Usage:
  python setup_workspace.py
"""

import argparse
import json
import platform
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional, List, Dict, Any


def run(cmd: List[str], cwd: Optional[Path] = None, check: bool = True) -> int:
    """Run a subprocess command and return its exit code."""
    print(f"→ Running: {' '.join(cmd)}" + (f"  (cwd={cwd})" if cwd else ""))
    result: subprocess.CompletedProcess[Any] = subprocess.run(cmd, cwd=cwd, check=check)
    return int(result.returncode)


def detect_repo_root(start: Path) -> Optional[Path]:
    """Walk upward from a starting path to find the nearest Git repository root."""
    p: Path = start.resolve()
    for _ in range(5):
        if (p / ".git").is_dir():
            return p
        if p.parent == p:
            break
        p = p.parent
    return None


def ensure_secrets(repo_root: Path) -> None:
    """Ensure an empty `secrets.toml` exists at the repository root."""
    secrets: Path = repo_root / "secrets.toml"
    if not secrets.exists():
        _ = secrets.write_text("", encoding="utf-8")
        print(f"✅ Created empty {secrets.relative_to(repo_root)}")
    else:
        print(f"ℹ️ {secrets.relative_to(repo_root)} already exists; leaving it as-is.")


def copy_initial_conditions(repo_root: Path) -> None:
    """
    Find all `initial_conditions_default.yaml` files in the repo and copy them
    to `initial_conditions.yaml` in the same directory if not already present.
    """
    matches: List[Path] = list(repo_root.rglob("initial_conditions_default.yaml"))
    if not matches:
        print("ℹ️ No initial_conditions_default.yaml found anywhere; skipping copy.")
        return

    for src in matches:
        dst: Path = src.with_name("initial_conditions.yaml")
        if not dst.exists():
            shutil.copy2(src, dst)
            print(f"✅ Copied {src.relative_to(repo_root)} → {dst.name}")
        else:
            print(f"ℹ️ {dst.relative_to(repo_root)} already exists; leaving it as-is.")


def python_in_venv(repo_root: Path) -> Path:
    """Return the path to the Python executable inside `.venv` for this OS."""
    system_name: str = platform.system().lower()
    if system_name.startswith("win"):
        return repo_root / ".venv" / "Scripts" / "python.exe"
    else:
        return repo_root / ".venv" / "bin" / "python"


def create_venv_and_install(repo_root: Path) -> None:
    """Create `.venv` if missing and install dependencies from requirements.txt."""
    venv_python: Path = python_in_venv(repo_root)
    venv_dir: Path = venv_python.parent.parent

    if not venv_dir.exists():
        base_py: Path = Path(sys.executable)
        print(f"Creating venv with {base_py}")
        run([str(base_py), "-m", "venv", str(venv_dir)])
        print(f"✅ Created virtual environment at {venv_dir.relative_to(repo_root)}")
    else:
        print(f"ℹ️ Virtual environment already exists at {venv_dir.relative_to(repo_root)}")

    req: Path = repo_root / "requirements.txt"
    if req.exists():
        print("Installing requirements...")
        _ = run(
            [
                str(venv_python),
                "-m",
                "pip",
                "install",
                "--upgrade",
                "pip",
                "wheel",
                "setuptools"
            ]
        )
        _ = run([str(venv_python), "-m", "pip", "install", "-r", str(req)])
        print("✅ Installed requirements")
    else:
        print("ℹ️ No requirements.txt found; skipping dependency install.")


def write_extensions_json(vscode_dir: Path) -> None:
    """Write `.vscode/extensions.json` with pylint recommendation and Copilot discouraged."""
    path: Path = vscode_dir / "extensions.json"
    merged: Dict[str, Any] = {
        "recommendations": ["ms-python.pylint"],
        "unwantedRecommendations": ["GitHub.copilot", "GitHub.copilot-chat"],
    }
    _ = path.write_text(json.dumps(merged, indent=2), encoding="utf-8")
    print(f"✅ Wrote {path.relative_to(vscode_dir.parent)}")


def write_vscode(repo_root: Path) -> None:
    """Create `.vscode/settings.json` + `.vscode/launch.json` and discourage Copilot."""
    vscode: Path = repo_root / ".vscode"
    _ = vscode.mkdir(exist_ok=True)

    venv_python: Path = python_in_venv(repo_root)

    settings: Dict[str, Any] = {
        "python.defaultInterpreterPath": str(venv_python).replace(
            str(repo_root),
            "${workspaceFolder}"
        ),
        "python.terminal.activateEnvironment": True,
        "terminal.integrated.env.windows": {
            "VIRTUAL_ENV": "${workspaceFolder}\\.venv",
            "PATH": "${workspaceFolder}\\.venv\\Scripts;${env:PATH}",
        },
        "terminal.integrated.env.osx": {
            "VIRTUAL_ENV": "${workspaceFolder}/.venv",
            "PATH": "${workspaceFolder}/.venv/bin:${env:PATH}",
        },
        "terminal.integrated.env.linux": {
            "VIRTUAL_ENV": "${workspaceFolder}/.venv",
            "PATH": "${workspaceFolder}/.venv/bin:${env:PATH}",
        },
        # Copilot restrictions
        "github.copilot.enable": {
            "*": False,
            "plaintext": False,
            "markdown": False,
            "scminput": False
        },
        "github.copilot.inlineSuggest.enable": False,
        "github.copilot.nextEditSuggestions.enabled": False,
        "editor.inlineSuggest.edits.allowCodeShifting": "never",
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
        "workbench.settings.showAISearchToggle": False,
        "search.searchView.semanticSearchBehavior": "manual",
    }

    _ = (vscode / "settings.json").write_text(json.dumps(settings, indent=2), encoding="utf-8")
    print("✅ Wrote .vscode/settings.json")

    launch: Dict[str, Any] = {
        "version": "0.2.0",
        "configurations": [
            {
                "name": "Python: Current File",
                "type": "debugpy",
                "request": "launch",
                "program": "${file}",
                "console": "integratedTerminal",
                "justMyCode": True,
                "env": {"VIRTUAL_ENV": "${workspaceFolder}/.venv"},
            }
        ],
    }
    _ = (vscode / "launch.json").write_text(json.dumps(launch, indent=2), encoding="utf-8")
    print("✅ Wrote .vscode/launch.json")

    write_extensions_json(vscode)


def main() -> None:
    """Main entrypoint: run workspace setup inside an already cloned repo."""
    parser = argparse.ArgumentParser(description="VS Code Python workspace setup")
    _ = parser.parse_args()

    repo_root: Optional[Path] = detect_repo_root(Path.cwd())
    if not repo_root:
        sys.exit("Error: Not inside a Git repository.")

    print(f"📁 Working in repo: {repo_root}")
    ensure_secrets(repo_root)
    copy_initial_conditions(repo_root)
    create_venv_and_install(repo_root)
    write_vscode(repo_root)

    print("\n🎉 Workspace setup complete.")
    print("Open the folder in VS Code, it should auto-select `.venv` and have Copilot disabled.")


if __name__ == "__main__":
    main()
