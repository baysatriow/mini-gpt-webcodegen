import tempfile
import unittest
from pathlib import Path

import nbformat

from qa.build_fullpage_v5_notebook import build_notebook


class SourceBoundNotebookTests(unittest.TestCase):
    def test_notebook_explains_training_stages_and_keeps_final_closed(self):
        with tempfile.TemporaryDirectory() as temporary:
            notebook = build_notebook(Path(temporary) / "source-bound.ipynb")
        nbformat.validate(notebook)
        code = "\n".join(cell.source for cell in notebook.cells if cell.cell_type == "code").lower()
        markdown = "\n".join(cell.source for cell in notebook.cells if cell.cell_type == "markdown").lower()
        self.assertIn("train-025", code)
        self.assertIn("train-026", code)
        self.assertNotIn("--scope final", code)
        self.assertNotIn("test.requests.jsonl", code)
        self.assertIn("76/80", markdown)
        self.assertIn("sintetis", markdown)
        self.assertIn("final", markdown)

    def test_notebook_has_separate_stage_cells(self):
        with tempfile.TemporaryDirectory() as temporary:
            notebook = build_notebook(Path(temporary) / "source-bound.ipynb")
        commands = [cell.source for cell in notebook.cells if cell.cell_type == "code"]
        train_025 = [cell for cell in commands if "TRAIN-025" in cell]
        train_026 = [cell for cell in commands if "TRAIN-026" in cell]
        self.assertGreaterEqual(len(train_025), 2)
        self.assertGreaterEqual(len(train_026), 2)


if __name__ == "__main__":
    unittest.main()
