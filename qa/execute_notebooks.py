"""Execute learning notebooks using the project kernel and retain real cell output."""
import argparse
import ast
import json
from pathlib import Path

import nbformat
from jupyter_client.kernelspec import KernelSpecManager
from nbclient import NotebookClient

ROOT = Path(__file__).resolve().parents[1]
KERNEL = "mini-gpt-webcodegen"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--save-in-place", action="store_true",
                        help="Save executed outputs in the tracked notebook files")
    args = parser.parse_args()
    spec = KernelSpecManager().get_kernel_spec(KERNEL)
    expected = ROOT / ".venv/Scripts/python.exe"
    if Path(spec.argv[0]).resolve() != expected.resolve():
        raise ValueError("Notebook kernel does not point to this project's VENV")
    for path in sorted((ROOT / "notebooks").glob("[0-9][0-9]_*.ipynb")):
        notebook = nbformat.read(path, as_version=4)
        nbformat.validate(notebook)
        for cell in notebook.cells:
            if cell.cell_type == "code":
                ast.parse(cell.source)
        NotebookClient(notebook, kernel_name=KERNEL, timeout=180,
                       resources={"metadata": {"path": str(path.parent)}},
                       allow_errors=False).execute()
        nbformat.validate(notebook)
        target = path if args.save_in_place else ROOT / "outputs/notebooks" / path.name
        target.parent.mkdir(parents=True, exist_ok=True)
        nbformat.write(notebook, target)
        print(json.dumps({"notebook": path.name, "kernel": KERNEL,
                          "code_cells": sum(c.cell_type == "code" for c in notebook.cells),
                          "error_outputs": 0, "saved_to": str(target.relative_to(ROOT))}))


if __name__ == "__main__":
    main()
