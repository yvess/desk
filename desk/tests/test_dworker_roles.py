"""What a dns node loads, and what it must not.

`desk-dns` installs three of the nine pinned packages (httpx, dnspython,
json-diff); the other six -- the invoice stack -- are foreman-only. Nothing in
the package enforces that, so these tests do: they run the real entry point in
a subprocess with `WORKER_TYPE=worker` and look at what ended up in
`sys.modules`. A new foreman-only import on the shared path fails here instead
of in a dns container.
"""
import json
import os
import subprocess
import sys
import unittest

DESK_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DWORKER = os.path.join(DESK_DIR, 'dworker')

# the six requirements that only docker/worker/requirements3.txt installs,
# under their import names, plus the two plugins that pull them in
FOREMAN_ONLY = (
    'desk.plugin.invoice', 'desk.plugin.extcrm',
    'cairosvg', 'jinja2', 'pymysql', 'pypdf', 'qrbill', 'weasyprint',
)


def run_dworker_code(source, worker_type, *argv):
    """Run `source` under WORKER_TYPE in a subprocess.

    Returns (completed process, names in its sys.modules at exit)."""
    wrapper = (
        "import atexit, json, sys\n"
        "atexit.register(lambda: sys.stderr.write("
        "'MODULES ' + json.dumps(sorted(sys.modules))))\n"
    ) + source
    env = dict(os.environ, WORKER_TYPE=worker_type, PYTHONDONTWRITEBYTECODE='1')
    process = subprocess.run(
        [sys.executable, '-c', wrapper, *argv],
        cwd=DESK_DIR, env=env, capture_output=True, text=True
    )
    marker = process.stderr.rindex('MODULES ')
    modules = json.loads(process.stderr[marker + len('MODULES '):])
    process.stderr = process.stderr[:marker]
    return process, modules


DWORKER_MAIN = (
    "import runpy, sys\n"
    "sys.argv[0] = 'dworker'\n"
    "runpy.run_path({!r}, run_name='__main__')\n"
).format(DWORKER)


class DnsNodeImportsTestCase(unittest.TestCase):
    def test_a_worker_loads_none_of_the_foreman_stack(self):
        process, modules = run_dworker_code(DWORKER_MAIN, 'worker', '--help')

        self.assertEqual(process.returncode, 0, process.stderr)
        self.assertIn('dns-check', process.stdout, "vacuous run")
        loaded = [name for name in modules if name.startswith(FOREMAN_ONLY)]
        self.assertEqual(loaded, [])

    def test_the_dummy_crm_does_not_load_pymysql(self):
        """`todoyu` is the only pymysql importer; the Dummy must not reach it."""
        process, modules = run_dworker_code(
            "from desk.utils import get_crm_module\n"
            "assert type(get_crm_module(object())).__name__ == 'Dummy'\n",
            'worker',
        )

        self.assertEqual(process.returncode, 0, process.stderr)
        self.assertNotIn('pymysql', modules)
        self.assertNotIn('desk.plugin.extcrm.todoyu', modules)


class RoleCommandsTestCase(unittest.TestCase):
    """`service-query` reports on services and reaches the CRM -- foreman work."""

    def test_a_worker_does_not_offer_service_query(self):
        process, _ = run_dworker_code(DWORKER_MAIN, 'worker', 'service-query', '--help')

        self.assertNotEqual(process.returncode, 0)
        self.assertIn('invalid choice', process.stderr)

    def test_a_foreman_offers_service_query(self):
        process, _ = run_dworker_code(DWORKER_MAIN, 'foreman', 'service-query', '--help')

        self.assertEqual(process.returncode, 0, process.stderr)
        self.assertIn('Query service data', process.stdout)


if __name__ == "__main__":
    unittest.main()
