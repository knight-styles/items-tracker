"""Tests for PWA configuration, manifest shortcuts, offline banner, and service worker."""
import json
import os
from django.conf import settings
from django.urls import reverse
from tracker.tests.base import BaseTestCase


def get_response_content(resp):
    if hasattr(resp, 'streaming_content'):
        return b"".join(resp.streaming_content).decode('utf-8')
    return resp.content.decode('utf-8')


class PWATestCase(BaseTestCase):
    """Test PWA Manifest, Service Worker, and Offline support."""

    def test_manifest_json_accessible(self):
        manifest_path = settings.BASE_DIR / 'static' / 'manifest.json'
        self.assertTrue(os.path.exists(manifest_path))
        with open(manifest_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        self.assertEqual(data['name'], 'Safety Item Tracker')
        self.assertEqual(data['display'], 'standalone')
        self.assertIn('shortcuts', data)
        self.assertEqual(len(data['shortcuts']), 3)

    def test_service_worker_accessible_at_root(self):
        resp = self.client.get('/sw.js')
        self.assertEqual(resp.status_code, 200)
        content = get_response_content(resp)
        self.assertIn('safety-tracker-v2', content)

    def test_offline_page_accessible(self):
        offline_path = settings.BASE_DIR / 'static' / 'offline.html'
        self.assertTrue(os.path.exists(offline_path))
        with open(offline_path, 'r', encoding='utf-8') as f:
            content = f.read()
        self.assertIn('You are offline', content)

    def test_base_html_includes_pwa_tags_and_elements(self):
        self.login_supervisor()
        resp = self.client.get(reverse('supervisor_log'))
        self.assertEqual(resp.status_code, 200)
        html = resp.content.decode('utf-8')
        self.assertIn('rel="manifest"', html)
        self.assertIn('name="theme-color"', html)
        self.assertIn('navigator.serviceWorker.register', html)
        self.assertIn('id="offlineBanner"', html)
        self.assertIn('id="pwaInstallBtn"', html)

    def test_pwa_icons_exist(self):
        icon192 = settings.BASE_DIR / 'static' / 'images' / 'pwa' / 'icon-192.png'
        icon512 = settings.BASE_DIR / 'static' / 'images' / 'pwa' / 'icon-512.png'
        self.assertTrue(os.path.exists(icon192))
        self.assertTrue(os.path.exists(icon512))
