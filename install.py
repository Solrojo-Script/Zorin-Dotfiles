#!/usr/bin/env python3
"""Install the Zorin Violet dotfiles and their application dependencies."""
import argparse
import json
import os
import re
import shutil
import subprocess
import tempfile
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path

PACKAGES = [
    'kitty', 'wofi', 'nautilus', 'fonts-jetbrains-mono', 'fonts-croscore', 'wl-clipboard',
    'dconf-cli', 'python3-gi', 'gnome-shell-extensions',
]
FILES = [
    'kitty/kitty.conf', 'kitty/current-theme.conf', 'wofi/config', 'wofi/style.css',
    'gtk-3.0/gtk.css', 'gtk-3.0/settings.ini', 'gtk-4.0/gtk.css', 'gtk-4.0/settings.ini',
    'bash/violet-prompt.sh',
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
REQUIRED_EXTENSIONS = ('dash-to-dock', 'window-padding', 'blur-my-shell')


def install_prompt(backup):
    bashrc = Path.home() / '.bashrc'
    previous = bashrc.read_text() if bashrc.exists() else ''
    if bashrc.exists() or bashrc.is_symlink():
        shutil.copy2(bashrc, backup / '.bashrc', follow_symlinks=False)
    else:
        (backup / 'new-bashrc.txt').write_text(str(bashrc) + '\n')
    marker = '# BEGIN Zorin Violet prompt'
    block = '''# BEGIN Zorin Violet prompt
if [ -r "${XDG_CONFIG_HOME:-$HOME/.config}/bash/violet-prompt.sh" ]; then
    . "${XDG_CONFIG_HOME:-$HOME/.config}/bash/violet-prompt.sh"
fi
# END Zorin Violet prompt'''
    if marker in previous:
        updated, count = re.subn(
            r'# BEGIN Zorin Violet prompt\n.*?# END Zorin Violet prompt',
            lambda _: block, previous, count=1, flags=re.S)
        if count != 1:
            raise SystemExit('The existing Violet prompt block is incomplete. Check your .bashrc.')
    else:
        updated = previous.rstrip() + '\n\n' + block + '\n'
    with tempfile.NamedTemporaryFile(dir=bashrc.parent, delete=False) as temporary:
        staged = Path(temporary.name)
    try:
        staged.write_text(updated)
        staged.chmod(bashrc.stat().st_mode & 0o777 if bashrc.exists() else 0o644)
        staged.replace(bashrc)
    finally:
        staged.unlink(missing_ok=True)


def install_required_extensions():
    installed = installed_extension_ids()
    missing = [EXTENSIONS[name] for name in REQUIRED_EXTENSIONS if EXTENSIONS[name] not in installed]
    if not missing:
        return
    version = subprocess.check_output(['gnome-shell', '--version'], text=True)
    match = re.search(r'\b(\d+)\.', version)
    if not match:
        raise SystemExit('Could not determine the GNOME Shell version.')
    major = match.group(1)
    for uuid in missing:
        query = urllib.parse.urlencode({'uuid': uuid, 'shell_version': major})
        try:
            with urllib.request.urlopen('https://extensions.gnome.org/extension-info/?' + query, timeout=30) as response:
                info = json.load(response)
            download = urllib.parse.urljoin('https://extensions.gnome.org', info['download_url'])
            if not download.startswith('https://extensions.gnome.org/download-extension/'):
                raise ValueError('Unexpected extension download URL')
            with tempfile.TemporaryDirectory() as directory:
                archive = Path(directory) / 'extension.zip'
                with urllib.request.urlopen(download, timeout=60) as response:
                    archive.write_bytes(response.read())
                with zipfile.ZipFile(archive) as package:
                    metadata = json.loads(package.read('metadata.json'))
                if metadata['uuid'] != uuid or major not in metadata['shell-version']:
                    raise ValueError('The extension package is incompatible with this GNOME version')
                subprocess.run(['gnome-extensions', 'install', str(archive)], check=True)
            print(f'Installed {uuid} from extensions.gnome.org.')
        except (OSError, ValueError, KeyError, subprocess.CalledProcessError, zipfile.BadZipFile) as error:
            raise SystemExit(f'Could not install {uuid}: {error}') from error


def shell_is_running():
    from gi.repository import Gio, GLib

    try:
        bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
        reply = bus.call_sync('org.freedesktop.DBus', '/org/freedesktop/DBus',
                              'org.freedesktop.DBus', 'NameHasOwner',
                              GLib.Variant('(s)', ('org.gnome.Shell',)),
                              GLib.VariantType.new('(b)'), Gio.DBusCallFlags.NONE, 2000, None)
        return reply.unpack()[0]
    except GLib.Error:
        return False


def installed_extension_ids():
    from gi.repository import GLib

    directories = [GLib.get_user_data_dir(), *GLib.get_system_data_dirs()]
    installed = set()
    for directory in directories:
        path = Path(directory) / 'gnome-shell/extensions'
        if path.is_dir():
            installed.update(metadata.parent.name for metadata in path.glob('*/metadata.json'))
    return installed


def install_theme(source, backup):
    data_home = Path(os.environ.get('XDG_DATA_HOME', Path.home() / '.local/share'))
    target = data_home / 'themes/ZorinViolet'
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=target.parent) as directory:
        staged = Path(directory) / 'ZorinViolet'
        shutil.copytree(source / '.local/share/themes/ZorinViolet', staged)
        if target.exists() or target.is_symlink():
            saved = backup / '.local/share/themes/ZorinViolet'
            saved.parent.mkdir(parents=True, exist_ok=True)
            if target.is_symlink():
                shutil.copy2(target, saved, follow_symlinks=False)
                target.unlink()
            else:
                shutil.copytree(target, saved, symlinks=True)
                shutil.rmtree(target)
        else:
            (backup / 'new-theme.txt').write_text(str(target) + '\n')
        staged.replace(target)
    print(f'Installed theme in {target}.')


