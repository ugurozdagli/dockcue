"""Build a portable Windows release from this repository only."""
from pathlib import Path
import hashlib
import importlib.metadata
import json
import shutil
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from dockcue import __version__
from dockcue.runtime import app_icon


def main():
    icon = ROOT / "assets" / "dockcue.ico"
    icon.parent.mkdir(parents=True, exist_ok=True)
    app_icon().save(icon, sizes=[(16,16), (24,24), (32,32), (48,48), (64,64), (128,128)])
    subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"], cwd=ROOT, check=True)
    subprocess.run([sys.executable, "-m", "PyInstaller", "--noconfirm", "--onefile", "--windowed",
                    "--name", "DockCue", "--paths", str(ROOT), "--collect-all", "customtkinter",
                    "--hidden-import", "pystray._win32", "--exclude-module", "numpy",
                    "--icon", str(icon), "--add-data", f"{icon};assets", "launcher.py"], cwd=ROOT, check=True)
    staging = ROOT / "release" / f"DockCue-{__version__}-windows-x64"
    staging.mkdir(parents=True, exist_ok=True)
    for source in [ROOT / "dist" / "DockCue.exe", ROOT / "README.md", ROOT / "LICENSE",
                   ROOT / "PRIVACY.md", ROOT / "THIRD_PARTY_NOTICES.md"]:
        shutil.copy2(source, staging / source.name)
    notices = staging / "licenses"
    notices.mkdir(exist_ok=True)
    python_license = Path(sys.base_prefix) / "LICENSE.txt"
    if python_license.is_file():
        shutil.copy2(python_license, notices / "Python-LICENSE.txt")
    for source in (Path(sys.base_prefix) / "tcl").rglob("license.terms"):
        shutil.copy2(source, notices / (source.parent.name + "-license.terms"))
    for name in ["hidapi", "websocket-client", "customtkinter", "pystray", "Pillow", "darkdetect", "six", "packaging"]:
        distribution = importlib.metadata.distribution(name)
        for filename in distribution.files or []:
            if any(part.lower() in ("licenses", "license", "copying") for part in filename.parts) or filename.name.lower().startswith(("license", "copying")):
                source = distribution.locate_file(filename)
                if source.is_file():
                    destination = notices / name / filename.name
                    destination.parent.mkdir(exist_ok=True)
                    shutil.copy2(source, destination)
    archive = ROOT / "release" / (staging.name + ".zip")
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as out:
        for source in sorted(staging.rglob("*")):
            if source.is_file():
                out.write(source, Path(staging.name) / source.relative_to(staging))
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    (ROOT / "release" / "SHA256SUMS.txt").write_text(f"{digest}  {archive.name}\n", encoding="ascii")
    print(json.dumps({"version": __version__, "archive": archive.name, "sha256": digest}))


if __name__ == "__main__":
    main()
