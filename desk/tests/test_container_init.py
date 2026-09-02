"""Tests for the s6 init scripts that template /etc/desk/worker.conf.

These are shell scripts, so the checks here are static: they read the scripts
and the config templates out of desk/docker/ and assert the one invariant that
actually broke -- see WorkerConfTemplatingTest.
"""
import os
import re
import unittest

DOCKER = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'docker'
)
WORKER_INIT = os.path.join(
    DOCKER, 'worker/etc/s6-overlay/s6-rc.d/worker-init/init.sh'
)
WORKER_CONFS = (
    os.path.join(DOCKER, 'worker/etc/desk/worker.conf'),
    os.path.join(DOCKER, 'dns/etc/desk/worker.conf'),
)
PLACEHOLDER = re.compile(r'-[A-Z_]+-')


def read(path):
    with open(path) as f:
        return f.read()


class WorkerConfTemplatingTest(unittest.TestCase):
    """Every worker.conf placeholder is filled in before `install-worker` runs.

    The dns image's worker.conf carries `[worker] dns = powerdns:-HOSTNAME-`,
    and `install-worker` copies that value into the worker doc's `provides`.
    The `-HOSTNAME-` substitution used to live in pdns-init, which s6 starts
    *after* worker-init -- so the dns nodes registered `provides.domain[0].name`
    as the literal "-HOSTNAME-" and matched no task's provider, leaving every
    dns task stuck in state "new".
    """

    def placeholders_in_the_configs(self):
        found = set()
        for path in WORKER_CONFS:
            found.update(PLACEHOLDER.findall(read(path)))
        return found

    def test_the_configs_still_use_placeholders(self):
        # guards the two tests below against silently passing on an empty set
        self.assertIn('-HOSTNAME-', self.placeholders_in_the_configs())

    def test_worker_init_substitutes_every_placeholder(self):
        script = read(WORKER_INIT)

        missing = sorted(
            p for p in self.placeholders_in_the_configs()
            if f's#{p}#' not in script
        )

        self.assertEqual(missing, [])

    def test_the_substitutions_happen_before_install_worker(self):
        lines = read(WORKER_INIT).splitlines()
        install = next(
            i for i, line in enumerate(lines)
            if 'dworker install-worker' in line
        )

        for placeholder in sorted(self.placeholders_in_the_configs()):
            sed = next(
                i for i, line in enumerate(lines) if f's#{placeholder}#' in line
            )
            self.assertLess(
                sed, install,
                f'{placeholder} is substituted after install-worker runs'
            )


if __name__ == '__main__':
    unittest.main()
