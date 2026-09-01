"""Import every module in the package.

Cheap guard against the failure mode that broke this suite before: a module
importing a dependency that no longer exists (e.g. PyPDF2's `PdfFileMerger`).
"""
import importlib
import pkgutil
import unittest

import desk


def _module_names():
    # without onerror walk_packages silently skips a subtree whose
    # __init__ fails to import -- the exact failure this test looks for
    failed = []
    names = [desk.__name__]
    for module in pkgutil.walk_packages(
        desk.__path__, prefix="desk.", onerror=failed.append
    ):
        names.append(module.name)
    return sorted(names), failed


class ImportTestCase(unittest.TestCase):
    def test_all_modules_import(self):
        names, failed = _module_names()
        self.assertEqual(failed, [])
        self.assertGreater(len(names), 20, "vacuous package walk")
        for name in names:
            with self.subTest(module=name):
                importlib.import_module(name)


if __name__ == "__main__":
    unittest.main()