def activate_shell_theme(backup):
    from gi.repository import Gio

    shell = Gio.Settings.new('org.gnome.shell')
    # The User Themes schema may not be visible to the current session yet.
    # Its stored preference can still be selected before the next login.
    path = '/org/gnome/shell/extensions/user-theme/'
    previous = subprocess.check_output(['dconf', 'dump', path])
    directory = backup / 'extension-settings'
    directory.mkdir(exist_ok=True)
    (directory / 'user-theme.dconf').write_bytes(previous)
    (backup / 'enabled-extensions.txt').write_text(
        shell.get_value('enabled-extensions').print_(True) + '\n')
    (backup / 'disabled-extensions.txt').write_text(
        shell.get_value('disabled-extensions').print_(True) + '\n')
    (backup / 'disable-user-extensions.txt').write_text(
        shell.get_value('disable-user-extensions').print_(True) + '\n')
    subprocess.run(['dconf', 'write', path + 'name', "'ZorinViolet'"], check=True)
    uuid = EXTENSIONS['user-theme']
    required = [uuid]
    installed = installed_extension_ids()
    required.extend(EXTENSIONS[name] for name in REQUIRED_EXTENSIONS if EXTENSIONS[name] in installed)
    if EXTENSIONS['window-padding'] not in installed:
        print('Window Padding is missing. Maximized-window gaps require this extension:')
        print('https://extensions.gnome.org/extension/11381/window-padding/')
    enabled = shell.get_strv('enabled-extensions')
    for extension in required:
        if extension not in enabled:
            enabled.append(extension)
    disabled = [item for item in shell.get_strv('disabled-extensions') if item not in required]
    # Match the source desktop's dock instead of running two docks together.
    if EXTENSIONS['dash-to-dock'] in required:
        conflicts = {'zorin-taskbar@zorinos.com', 'zorin-dash@zorinos.com', 'ubuntu-dock@ubuntu.com'}
        enabled = [item for item in enabled if item not in conflicts]
        disabled = list(dict.fromkeys([*disabled, *sorted(conflicts)]))
    if not shell.set_strv('disabled-extensions', disabled):
        raise RuntimeError('GNOME could not update disabled extensions.')
    if not shell.set_strv('enabled-extensions', enabled):
        raise RuntimeError('GNOME could not enable the required desktop extensions.')
    if not shell.set_boolean('disable-user-extensions', False):
        raise RuntimeError('GNOME could not turn on extensions.')
    Gio.Settings.sync()
    if shutil.which('gnome-extensions') and shell_is_running():
        environment = {**os.environ, 'LC_ALL': 'C'}
        status = subprocess.run(['gnome-extensions', 'info', uuid],
                                capture_output=True, text=True, env=environment)
        if status.returncode == 0:
            # Reload an already loaded theme after replacing its stylesheet.
            subprocess.run(['gnome-extensions', 'disable', uuid],
                           capture_output=True, env=environment)
            enabled_result = subprocess.run(['gnome-extensions', 'enable', uuid],
                                            capture_output=True, env=environment)
            if enabled_result.returncode:
                shell.set_strv('enabled-extensions', enabled)
                shell.set_strv('disabled-extensions', disabled)
                Gio.Settings.sync()
                print('GNOME could not reload User Themes. Log out and back in.')
        else:
            print('User Themes is not discovered by this session yet. Log out and back in.')
    print('ZorinViolet selected. Run python3 install.py --check to check theme activation.')


