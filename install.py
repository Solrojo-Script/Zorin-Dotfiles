#!/usr/bin/env python3
"""Install the Zorin Violet dotfiles and their application dependencies."""
import argparse
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

PACKAGES = ['kitty', 'wofi', 'nautilus', 'fonts-jetbrains-mono', 'wl-clipboard', 'dconf-cli']
FILES = [
    'kitty/kitty.conf', 'kitty/current-theme.conf', 'wofi/config', 'wofi/style.css',
    'gtk-3.0/gtk.css', 'gtk-3.0/settings.ini', 'gtk-4.0/gtk.css', 'gtk-4.0/settings.ini',
]
EXTENSIONS = {
    'blur-my-shell': 'blur-my-shell@aunetx',
    'dash-to-dock': 'dash-to-dock@micxgx.gmail.com',
    'system-monitor': 'system-monitor@gnome-shell-extensions.gcampax.github.com',
    'user-theme': 'user-theme@gnome-shell-extensions.gcampax.github.com',
    'window-padding': 'window-padding@pvlamkhtn.github.io',
    'zorin-appindicator': 'zorin-appindicator@zorinos.com',
    'zorin-desktop-icons': 'zorin-desktop-icons@zorinos.com',
    'zorin-tiling-shell': 'zorin-tiling-shell@zorinos.com',
}


def restore_extension_settings(source, backup):
    if not shutil.which('gnome-extensions') or not shutil.which('dconf'):
        print('Extension settings skipped. GNOME tools are unavailable.')
        return
    result = subprocess.run(['gnome-extensions', 'list'], capture_output=True, text=True)
    if result.returncode:
        print('Extension settings skipped. No GNOME session is available.')
        return
    installed = set(result.stdout.splitlines())
    for settings in sorted((source / '.config/gnome-extension-settings').glob('*.dconf')):
        name = settings.stem
        if EXTENSIONS.get(name) not in installed:
            print(f'Skipped {name}. The extension is not installed.')
            continue
        data_home = Path(os.environ.get('XDG_DATA_HOME', Path.home() / '.local/share'))
        if name == 'user-theme' and not any(path.is_dir() for path in (
            data_home / 'themes/ZorinViolet', Path.home() / '.themes/ZorinViolet',
            Path('/usr/share/themes/ZorinViolet'),
        )):
            print('User Themes settings skipped. ZorinViolet is not installed.')
            continue
        target = f'/org/gnome/shell/extensions/{name}/'
        previous = subprocess.check_output(['dconf', 'dump', target])
        directory = backup / 'extension-settings'
        directory.mkdir(exist_ok=True)
        (directory / settings.name).write_bytes(previous)
        subprocess.run(['dconf', 'load', target], input=settings.read_bytes(), check=True)
        print(f'Imported settings for {name}.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--skip-packages', action='store_true')
    parser.add_argument('--skip-extension-settings', action='store_true')
    args = parser.parse_args()
    if os.geteuid() == 0:
        parser.exit(1, 'Run as your desktop user. Only package installation uses sudo.\n')
    source = Path(__file__).resolve().parent
    config = Path(os.environ.get('XDG_CONFIG_HOME', Path.home() / '.config'))
    state = Path(os.environ.get('XDG_STATE_HOME', Path.home() / '.local/state'))
    for name in FILES:
        if not (source / '.config' / name).is_file():
            parser.exit(1, f'Missing source file: {name}\n')
    if args.dry_run:
        if not args.skip_packages:
            print('Install packages: ' + ', '.join(PACKAGES))
        for name in FILES:
            print(f'Copy {name} to {config / name}')
        print(f'Backups will be stored under {state / "zorin-violet-dotfiles"}')
        if not args.skip_extension_settings:
            print('Import saved preferences for installed GNOME extensions.')
        return
    if not args.skip_packages:
        if not shutil.which('apt-get'):
            parser.exit(1, 'Package installation requires apt-get (Zorin OS / Ubuntu).\n')
        subprocess.run(['sudo', 'apt-get', 'update'], check=True)
        subprocess.run(['sudo', 'apt-get', 'install', '-y', *PACKAGES], check=True)

    backups = state / 'zorin-violet-dotfiles'
    backups.mkdir(parents=True, exist_ok=True)
    backup = Path(tempfile.mkdtemp(prefix='backup-', dir=backups))
    print(f'Backup directory: {backup}', flush=True)
    new_files = []
    # Back up the entire set before replacing any of the files.
    for name in FILES:
        target = config / name
        if target.exists() or target.is_symlink():
            saved = backup / '.config' / name
            saved.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(target, saved, follow_symlinks=False)
        else:
            new_files.append(name)
    (backup / 'new-files.txt').write_text(''.join(name + '\n' for name in new_files))
    for name in FILES:
        target = config / name
        target.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(dir=target.parent, delete=False) as temporary:
            staged = Path(temporary.name)
        try:
            shutil.copyfile(source / '.config' / name, staged)
            staged.chmod(0o644)
            staged.replace(target)
        finally:
            staged.unlink(missing_ok=True)
    if not args.skip_extension_settings:
        restore_extension_settings(source, backup)
    print('Installed. Restart Kitty and Wofi. Log out and back in to reload desktop styling.')


if __name__ == '__main__':
    main()
