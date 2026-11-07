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

The installer downloads missing Dash to Dock, Window Padding and Blur My Shell
from extensions.gnome.org, choosing a package for the installed GNOME version.
It enables them and disables Zorin Taskbar, Zorin Dash and Ubuntu Dock so they
do not compete with Dash to Dock. Other extension preferences are imported
when the corresponding extensions are already installed.
The bundled ZorinViolet theme is installed automatically, and User Themes is
enabled to apply it to the top bar. Log out and back in after installation.
The installer turns on the Extensions master switch and saves its previous value.
It reloads User Themes when the running GNOME session already knows about it.

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
User Themes comes from the system package installer. Dash to Dock, Window
Padding and Blur My Shell are downloaded from the official GNOME extension
catalog when missing. Other extensions must be installed separately.

## Options

- --dry-run lists the planned changes without modifying the system.
- --skip-packages copies configurations without installing applications or downloading extensions.
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

## Top bar still uses the default appearance

After logging out and back in, open a terminal in the dotfiles folder and run:

    python3 install.py --check

The output shows the first matching theme file, the selected theme name,
the extensions master switch and the live User Themes extension status.
The selected theme should be ZorinViolet and User Themes should be ACTIVE.
A theme under ~/.themes takes precedence over ~/.local/share/themes; check
the reported path if you have an older copy installed.

## Window gaps

Window Padding keeps margins around maximized windows. The installer downloads
and enables it automatically. Zorin Tiling Shell controls gaps in tiled layouts.

The saved values are 4 pixels at the top and 8 pixels at the other screen edges
for Window Padding, plus 4 pixels for both inner and outer Tiling Shell gaps.
These values are exported explicitly so another installation uses the same gaps.
Extension settings can be imported before GNOME discovers newly installed
extensions. Log out and back in afterward.

## Match the desktop dock

Copy the complete folder, including .config and .local, before running install.py.
The bundled theme provides 16-pixel rounded corners and violet dock borders.
The dock preference export disables the fixed, full-width dock appearance and
uses the bottom auto-hiding Dash to Dock layout. Physical monitor connector
names are excluded so a VM can use its own display.

The installer enables User Themes, Dash to Dock, Window Padding and Blur My Shell.
It does not require Rounded Window Corners to round the dock. After installation,
log out and back in. Run python3 install.py --check to check which extensions
are installed and enabled.

## GDM wallpaper synchronization

Install Violet Windows separately using its install.sh script. In its preferences,
choose Enable sync under Follow desktop wallpaper. Alternatively, from its
repository directory, run:

    sudo python3 install-gdm.py --sync-wallpaper

The installer includes the per-monitor background component, so a fresh Zorin
VM can follow its own desktop wallpaper. Administrator authorization is needed
once. Future local wallpaper changes are synchronized automatically.