def check_theme():
    from gi.repository import Gio

    shell = Gio.Settings.new('org.gnome.shell')
    data_home = Path(os.environ.get('XDG_DATA_HOME', Path.home() / '.local/share'))
    candidates = [Path.home() / '.themes/ZorinViolet/gnome-shell/gnome-shell.css',
                  data_home / 'themes/ZorinViolet/gnome-shell/gnome-shell.css']
    for directory in os.environ.get('XDG_DATA_DIRS', '/usr/local/share:/usr/share').split(':'):
        candidates.append(Path(directory) / 'themes/ZorinViolet/gnome-shell/gnome-shell.css')
    stylesheet = next((path for path in candidates if path.is_file()), None)
    uuid = EXTENSIONS['user-theme']
    selected = subprocess.check_output(
        ['dconf', 'read', '/org/gnome/shell/extensions/user-theme/name'], text=True).strip()
    print(f'Theme file used by User Themes: {stylesheet or "MISSING"}')
    print(f'Selected theme: {selected or "DEFAULT"}')
    print(f'Extensions switch enabled: {not shell.get_boolean("disable-user-extensions")}')
    print(f'User Themes enabled: {uuid in shell.get_strv("enabled-extensions")}')
    print(f'User Themes explicitly disabled: {uuid in shell.get_strv("disabled-extensions")}')
    installed = installed_extension_ids()
    for name in REQUIRED_EXTENSIONS:
        uuid = EXTENSIONS[name]
        print(f'{name} installed: {uuid in installed}; enabled: {uuid in shell.get_strv("enabled-extensions")}')
    if shutil.which('gnome-extensions') and shell_is_running():
        subprocess.run(['gnome-extensions', 'info', uuid],
                       env={**os.environ, 'LC_ALL': 'C'})
    else:
        print('Live GNOME session unavailable. Log in to GNOME and repeat this check.')


def restore_extension_settings(source, backup):
    if not shutil.which('dconf'):
        print('Extension settings skipped. dconf is unavailable.')
        return
    installed = installed_extension_ids()
    for settings in sorted((source / '.config/gnome-extension-settings').glob('*.dconf')):
        name = settings.stem
        if name == 'user-theme':
            continue  # Applied separately, including on a fresh GNOME session.
        if EXTENSIONS.get(name) not in installed:
            print(f'Skipped {name}. The extension is not installed.')
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
    parser.add_argument('--check', action='store_true', help='show theme activation status without changing settings')
    args = parser.parse_args()
    if os.geteuid() == 0:
        parser.exit(1, 'Run as your desktop user. Only package installation uses sudo.\n')
    if args.check:
        check_theme()
        return
    source = Path(__file__).resolve().parent
    config = Path(os.environ.get('XDG_CONFIG_HOME', Path.home() / '.config'))
    state = Path(os.environ.get('XDG_STATE_HOME', Path.home() / '.local/state'))
    for name in FILES:
        if not (source / '.config' / name).is_file():
            parser.exit(1, f'Missing source file: {name}\n')
    if not (source / '.local/share/themes/ZorinViolet/gnome-shell/gnome-shell.css').is_file():
        parser.exit(1, 'Missing bundled ZorinViolet theme. Copy the complete dotfiles directory.\n')
    if args.dry_run:
        if not args.skip_packages:
            print('Install packages: ' + ', '.join(PACKAGES))
            print('Install missing Dash to Dock, Window Padding and Blur My Shell from extensions.gnome.org.')
        for name in FILES:
            print(f'Copy {name} to {config / name}')
        print('Install the bundled ZorinViolet theme and enable User Themes.')
        print('Add the bundled Bash prompt to ~/.bashrc, with a backup.')
        print(f'Backups will be stored under {state / "zorin-violet-dotfiles"}')
        if not args.skip_extension_settings:
            print('Import saved preferences for installed GNOME extensions.')
        return
    if not args.skip_packages:
        if not shutil.which('apt-get'):
            parser.exit(1, 'Package installation requires apt-get (Zorin OS / Ubuntu).\n')
        subprocess.run(['sudo', 'apt-get', 'update'], check=True)
        subprocess.run(['sudo', 'apt-get', 'install', '-y', *PACKAGES], check=True)
        install_required_extensions()
    if not shutil.which('dconf'):
        parser.exit(1, 'Install dconf-cli before using --skip-packages.\n')
    from gi.repository import Gio
    Gio.Settings.new('org.gnome.shell')  # Validate the GNOME settings dependency before copying files.

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
    install_theme(source, backup)
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
    install_prompt(backup)
    if not args.skip_extension_settings:
        restore_extension_settings(source, backup)
    activate_shell_theme(backup)
    print('Installed. Restart Kitty and Wofi. Log out and back in to reload desktop styling.')


if __name__ == '__main__':
    main()
