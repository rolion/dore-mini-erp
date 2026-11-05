"""Pruebas estáticas del pipeline de deploy (TASK-github-actions-deploy-produccion)."""
import os
import shutil
import stat
import subprocess
import tempfile
from pathlib import Path
from unittest import TestCase, skipUnless

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / '.github' / 'workflows' / 'deploy.yml'
SCRIPT = ROOT / 'scripts' / 'deploy' / 'remote-deploy.sh'
BASH = shutil.which('bash')

BASE_ENV = {
    'IMAGE_TAG': 'abc123',
    'DEPLOY_PATH': '/srv/pocketbiz',
    'DATABASE_NETWORK': 'dbnet',
    'SECRET_KEY': 'k',
    'DB_USER': 'app user',
    'DB_PASSWORD': 'p@ss:w/rd#1',
    'DB_NAME': 'doredb',
    'DEPLOY_CHECK_ONLY': '1',
}


def run_script(env):
    return subprocess.run(
        [BASH, str(SCRIPT)],
        env={**{'PATH': os.environ.get('PATH', '')}, **env},
        capture_output=True, text=True,
    )


class WorkflowStructureTests(TestCase):
    def setUp(self):
        self.text = WORKFLOW.read_text(encoding='utf-8')

    def test_triggers_and_safety(self):  # AC-01
        self.assertIn('branches: [main]', self.text)
        self.assertIn('workflow_dispatch', self.text)
        self.assertIn('cancel-in-progress: false', self.text)
        self.assertIn('contents: read', self.text)
        self.assertIn('environment: production', self.text)

    def test_builds_tagged_images_and_verifies_host_key(self):  # AC-02
        self.assertIn('pocketbiz-backend:${IMAGE_TAG}', self.text)
        self.assertIn('pocketbiz-frontend:${IMAGE_TAG}', self.text)
        self.assertIn('StrictHostKeyChecking yes', self.text)
        self.assertNotIn('ssh-keyscan', self.text)

    def test_only_main_and_stdin_read_before_eval(self):  # REV-01, REV-03
        self.assertIn("github.ref == 'refs/heads/main'", self.text)
        self.assertIn('payload=$(cat); eval "$payload"', self.text)

    def test_smoke_check_present(self):  # AC-05
        self.assertIn('/api/health/', self.text)
        self.assertIn('curl --fail', self.text)


class RemoteDeployScriptTests(TestCase):
    def test_step_order(self):  # AC-04, INV-01, INV-02
        text = SCRIPT.read_text(encoding='utf-8')
        positions = [text.index(s) for s in (
            'pg_dump', 'manage.py migrate --noinput', 'up -d --no-build --wait')]
        self.assertEqual(positions, sorted(positions))
        self.assertNotIn('down -v', text)

    @skipUnless(BASH, 'bash no disponible')
    def test_syntax(self):
        self.assertEqual(subprocess.run([BASH, '-n', str(SCRIPT)]).returncode, 0)

    @skipUnless(BASH, 'bash no disponible')
    def test_database_url_is_composed_and_encoded(self):  # AC-03
        result = run_script(BASE_ENV)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            result.stdout.strip(),
            'DATABASE_URL=postgresql://app%20user:p%40ss%3Aw%2Frd%231@db_v2:5432/doredb',
        )

    @skipUnless(BASH, 'bash no disponible')
    def test_missing_variables_fail_early(self):  # AC-03
        env = {k: v for k, v in BASE_ENV.items() if k != 'DB_PASSWORD'}
        result = run_script(env)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('DB_PASSWORD', result.stderr)


def posix(path):
    p = Path(path).as_posix()
    return '/' + p[0].lower() + p[2:] if len(p) > 1 and p[1] == ':' else p


FAKE_DOCKER = r"""#!/usr/bin/env bash
echo "$*" >> "$FAKE_LOG"
case "$1 $2" in
  "exec -e") [ "${FAIL_ON:-}" = pg_dump ] && exit 1; echo dump; exit 0 ;;
  "compose run") cat > /dev/null; [ "${FAIL_ON:-}" = migrate ] && exit 1; exit 0 ;;
  "image ls") printf 'abc123\nlatest\n'; exit 0 ;;
esac
cat > /dev/null
exit 0
"""


@skipUnless(BASH, 'bash no disponible')
class RemoteDeployExecutionTests(TestCase):
    """Ejecuta el script como en producción (stdin -> eval) con un docker falso."""

    def run_deploy(self, fail_on=''):
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp, True)
        bin_dir = Path(tmp, 'bin')
        bin_dir.mkdir()
        fake = bin_dir / 'docker'
        fake.write_text(FAKE_DOCKER, encoding='utf-8', newline='\n')
        fake.chmod(fake.stat().st_mode | stat.S_IEXEC)
        log = Path(tmp, 'calls.log')
        deploy = Path(tmp, 'deploy')
        deploy.mkdir()
        env = {k: v for k, v in BASE_ENV.items() if k != 'DEPLOY_CHECK_ONLY'}
        env.update(DEPLOY_PATH=posix(deploy), FAIL_ON=fail_on, FAKE_LOG=posix(log))
        exports = ''.join(f"export {k}='{v}'\n" for k, v in env.items())
        payload = exports + SCRIPT.read_text(encoding='utf-8')
        result = subprocess.run(
            [BASH, '-c', 'payload=$(cat); eval "$payload"'],
            input=payload, text=True, capture_output=True,
            env={'PATH': posix(bin_dir) + os.pathsep + os.environ.get('PATH', '')},
        )
        calls = log.read_text(encoding='utf-8') if log.exists() else ''
        return result, calls

    def test_happy_path_runs_all_steps_even_with_nothing_to_prune(self):  # REV-01, REV-02
        result, calls = self.run_deploy()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertLess(calls.index('pg_dump'), calls.index('manage.py migrate'))
        self.assertLess(calls.index('manage.py migrate'), calls.index('up -d --no-build --wait'))
        self.assertIn('completado', result.stdout)

    def test_backup_failure_prevents_migration(self):  # INV-01
        result, calls = self.run_deploy('pg_dump')
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn('migrate', calls)

    def test_migration_failure_prevents_up(self):  # INV-02
        result, calls = self.run_deploy('migrate')
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn('up -d', calls)
