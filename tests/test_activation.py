"""Settings integration tests; only run with the in-memory GSettings backend."""
import importlib.util
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from extension_options import EXTENSIONS, ExtensionPlan, build_plan
spec = importlib.util.spec_from_file_location('activation_installer', ROOT / 'install.py')
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)


@unittest.skipUnless(os.environ.get('GSETTINGS_BACKEND') == 'memory',
                     'Use GSETTINGS_BACKEND=memory to protect desktop settings.')
class ActivationTests(unittest.TestCase):
    def setUp(self):
        from gi.repository import Gio
        self.shell = Gio.Settings.new('org.gnome.shell')
        self.enabled = ['existing@example', 'ubuntu-dock@ubuntu.com', EXTENSIONS['window-padding']]
        self.disabled = ['disabled@example', EXTENSIONS['window-padding']]
        self.shell.set_strv('enabled-extensions', self.enabled)
        self.shell.set_strv('disabled-extensions', self.disabled)
        self.shell.set_boolean('disable-user-extensions', False)
        self.temporary = tempfile.TemporaryDirectory()
        self.backup = Path(self.temporary.name)
        self.installed_patch = patch.object(installer, 'installed_extension_ids', return_value=set(EXTENSIONS.values()))
        self.installed_patch.start()
        self.addCleanup(self.installed_patch.stop)
        self.addCleanup(self.temporary.cleanup)

    def test_empty_plan_preserves_all_activation_settings(self):
        installer.apply_extension_activation(ExtensionPlan(), self.backup)
        self.assertEqual(self.shell.get_strv('enabled-extensions'), self.enabled)
        self.assertEqual(self.shell.get_strv('disabled-extensions'), self.disabled)
        self.assertFalse(list(self.backup.iterdir()))

    def test_only_selected_extension_is_enabled_and_others_are_preserved(self):
        plan = build_plan({'window-padding'}, set(EXTENSIONS.values()), self.enabled)
        with patch.object(installer, 'activate_shell_theme') as theme:
            installer.apply_extension_activation(plan, self.backup)
        self.assertEqual(self.shell.get_strv('enabled-extensions'), self.enabled)
        self.assertEqual(self.shell.get_strv('disabled-extensions'), ['disabled@example'])
        theme.assert_not_called()

    def test_master_switch_is_preserved_even_when_extensions_are_selected(self):
        self.shell.set_boolean('disable-user-extensions', True)
        plan = build_plan({'blur-my-shell'}, set(EXTENSIONS.values()), self.enabled)
        installer.apply_extension_activation(plan, self.backup)
        self.assertTrue(self.shell.get_boolean('disable-user-extensions'))
        self.assertIn('existing@example', self.shell.get_strv('enabled-extensions'))

    def test_theme_is_applied_only_when_user_themes_is_selected(self):
        plan = build_plan({'user-theme'}, set(EXTENSIONS.values()), self.enabled)
        with patch.object(installer, 'activate_shell_theme') as theme:
            installer.apply_extension_activation(plan, self.backup)
        theme.assert_called_once_with(self.backup)

    def test_only_explicitly_approved_conflicting_dock_is_disabled(self):
        plan = build_plan({'dash-to-dock'}, set(EXTENSIONS.values()), self.enabled, replace_dock=True)
        installer.apply_extension_activation(plan, self.backup)
        self.assertNotIn('ubuntu-dock@ubuntu.com', self.shell.get_strv('enabled-extensions'))
        self.assertIn('existing@example', self.shell.get_strv('enabled-extensions'))
        self.assertIn('ubuntu-dock@ubuntu.com', self.shell.get_strv('disabled-extensions'))
        self.assertIn('disabled@example', self.shell.get_strv('disabled-extensions'))

    def test_complete_dotfiles_install_with_skip_extensions_preserves_activation(self):
        with tempfile.TemporaryDirectory() as home:
            home = Path(home)
            environment = {'XDG_CONFIG_HOME': str(home / 'config'),
                           'XDG_DATA_HOME': str(home / 'data'),
                           'XDG_STATE_HOME': str(home / 'state')}
            with patch.dict(os.environ, environment), patch.object(Path, 'home', return_value=home):
                installer.main(['--skip-packages', '--skip-extensions'])
            self.assertTrue((home / 'config/kitty/kitty.conf').is_file())
            self.assertTrue((home / 'data/themes/ZorinViolet/gnome-shell/gnome-shell.css').is_file())
            self.assertTrue((home / '.bashrc').is_file())
        self.assertEqual(self.shell.get_strv('enabled-extensions'), self.enabled)
        self.assertEqual(self.shell.get_strv('disabled-extensions'), self.disabled)
        self.assertFalse(self.shell.get_boolean('disable-user-extensions'))


if __name__ == '__main__':
    unittest.main()
