"""
The production settings failed Django's own deployment checklist
(no HSTS, no HTTPS redirect, cookies not marked secure).
"""
import os
import secrets
import subprocess
import sys
from pathlib import Path

from django.test import TestCase

BACKEND = Path(__file__).resolve().parent.parent


class TestDeploymentChecklist(TestCase):
    def test_production_settings_pass_check_deploy(self):
        env = {**os.environ, 'DEBUG': 'False', 'ALLOWED_HOSTS': 'api.example.com',
               'SECURE_SSL_REDIRECT': 'True',
               'SECRET_KEY': secrets.token_urlsafe(50),
               'CORS_ALLOWED_ORIGINS': 'https://app.example.com'}
        result = subprocess.run(
            [sys.executable, 'manage.py', 'check', '--deploy', '--fail-level', 'WARNING'],
            cwd=BACKEND, env=env, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
