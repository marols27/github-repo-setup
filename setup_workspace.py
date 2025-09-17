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
import platform
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional, List, Dict, Any


def run(cmd: List[str], cwd: Optional[Path] = None, check: bool = True) -> int:
    """
    Run a subprocess command and optionally ensure success.

    Parameters
    ----------
    cmd : list[str]
        Command and arguments to execute 
        (e.g., ["python", "-m", "pip", "install", "-r", "requirements.txt"]).
    cwd : Path | None
        Working directory to execute the command in. 
        If None, uses the current process working directory.
    check : bool
        If True, raise subprocess.CalledProcessError when the command exits with a non-zero code.

    Returns
    -------
    int
        The process return code (0 on success).
    """
    cmd_display: str = " ".join(cmd)
    print(f"→ Running: {cmd_display}" + (f"  (cwd={cwd})" if cwd else ""))
    result: subprocess.CompletedProcess[Any] = subprocess.run(cmd, cwd=cwd, check=check)
    return int(result.returncode)


def have_git() -> bool:
    """
    Check whether Git is available on PATH.

    Returns
    -------
    bool
        True if the `git` executable can be invoked, False otherwise.
    """
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
    """
    Clone a Git repository via SSH into the given destination directory.

    Parameters
    ----------
    repo_ssh : str
        SSH URL of the repository (e.g., "git@github.com:org/repo.git").
    dest_dir : Path
        Destination directory to clone into. Will be created if it does not exist.

    Returns
    -------
    Path
        The destination directory path (whether cloned into or skipped).
    """
    if not have_git():
        sys.exit("Error: 'git' not found on PATH. Please install Git and try again.")

    if dest_dir.exists() and any(dest_dir.iterdir()):
        print(f"⚠️ Destination '{dest_dir}' already exists and is not empty; skipping clone.")
        return dest_dir

    _parent: Path = dest_dir.parent
    _parent.mkdir(parents=True, exist_ok=True)
    run(["git", "clone", repo_ssh, str(dest_dir)])
    return dest_dir


def detect_repo_root(start: Path) -> Optional[Path]:
    """
    Walk upward from a starting path to find the nearest Git repository root.

    Parameters
    ----------
    start : Path
        Starting directory to search from.

    Returns
    -------
    Optional[Path]
        The repository root containing a `.git` directory, or None if not found
        within a limited number of parent directories.
    """
    p: Path = start.resolve()
    for _ in range(5):
        git_dir: Path = p / ".git"
        if git_dir.is_dir():
            return p
        if p.parent == p:
            break
        p = p.parent
    return None


def ensure_secrets(repo_root: Path) -> None:
    """
    Ensure an empty `secrets.toml` exists at the repository root.

    Parameters
    ----------
    repo_root : Path
        The repository root directory.

    Returns
    -------
    None
    """
    secrets: Path = repo_root / "secrets.toml"
    if not secrets.exists():
        _ = secrets.write_text("", encoding="utf-8")
        print(f"✅ Created empty {secrets.relative_to(repo_root)}")
    else:
        print(f"ℹ️ {secrets.relative_to(repo_root)} already exists; leaving it as-is.")


def copy_initial_conditions(repo_root: Path) -> None:
    """
    Copy default initial conditions to a working file if needed.

    Copies `initial_conditions_default.yaml` → `initial_conditions.yaml`
    only if the source exists and the target does not.

    Parameters
    ----------
    repo_root : Path
        The repository root directory.

    Returns
    -------
    None
    """
    src: Path = repo_root / "initial_conditions_default.yaml"
    dst: Path = repo_root / "initial_conditions.yaml"
    if src.exists():
        if not dst.exists():
            shutil.copy2(src, dst)
            print(f"✅ Copied {src.name} → {dst.name}")
        else:
            print(f"ℹ️ {dst.name} already exists; leaving it as-is.")
    else:
        print("ℹ️ initial_conditions_default.yaml not found; skipping copy.")


def python_in_venv(repo_root: Path) -> Path:
    """
    Compute the path to the Python executable inside `.venv` for the current OS.

    Parameters
    ----------
    repo_root : Path
        The repository root directory.

    Returns
    -------
    Path
        Path to `.venv/Scripts/python.exe` on Windows, or `.venv/bin/python` on POSIX.
    """
    system_name: str = platform.system().lower()
    if system_name.startswith("win"):
        return repo_root / ".venv" / "Scripts" / "python.exe"
    else:
        return repo_root / ".venv" / "bin" / "python"


def create_venv_and_install(repo_root: Path) -> None:
    """
    Create a virtual environment in `.venv` and install dependencies.

    - Creates the venv using the current interpreter (`sys.executable`) if it does not exist.
    - Upgrades pip/wheel/setuptools.
    - Installs packages listed in `requirements.txt` if the file is present.

    Parameters
    ----------
    repo_root : Path
        The repository root directory.

    Returns
    -------
    None
    """
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
    """
    Create or update `.vscode/extensions.json` with workspace recommendations
    and explicit discouragement of Copilot extensions.

    Adds:
      - recommendations:    ms-python.pylint
      - unwantedRecommendations: GitHub.copilot, GitHub.copilot-chat

    Parameters
    ----------
    vscode_dir : Path
        Path to the `.vscode` directory.

    Returns
    -------
    None
    """
    path: Path = vscode_dir / "extensions.json"
    payload: Dict[str, Any] = {
        "recommendations": [
            "ms-python.pylint"
        ],
        "unwantedRecommendations": [
            "GitHub.copilot",
            "GitHub.copilot-chat",
        ],
    }

    try:
        if path.exists():
            existing_text: str = path.read_text(encoding="utf-8")
            existing: Dict[str, Any] = json.loads(existing_text)
        else:
            existing = {}
    except Exception:
        existing = {}

    # Merge: keep existing recommendations, ensure pylint is included;
    # merge + sort unwantedRecommendations with Copilot IDs added.
    existing_recs: List[str] = list(existing.get("recommendations", []))
    merged_recs: List[str] = sorted(set(existing_recs) | set(payload["recommendations"]))

    existing_unwanted: List[str] = list(existing.get("unwantedRecommendations", []))
    merged_unwanted: List[str] = sorted(set(existing_unwanted) 
                                        | set(payload["unwantedRecommendations"]))

    merged: Dict[str, Any] = {
        "recommendations": merged_recs,
        "unwantedRecommendations": merged_unwanted,
    }

    _ = path.write_text(json.dumps(merged, indent=2), encoding="utf-8")
    print(f"✅ Wrote {path.relative_to(vscode_dir.parent)}")



