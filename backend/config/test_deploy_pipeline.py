"""Pruebas estáticas del pipeline de deploy (TASK-github-actions-deploy-produccion)."""
import os
import shutil
import subprocess
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
