"""Explicit consent and read-only planning for optional GNOME extensions.

This module never downloads files, changes settings, or invokes subprocesses.
The installer applies only the operations in a confirmed ExtensionPlan.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class ExtensionOption:
    key: str
    name: str
    uuid: str
    purpose: str
    downloadable: bool = True


OPTIONS = (
    ExtensionOption('user-theme', 'User Themes', 'user-theme@gnome-shell-extensions.gcampax.github.com', 'Top bar theme'),
    ExtensionOption('dash-to-dock', 'Dash to Dock', 'dash-to-dock@micxgx.gmail.com', 'Dock layout'),
    ExtensionOption('window-padding', 'Window Padding', 'window-padding@pvlamkhtn.github.io', 'Maximized-window margins'),
    ExtensionOption('blur-my-shell', 'Blur My Shell', 'blur-my-shell@aunetx', 'Overview and panel effects'),
    ExtensionOption('system-monitor', 'System Monitor', 'system-monitor@gnome-shell-extensions.gcampax.github.com', 'CPU, memory and network indicator'),
    ExtensionOption('zorin-appindicator', 'Zorin AppIndicator', 'zorin-appindicator@zorinos.com', 'Existing extension: settings only', False),
    ExtensionOption('zorin-desktop-icons', 'Zorin Desktop Icons', 'zorin-desktop-icons@zorinos.com', 'Existing extension: settings only', False),
    ExtensionOption('zorin-tiling-shell', 'Zorin Tiling Shell', 'zorin-tiling-shell@zorinos.com', 'Existing extension: settings only', False),
)
BY_KEY = {option.key: option for option in OPTIONS}
EXTENSIONS = {option.key: option.uuid for option in OPTIONS}
DOCKS = {
    'zorin-taskbar@zorinos.com': 'Zorin Taskbar',
    'zorin-dash@zorinos.com': 'Zorin Dash',
    'ubuntu-dock@ubuntu.com': 'Ubuntu Dock',
}


@dataclass(frozen=True)
class ExtensionPlan:
    """Immutable operations approved together; empty means no extension changes."""
    install: tuple[str, ...] = ()
    enable: tuple[str, ...] = ()
    configure: tuple[str, ...] = ()
    disable: tuple[str, ...] = ()
    skipped: tuple[str, ...] = ()


def parse_selection(value: str) -> set[str]:
    """Accept displayed numbers or documented keys; empty input selects nothing."""
    selected = set()
    for token in value.replace(',', ' ').split():
        if token.isdecimal() and 1 <= int(token) <= len(OPTIONS):
            selected.add(OPTIONS[int(token) - 1].key)
        elif token in BY_KEY:
            selected.add(token)
        else:
            raise ValueError(f'Unknown extension selection: {token}')
    return selected


def build_plan(selected, installed, enabled, *, allow_downloads=True,
               import_settings=True, replace_dock=False) -> ExtensionPlan:
    """Do not guess consent from installed status, dependencies, or defaults."""
    unknown = set(selected) - BY_KEY.keys()
    if unknown:
        raise ValueError('Unknown extensions: ' + ', '.join(sorted(unknown)))
    install, activate, configure, skipped = [], [], [], []
    conflicts = tuple(sorted(set(enabled) & DOCKS.keys()))
    for option in OPTIONS:
        if option.key not in selected:
            continue
        present = option.uuid in installed
        if not present:
            if not option.downloadable or not allow_downloads:
                skipped.append(option.key)
                continue
            install.append(option.key)
        if import_settings:
            configure.append(option.key)
        if option.downloadable:
            if option.key != 'dash-to-dock' or not conflicts or replace_dock:
                activate.append(option.key)
    disable = conflicts if replace_dock and 'dash-to-dock' in activate else ()
    return ExtensionPlan(tuple(install), tuple(activate), tuple(configure), disable, tuple(skipped))


def confirm(prompt, *, ask=input) -> bool:
    """Only an explicit yes grants consent, including when stdin is piped."""
    try:
        return ask(prompt).strip().lower() in ('y', 'yes')
    except (EOFError, KeyboardInterrupt):
        return False


def print_catalog(installed, *, output=print):
    output('Optional GNOME extensions — nothing selected by default')
    for number, option in enumerate(OPTIONS, 1):
        present = option.uuid in installed
        state = 'installed' if present else 'not installed' if option.downloadable else 'unavailable'
        output(f'  {number}  [ ] {option.name} — {option.purpose} ({state})')


def print_plan(plan, *, output=print):
    def names(keys):
        return ', '.join(BY_KEY[key].name for key in keys) or 'none'
    output('Extension plan')
    output('  Install: ' + names(plan.install))
    output('  Enable: ' + names(plan.enable))
    output('  Import settings: ' + names(plan.configure))
    output('  Disable other docks: ' + (', '.join(DOCKS[uuid] for uuid in plan.disable) or 'none'))
    if plan.skipped:
        output('  Skip unavailable extensions or downloads disabled by --skip-packages: ' + names(plan.skipped))
    if 'user-theme' in plan.enable:
        output('  Apply the bundled ZorinViolet shell theme through User Themes.')


def choose_plan(installed, enabled, *, requested=None, skip=False, assume_yes=False,
                dry_run=False, allow_downloads=True, import_settings=True,
                replace_dock=False, ask=input, output=print) -> ExtensionPlan:
    """Collect selection, dock consent, and final consent before any mutation.

    --yes confirms an explicit selection; it never selects extensions itself.
    --dry-run displays plans without prompting or applying them.
    """
    if skip:
        output('All extension installation, activation and settings changes skipped.')
        return ExtensionPlan()
    print_catalog(installed, output=output)
    if requested is None:
        if dry_run:
            raw = ''
        else:
            try:
                raw = ask('Selection (numbers or keys, Enter to skip): ')
            except (EOFError, KeyboardInterrupt):
                raw = ''
    else:
        raw = requested
    selected = parse_selection(raw)
    if not selected:
        output('No extensions selected; extension settings and activation stay unchanged.')
        return ExtensionPlan()
    conflicts = tuple(sorted(set(enabled) & DOCKS.keys()))
    dock_available = EXTENSIONS['dash-to-dock'] in installed or allow_downloads
    if 'dash-to-dock' in selected and dock_available and conflicts and not replace_dock:
        output('Dash to Dock conflicts with: ' + ', '.join(DOCKS[uuid] for uuid in conflicts))
        if not dry_run:
            # --yes does not authorize changing a different dock.
            replace_dock = confirm('Disable these docks? [y/N]: ', ask=ask)
        if not replace_dock:
            output('Dash to Dock will not be enabled; the existing docks stay unchanged.')
    plan = build_plan(selected, installed, enabled, allow_downloads=allow_downloads,
                      import_settings=import_settings, replace_dock=replace_dock)
    print_plan(plan, output=output)
    if dry_run or assume_yes or confirm('Apply this extension plan? [y/N]: ', ask=ask):
        return plan
    output('Extension plan cancelled; no extensions or extension settings will change.')
    return ExtensionPlan()
