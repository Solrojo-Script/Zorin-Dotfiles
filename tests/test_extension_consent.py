"""Consent regression tests; no network requests or system modifications."""
import importlib.util
import io
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from extension_options import (EXTENSIONS, DOCKS, ExtensionPlan, build_plan,
                               choose_plan, parse_selection)
spec = importlib.util.spec_from_file_location('dotfiles_installer', ROOT / 'install.py')
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)


class ConsentTests(unittest.TestCase):
    def test_empty_selection_and_eof_change_nothing(self):
        for response in ('', EOFError(), KeyboardInterrupt()):
            def ask(_prompt):
                if isinstance(response, BaseException):
                    raise response
                return response
            self.assertEqual(choose_plan(set(), set(), ask=ask, output=lambda _: None), ExtensionPlan())

    def test_explicit_choice_installs_only_selected_extensions(self):
        plan = choose_plan(set(), set(), requested='1,3', assume_yes=True, output=lambda _: None)
        self.assertEqual(plan.install, ('user-theme', 'window-padding'))
        self.assertEqual(plan.enable, plan.install)

    def test_no_final_confirmation_discards_every_operation(self):
        for answer in ('', 'no', EOFError()):
            def ask(_prompt):
                if isinstance(answer, BaseException):
                    raise answer
                return answer
            self.assertEqual(choose_plan(set(), set(), requested='1', ask=ask,
                                         output=lambda _: None), ExtensionPlan())

    def test_yes_flag_does_not_select_any_extension(self):
        self.assertEqual(choose_plan(set(), set(), assume_yes=True, ask=lambda _: '',
                                     output=lambda _: None), ExtensionPlan())

    def test_skip_mode_never_prompts_even_with_other_yes_flag(self):
        def unexpected(_prompt):
            self.fail('Skip mode must not prompt.')
        self.assertEqual(choose_plan(set(), set(), skip=True, assume_yes=True,
                                     ask=unexpected, output=lambda _: None), ExtensionPlan())

    def test_dock_replacement_requires_separate_consent(self):
        active = {'zorin-taskbar@zorinos.com'}
        declined = choose_plan(set(), active, requested='2', assume_yes=True,
                               ask=lambda _: '', output=lambda _: None)
        self.assertEqual(declined.install, ('dash-to-dock',))
        self.assertFalse(declined.enable)
        self.assertFalse(declined.disable)
        approved = choose_plan(set(), active, requested='2', assume_yes=True,
                               ask=lambda _: 'yes', output=lambda _: None)
        self.assertEqual(approved.disable, ('zorin-taskbar@zorinos.com',))
        self.assertEqual(approved.enable, ('dash-to-dock',))

    def test_dock_flag_does_not_affect_unselected_dock(self):
        plan = build_plan({'user-theme'}, set(), set(DOCKS), replace_dock=True)
        self.assertFalse(plan.disable)

    def test_installed_extension_is_not_downloaded_again(self):
        plan = build_plan({'blur-my-shell'}, {EXTENSIONS['blur-my-shell']}, set())
        self.assertFalse(plan.install)
        self.assertEqual(plan.enable, ('blur-my-shell',))

    def test_settings_only_zorin_extension_is_never_installed_or_enabled(self):
        plan = build_plan({'zorin-tiling-shell'}, {EXTENSIONS['zorin-tiling-shell']}, set())
        self.assertFalse(plan.install)
        self.assertFalse(plan.enable)
        self.assertEqual(plan.configure, ('zorin-tiling-shell',))
        missing = build_plan({'zorin-tiling-shell'}, set(), set())
        self.assertFalse(missing.configure)
        self.assertEqual(missing.skipped, ('zorin-tiling-shell',))

    def test_skip_packages_only_allows_existing_extensions(self):
        plan = build_plan({'user-theme', 'blur-my-shell'}, {EXTENSIONS['user-theme']}, set(),
                          allow_downloads=False)
        self.assertFalse(plan.install)
        self.assertEqual(plan.enable, ('user-theme',))
        self.assertEqual(plan.skipped, ('blur-my-shell',))

    def test_skip_preference_imports_preserves_activation_selection(self):
        plan = build_plan({'user-theme'}, set(), set(), import_settings=False)
        self.assertFalse(plan.configure)
        self.assertEqual(plan.enable, ('user-theme',))

    def test_invalid_selection_is_rejected(self):
        for value in ('0', '9', 'all', 'unknown-extension'):
            with self.assertRaises(ValueError):
                parse_selection(value)
        self.assertEqual(parse_selection('1 1,user-theme'), {'user-theme'})

    def test_dry_run_never_prompts_and_defaults_to_empty(self):
        def unexpected(_prompt):
            self.fail('Dry run must not prompt.')
        self.assertEqual(choose_plan(set(), set(), dry_run=True, ask=unexpected,
                                     output=lambda _: None), ExtensionPlan())

    def test_base_packages_do_not_include_extension_bundle(self):
        self.assertNotIn('gnome-shell-extensions', installer.PACKAGES)
        self.assertFalse(any('extension' in package for package in installer.PACKAGES))

    def test_empty_install_plan_has_no_network_or_process_calls(self):
        with patch.object(installer, 'installed_extension_ids', return_value=set()), \
             patch.object(installer.urllib.request, 'urlopen') as network, \
             patch.object(installer.subprocess, 'run') as process:
            installer.install_selected_extensions(())
        network.assert_not_called()
        process.assert_not_called()

    def test_unselected_extension_settings_are_not_imported(self):
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            settings = root / '.config/gnome-extension-settings'
            settings.mkdir(parents=True)
            (settings / 'blur-my-shell.dconf').write_text('[/]\nbrightness=0.9\n')
            (settings / 'window-padding.dconf').write_text('[/]\npadding=8\n')
            with patch.object(installer, 'installed_extension_ids', return_value=set(EXTENSIONS.values())), \
                 patch.object(installer.subprocess, 'check_output', return_value=b'old'), \
                 patch.object(installer.subprocess, 'run') as process:
                installer.restore_extension_settings(root, root, ('window-padding',))
            self.assertEqual(process.call_count, 1)
            self.assertEqual(process.call_args.args[0], ['dconf', 'load', '/org/gnome/shell/extensions/window-padding/'])


if __name__ == '__main__':
    unittest.main()
