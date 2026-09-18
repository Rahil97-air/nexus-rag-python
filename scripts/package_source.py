"""Build a source-only handoff; never include credentials or user indexes."""
from pathlib import Path
import argparse
from zipfile import ZipFile, ZIP_DEFLATED

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT.parent / "output" / "Nexus_RAG_Python_Source_2026-09-18.zip"
ROOT_FILES = ["README.md", "requirements.in", "requirements.txt", ".gitignore", ".env.example", "app.py", "portfolio_app.py", "Start Nexus.cmd", ".streamlit/config.toml"]
FOLDERS = {"nexus_rag": {".py"}, "scripts": {".py"}, "tests": {".py", ".json"}, "docs": {".md"}}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--replace", action="store_true", help="Explicitly replace the known generated source bundle.")
    args = parser.parse_args()
    files = [ROOT / name for name in ROOT_FILES]
    for folder, suffixes in FOLDERS.items():
        files.extend(p for p in (ROOT / folder).rglob("*") if p.is_file()
                     and p.suffix in suffixes and "__pycache__" not in p.parts)
    files.append(ROOT / "samples/handbook.pdf")
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    # Exclusive creation prevents accidentally replacing a user's existing file.
    with ZipFile(OUTPUT, "w" if args.replace else "x", ZIP_DEFLATED) as archive:
        for path in sorted(set(files)):
            archive.write(path, "nexus-rag/" + path.relative_to(ROOT).as_posix())
    with ZipFile(OUTPUT) as archive:
        assert archive.testzip() is None
        assert not any(part in {".env", "secrets.toml", ".data", ".api-data", ".demo-data", ".cache", ".venv", "__pycache__"}
                       for name in archive.namelist() for part in Path(name).parts)
        print(f"Verified {len(archive.namelist())} source/sample files; no credentials, indexes or caches.")
    print(OUTPUT)


if __name__ == "__main__":
    main()
