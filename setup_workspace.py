#!/usr/bin/env python3
"""
VS Code Python workspace setup script (Windows/macOS/Linux)

Features:
  - Optional git clone via SSH (--repo, --dest)
  - Creates secrets.toml, copies initial_conditions_default.yaml -> initial_conditions.yaml
  - Auto-selects a safe Python for .venv based on requirements.txt
      * If the required Python (e.g. 3.11) isn't installed, downloads a portable CPython
        into .pythonrt/<ver>/ inside the repo and creates .venv from it (no system installs)
  - Installs requirements.txt (if present)
  - Writes .vscode/settings.json (Copilot completions/chat/indexing fully disabled)
  - Writes .vscode/launch.json and .vscode/extensions.json (unwantedRecommendations for Copilot)
  - Writes a repo .gitignore
  - Creates secure launchers:
        tools/code_secure.sh   (macOS/Linux)  -> opens VS Code with Copilot extensions disabled
        tools/code_secure.ps1  (Windows)
"""

import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
import tarfile
import urllib.request
from pathlib import Path
from typing import Optional


# ---------------------- shell helpers ----------------------

def run(cmd, cwd=None, check=True):
    print(f"→ Running: {' '.join(cmd)}" + (f"  (cwd={cwd})" if cwd else ""))
    result = subprocess.run(cmd, cwd=cwd, check=check)
    return result.returncode


