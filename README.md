# Zorin Violet dotfiles

Configuration files for Kitty, Wofi, GTK 3 and GTK 4, plus saved preferences
for the GNOME extensions used by this desktop. Nautilus shares the GTK styling.

## Installation

Copy the entire folder, including its hidden .config directory, and open a
terminal in the folder. Preview the changes, then run the installer.

    python3 install.py --dry-run
    python3 install.py

Run as your regular desktop user. The installer requests administrator
authorization through sudo to install Kitty, Wofi, Nautilus, JetBrains Mono,
wl-clipboard, dconf-cli, PyGObject and the GNOME Shell extensions package
from the distribution package manager. The latter provides User Themes.

Existing configuration files are backed up before replacement. Backups are
stored under XDG_STATE_HOME/zorin-violet-dotfiles, or
~/.local/state/zorin-violet-dotfiles when XDG_STATE_HOME is unset. The installer
prints the exact backup directory. Each backup includes new-files.txt listing
files that did not exist before installation.

Saved extension preferences are imported only for extensions already installed.
Install the extensions separately if you want to restore their preferences.
The bundled ZorinViolet theme is installed automatically, and User Themes is
enabled to apply it to the top bar. Log out and back in after installation.
If the Extensions app has its master switch turned off, enable it there.

Restart Kitty and Wofi afterward. Log out and back in for desktop styling.

## Included extension settings

The bundle includes saved preferences for the following extensions:

- Blur My Shell — blur-my-shell@aunetx
- Dash to Dock — dash-to-dock@micxgx.gmail.com
- System Monitor — system-monitor@gnome-shell-extensions.gcampax.github.com
- User Themes — user-theme@gnome-shell-extensions.gcampax.github.com
- Window Padding — window-padding@pvlamkhtn.github.io
- Zorin AppIndicator — zorin-appindicator@zorinos.com
- Zorin Desktop Icons — zorin-desktop-icons@zorinos.com
- Zorin Tiling Shell — zorin-tiling-shell@zorinos.com

These preferences are stored under .config/gnome-extension-settings. The
installer imports them only when the corresponding extension is installed.
Missing extensions must be installed separately, except User Themes, which is
provided by the package installer and enabled automatically with ZorinViolet.

## Options

- --dry-run lists the planned changes without modifying the system.
- --skip-packages copies configurations without installing applications.
- --skip-extension-settings skips the optional extension preference imports.
  The bundled shell theme and User Themes activation are still applied.

## Restore a backup

Copy the desired files from the backup's .config directory back into your
configuration directory. Files listed in new-files.txt were newly installed.

To restore an extension's preferences, open a terminal in the backup directory
and use the matching extension path. For example, for Dash to Dock, run
the following commands from your regular desktop session.

    dconf reset -f /org/gnome/shell/extensions/dash-to-dock/
    dconf load /org/gnome/shell/extensions/dash-to-dock/ < extension-settings/dash-to-dock.dconf

Previous extension preferences are saved under extension-settings in the backup.

## Included theme files

The complete ZorinViolet theme is bundled under .local/share/themes/ZorinViolet.
Copy this hidden directory along with .config when moving the dotfiles to a VM.
The top bar styling lives in gnome-shell/gnome-shell.css inside that theme.

Existing themes are backed up under .local/share/themes in the backup directory.
User Themes preferences and the enabled and disabled extension lists are also
backed up before the installer changes them.
