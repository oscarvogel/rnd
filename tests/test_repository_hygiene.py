import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def tracked_files():
    result = subprocess.run(
        ["git", "ls-files"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


class RepositoryHygieneTests(unittest.TestCase):
    def test_generated_validation_artifacts_are_ignored(self):
        gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8")

        self.assertIn("artifacts/", gitignore.splitlines())

    def test_generated_and_local_files_are_not_tracked(self):
        forbidden_prefixes = (
            ".venv-build/",
            "build/",
            "dist/",
            "documentacion/",
            "__pycache__/",
        )
        forbidden_files = {"all.log", "errors.log", ".env"}

        tracked = tracked_files()

        for path in tracked:
            with self.subTest(path=path):
                self.assertFalse(path.endswith(".pyc"))
                self.assertNotIn(path, forbidden_files)
                self.assertFalse(path.endswith((".log", ".xls", ".xlsx", ".pdf", ".csv")))
                self.assertFalse(path.startswith(forbidden_prefixes))

    def test_known_secret_values_are_not_tracked(self):
        secret_fragments = (
            "fa" + "sca",
            "Na" + "ja2011",
            "QK" + "wJNczkz9dHoaRo5qHa",
            "@M" + "Ug!*d98n",
            "oc*" + "nmlo5Koxwlnx",
        )

        offenders = []
        for path in tracked_files():
            file_path = ROOT / path
            if not file_path.is_file():
                continue
            try:
                content = file_path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
            for secret in secret_fragments:
                if secret in content:
                    offenders.append(path)

        self.assertEqual(offenders, [])


if __name__ == "__main__":
    unittest.main()