def have_git() -> bool:
    try:
        subprocess.run(["git", "--version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        return True
    except Exception:
        return False


# ---------------------- repo helpers ----------------------

def clone_repo(repo_ssh: str, dest_dir: Path) -> Path:
    if not have_git():
        sys.exit("Error: 'git' not found on PATH. Please install Git and try again.")

    if dest_dir.exists() and any(dest_dir.iterdir()):
        print(f"⚠️ Destination '{dest_dir}' already exists and is not empty; skipping clone.")
        return dest_dir

    dest_dir.parent.mkdir(parents=True, exist_ok=True)
    run(["git", "clone", repo_ssh, str(dest_dir)])
    return dest_dir


def detect_repo_root(start: Path) -> Optional[Path]:
    p = start.resolve()
    for _ in range(6):
        if (p / ".git").is_dir():
            return p
        if p.parent == p:
            break
        p = p.parent
    return None


# ---------------------- initial files ----------------------

def ensure_secrets(repo_root: Path) -> None:
    secrets = repo_root / "secrets.toml"
    if not secrets.exists():
        secrets.write_text("", encoding="utf-8")
        print(f"✅ Created empty {secrets.relative_to(repo_root)}")
    else:
        print(f"ℹ️ {secrets.relative_to(repo_root)} already exists; leaving it as-is.")


def copy_initial_conditions(repo_root: Path) -> None:
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


# ---------------------- python/venv selection ----------------------

HEAVY_PKGS = {"numpy", "pandas", "scipy", "matplotlib", "scikit-learn", "torch", "tensorflow"}

def parse_requirements_for_heavy(req_path: Path) -> bool:
    if not req_path.exists():
        return False
    try:
        text = req_path.read_text(encoding="utf-8")
    except Exception:
        return False
    lines = [l.strip() for l in text.splitlines() if l.strip() and not l.strip().startswith("#")]
    for line in lines:
        # remove environment markers
        x = line.split(";", 1)[0]
        # extract name before version/extras
        name = (
            x.split("==", 1)[0].split(">=", 1)[0].split("<=", 1)[0]
             .split("!=", 1)[0].split("~=", 1)[0].split("[", 1)[0]
            .strip().lower()
        )
        base = name.replace("_", "-")
        if base in HEAVY_PKGS:
            return True
    return False


def python_in_venv(repo_root: Path) -> Path:
    if platform.system().lower().startswith("win"):
        return repo_root / ".venv" / "Scripts" / "python.exe"
    else:
        return repo_root / ".venv" / "bin" / "python"


# -------- portable CPython download (project-local, no system install) --------

def platform_tag() -> str:
    """Return python-build-standalone platform tag."""
    sysname = platform.system().lower()
    machine = platform.machine().lower()
    # Normalize arch names
    if machine in ("x86_64", "amd64"):
        arch = "x86_64"
    elif machine in ("arm64", "aarch64"):
        arch = "aarch64"
    else:
        arch = machine  # best effort

    if sysname.startswith("win"):
        # msvc shared runtime, 'install_only' layout
        return f"{arch}-pc-windows-msvc-shared-install_only"
    elif sysname == "darwin":
        return f"{arch}-apple-darwin-install_only"
    else:
        # assume glibc linux; (musl users would need '-unknown-linux-musl-...')
        return f"{arch}-unknown-linux-gnu-install_only"


def pbs_url(version: str = "3.11.9", tag: str = "20240715") -> str:
    # Example:
    # https://github.com/indygreg/python-build-standalone/releases/download/20240715/
    #   cpython-3.11.9+20240715-x86_64-unknown-linux-gnu-install_only.tar.gz
    return (
        "https://github.com/indygreg/python-build-standalone/releases/download/"
        f"{tag}/cpython-{version}+{tag}-{platform_tag()}.tar.gz"
    )


def download_file(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    print(f"↓ Downloading {url}")
    with urllib.request.urlopen(url) as r, open(dest, "wb") as f:
        shutil.copyfileobj(r, f)


def extract_tar_gz(archive: Path, dest_dir: Path) -> None:
    print(f"⇪ Extracting {archive.name} → {dest_dir}")
    dest_dir.mkdir(parents=True, exist_ok=True)
    with tarfile.open(archive, "r:gz") as tf:
        tf.extractall(dest_dir)


def ensure_portable_python(repo_root: Path, version: str = "3.11.9", tag: str = "20240715") -> Path:
    """
    Ensure a portable CPython lives under .pythonrt/<major.minor>/ and return its python executable path.
    """
    major_minor = ".".join(version.split(".")[:2])  # e.g. "3.11"
    runtime_root = repo_root / ".pythonrt" / major_minor

    # Expected executable path after extraction
    if platform.system().lower().startswith("win"):
        candidate = runtime_root / "python" / "python.exe"
    else:
        candidate = runtime_root / "python" / "bin" / "python3"

    if candidate.exists():
        return candidate

    # Not present → download & extract
    url = pbs_url(version=version, tag=tag)
    tmp = repo_root / ".pythonrt" / f"cpython-{version}.tar.gz"
    download_file(url, tmp)
    extract_tar_gz(tmp, runtime_root)
    try:
        tmp.unlink()
    except Exception:
        pass

    if not candidate.exists():
        raise RuntimeError("Portable Python extraction did not produce an executable at expected path.")
    return candidate


def create_venv_with_interpreter(venv_dir: Path, interpreter_path: str) -> None:
    """
    Create venv using the given interpreter. Use --copies to keep it self-contained.
    """
    run([interpreter_path, "-m", "venv", "--copies", str(venv_dir)])


# ---------------------- venv + install ----------------------

def create_venv_and_install(repo_root: Path, base_python_spec: Optional[str] = None) -> None:
    """
    Create .venv with a compatible Python.
    - If --python is provided, honor it (version like '3.11' or full path or 'python3.11').
    - Else detect if heavy packages exist; prefer 3.11 for best wheel coverage on Windows.
    - If desired version not installed, download portable CPython into .pythonrt/<ver>/ and use it.
    """
    req = repo_root / "requirements.txt"
    heavy = parse_requirements_for_heavy(req)

    # Decide target Python major.minor
    if base_python_spec and base_python_spec.startswith("3."):
        target_ver = base_python_spec
    elif heavy:
        target_ver = "3.11"
    else:
        target_ver = f"{sys.version_info.major}.{sys.version_info.minor}"

    # Resolve an installed interpreter for target_ver
    chosen_path: Optional[str] = None
    if base_python_spec:
        # explicit path or name
        if Path(base_python_spec).exists():
            chosen_path = str(Path(base_python_spec))
        else:
            found = shutil.which(base_python_spec)
            chosen_path = found if found else None
        if chosen_path:
            print(f"🔧 --python specified → using {chosen_path}")

    if not chosen_path:
        if platform.system().lower().startswith("win"):
            # Windows launcher: prefer version selector if available (e.g., py -3.11)
            try:
                run(["py", f"-{target_ver}", "-V"], check=True)
                chosen_path = f"py -{target_ver}"
            except Exception:
                chosen_path = None
        else:
            p = shutil.which(f"python{target_ver}")
            chosen_path = p

    venv_python = python_in_venv(repo_root)
    venv_dir = venv_python.parent.parent

    if not venv_dir.exists():
        if chosen_path:
            print(f"Creating venv with installed Python {target_ver} ({chosen_path})")
            if platform.system().lower().startswith("win") and chosen_path.startswith("py -"):
                # Use Windows launcher
                run(chosen_path.split() + ["-m", "venv", "--copies", str(venv_dir)])
            else:
                create_venv_with_interpreter(venv_dir, chosen_path)
        else:
            # No suitable interpreter on the machine → fetch a portable one into the project
            print(f"⚠️ Python {target_ver} not found. Fetching a portable runtime into the project…")
            # Pin to a concrete micro version that has portable builds:
            portable_py = ensure_portable_python(repo_root, version=f"{target_ver}.9", tag="20240715")
            print(f"Creating venv with portable runtime at {portable_py}")
            create_venv_with_interpreter(venv_dir, str(portable_py))

        print(f"✅ Created virtual environment at {venv_dir.relative_to(repo_root)}")
    else:
        print(f"ℹ️ Virtual environment already exists at {venv_dir.relative_to(repo_root)}")

    if req.exists():
        print("Installing requirements...")
        run([str(venv_python), "-m", "pip", "install", "--upgrade", "pip", "wheel", "setuptools"])
        # If you want to fail fast when wheels are missing, uncomment:
        # run([str(venv_python), "-m", "pip", "install", "--only-binary=:all:", "-r", str(req)])
        run([str(venv_python), "-m", "pip", "install", "-r", str(req)])
        print("✅ Installed requirements")
    else:
        print("ℹ️ No requirements.txt found; skipping dependency install.")


# ---------------------- VS Code config ----------------------

def write_extensions_json(vscode_dir: Path) -> None:
    """
    Create .vscode/extensions.json to discourage Copilot and recommend Python extension.
    """
    path = vscode_dir / "extensions.json"
    payload = {
        "recommendations": ["ms-python.python"],
        "unwantedRecommendations": ["GitHub.copilot", "GitHub.copilot-chat"],
    }
    try:
        if path.exists():
            existing = json.loads(path.read_text(encoding="utf-8"))
        else:
            existing = {}
    except Exception:
        existing = {}

    unwanted = set(existing.get("unwantedRecommendations", [])) | set(payload["unwantedRecommendations"])
    recommendations = list(set(existing.get("recommendations", [])) | set(payload["recommendations"]))
    merged = {"recommendations": sorted(recommendations), "unwantedRecommendations": sorted(unwanted)}

    path.write_text(json.dumps(merged, indent=2), encoding="utf-8")
    print(f"✅ Wrote {path.relative_to(vscode_dir.parent)}")


def write_vscode(repo_root: Path) -> None:
    vscode = repo_root / ".vscode"
    vscode.mkdir(exist_ok=True)
    settings_path = vscode / "settings.json"

    venv_python = python_in_venv(repo_root)

    # Terminal env so any new terminal picks up the venv by default
    term_env_windows = {
        "VIRTUAL_ENV": "${workspaceFolder}\\.venv",
        "PATH": "${workspaceFolder}\\.venv\\Scripts;${env:PATH}",
    }
    term_env_unix = {
        "VIRTUAL_ENV": "${workspaceFolder}/.venv",
        "PATH": "${workspaceFolder}/.venv/bin:${env:PATH}",
    }

    # Full Copilot shutdown + Python defaults
    settings = {
        # Copilot completions off
        "github.copilot.enable": {"*": False, "plaintext": False, "markdown": False, "scminput": False},
        "github.copilot.nextEditSuggestions.enabled": False,
        "editor.inlineSuggest.edits.allowCodeShifting": "never",
        "github.copilot.inlineSuggest.enable": False,

        # Copilot Chat & indexing off
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

        # Optional: reduce AI/semantic noise
        "workbench.settings.showAISearchToggle": False,
        "search.searchView.semanticSearchBehavior": "manual",

        # Python / venv config
        "python.defaultInterpreterPath": str(venv_python).replace(str(repo_root), "${workspaceFolder}"),
        "python.terminal.activateEnvironment": True,
        "terminal.integrated.env.windows": term_env_windows,
        "terminal.integrated.env.osx": term_env_unix,
        "terminal.integrated.env.linux": term_env_unix,
    }

    # Merge with existing settings if present (ours overwrite same keys)
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

    # Also write extensions.json to discourage Copilot
    write_extensions_json(vscode)


# ---------------------- developer quality-of-life ----------------------

def ensure_gitignore(repo_root: Path) -> None:
    gi = repo_root / ".gitignore"
    lines = {
        ".venv/",
        ".pythonrt/",
        "secrets.toml",
        "__pycache__/",
        ".vscode/*.log",
    }
    if gi.exists():
        existing = set(line.strip() for line in gi.read_text(encoding="utf-8").splitlines())
    else:
        existing = set()
    new = existing | lines
    gi.write_text("\n".join(sorted(filter(None, new))) + "\n", encoding="utf-8")
    print(f"✅ Ensured {gi.relative_to(repo_root)} has venv, portable runtime & secrets")


def write_secure_launchers(repo_root: Path) -> None:
    """
    Create helper scripts that open this workspace with Copilot extensions disabled.
    - tools/code_secure.sh   (macOS/Linux)
    - tools/code_secure.ps1  (Windows PowerShell)
    """
    tools_dir = repo_root / "tools"
    tools_dir.mkdir(exist_ok=True)

    # macOS / Linux launcher
    sh_path = tools_dir / "code_secure.sh"
    sh_contents = f"""#!/usr/bin/env bash
# Open VS Code with Copilot extensions disabled for THIS workspace
exec code --disable-extension GitHub.copilot --disable-extension GitHub.copilot-chat "{repo_root}"
"""
    sh_path.write_text(sh_contents, encoding="utf-8")
    try:
        sh_path.chmod(sh_path.stat().st_mode | 0o111)  # make executable
    except Exception:
        pass

    # Windows PowerShell launcher
    ps1_path = tools_dir / "code_secure.ps1"
    ps1_contents = f"""# Open VS Code with Copilot extensions disabled for THIS workspace
$workspace = "{repo_root}"
code --disable-extension GitHub.copilot --disable-extension GitHub.copilot-chat $workspace
"""
    ps1_path.write_text(ps1_contents, encoding="utf-8")

    print(f"✅ Wrote secure launchers: {sh_path.relative_to(repo_root)} and {ps1_path.relative_to(repo_root)}")


# ---------------------- main ----------------------

def main():
    parser = argparse.ArgumentParser(description="VS Code Python workspace setup")
    parser.add_argument("--repo", help="SSH repo URL (e.g., git@github.com:org/repo.git)")
    parser.add_argument("--dest", help="Destination folder for clone (defaults to repo name)")
    parser.add_argument("--python", help="Base Python to create venv (path or version, e.g. 3.11)", default=None)
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
    ensure_gitignore(repo_root)

    create_venv_and_install(repo_root, base_python_spec=args.python)
    write_vscode(repo_root)
    write_secure_launchers(repo_root)

    print("\n🎉 Workspace setup complete.")
    print("Open the folder in VS Code; it should auto-select .venv and have Copilot disabled for this workspace.")
    print("To force-disable Copilot extensions at launch, use: tools/code_secure.sh or tools/code_secure.ps1")


if __name__ == "__main__":
    main()