def write_vscode(repo_root: Path) -> None:
    """
    Create or update VS Code workspace configuration under `.vscode/`.

    Writes:
      - `.vscode/settings.json` with Python/venv defaults **and Copilot restrictions**:
        completions, chat, codebase search/indexing, MCP integrations are disabled.
      - `.vscode/launch.json` using the modern `debugpy` debug type.
      - `.vscode/extensions.json` recommending Pylint and discouraging Copilot.

    Parameters
    ----------
    repo_root : Path
        The repository root directory.

    Returns
    -------
    None
    """
    vscode: Path = repo_root / ".vscode"
    _ = vscode.mkdir(exist_ok=True)
    settings_path: Path = vscode / "settings.json"

    venv_python: Path = python_in_venv(repo_root)

    # Terminal env so any new terminal picks up the venv by default
    term_env_windows: Dict[str, str] = {
        "VIRTUAL_ENV": "${workspaceFolder}\\.venv",
        "PATH": "${workspaceFolder}\\.venv\\Scripts;${env:PATH}",
    }
    term_env_unix: Dict[str, str] = {
        "VIRTUAL_ENV": "${workspaceFolder}/.venv",
        "PATH": "${workspaceFolder}/.venv/bin:${env:PATH}",
    }

    # Copilot restrictions are restored here (completions + chat + code search/indexing).
    settings: Dict[str, Any] = {
        # Python / venv config
        "python.defaultInterpreterPath": 
            str(venv_python).replace(str(repo_root), "${workspaceFolder}"),
        "python.terminal.activateEnvironment": True,
        "terminal.integrated.env.windows": term_env_windows,
        "terminal.integrated.env.osx": term_env_unix,
        "terminal.integrated.env.linux": term_env_unix,

        # ── Disable ALL Copilot code suggestions ──
        "github.copilot.enable": {
            "*": False,
            "plaintext": False,
            "markdown": False,
            "scminput": False,
        },
        "github.copilot.inlineSuggest.enable": False,
        "github.copilot.nextEditSuggestions.enabled": False,
        "editor.inlineSuggest.edits.allowCodeShifting": "never",

        # ── Disable Copilot Chat + indexing/context ingestion ──
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

        # Optional: reduce AI/semantic search noise in UI
        "workbench.settings.showAISearchToggle": False,
        "search.searchView.semanticSearchBehavior": "manual",
    }

    if settings_path.exists():
        try:
            existing_text: str = settings_path.read_text(encoding="utf-8")
            existing: Dict[str, Any] = json.loads(existing_text)
        except Exception:
            existing = {}
        merged: Dict[str, Any] = {**existing, **settings}
    else:
        merged = settings

    _ = settings_path.write_text(json.dumps(merged, indent=2), encoding="utf-8")
    print(f"✅ Wrote {settings_path.relative_to(repo_root)}")

    # Debug: keep 'debugpy'
    launch_path: Path = vscode / "launch.json"
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
    _ = launch_path.write_text(json.dumps(launch, indent=2), encoding="utf-8")
    print(f"✅ Wrote {launch_path.relative_to(repo_root)}")

    # Recommend pylint and discourage Copilot
    write_extensions_json(vscode)



def main() -> None:
    """
    Entry point for the setup script.

    Parses command-line arguments, resolves/creates the target repository folder,
    prepares initial files, creates a virtual environment and installs dependencies,
    and writes VS Code workspace configuration.

    Returns
    -------
    None
    """
    parser: argparse.ArgumentParser = argparse.ArgumentParser(
        description="VS Code Python workspace setup"
    )
    _ = parser.add_argument("--repo", help="SSH repo URL (e.g., git@github.com:org/repo.git)")
    _ = parser.add_argument("--dest", help="Destination folder for clone (defaults to repo name)")
    args: argparse.Namespace = parser.parse_args()

    repo_root: Path
    if args.repo:
        if args.dest:
            dest: Path = Path(args.dest).resolve()
        else:
            raw_name: str = args.repo.rstrip("/")
            last: str = raw_name.split("/")[-1]
            name: str = last[:-4] if last.endswith(".git") else last
            dest = (Path.cwd() / name).resolve()
        repo_root = clone_repo(args.repo, dest)
    else:
        maybe_root: Optional[Path] = detect_repo_root(Path.cwd())
        if not maybe_root:
            sys.exit("Error: Not inside a Git repository and no --repo was provided.")
        repo_root = maybe_root

    print(f"📁 Working in repo: {repo_root}")
    ensure_secrets(repo_root)
    copy_initial_conditions(repo_root)
    create_venv_and_install(repo_root)
    write_vscode(repo_root)

    print("\n🎉 Workspace setup complete.")
    print(
        "Open the folder in VS Code; it should auto-select .venv, "
        "recommend Pylint, and use the debugpy adapter for 'Python: Current File'."
        )


if __name__ == "__main__":
    main()
