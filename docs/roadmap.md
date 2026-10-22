# Workspace customization roadmap

## Available

- Five workspaces and reusable layouts; manual pane split, movement, resizing, floating and layout export.
- Existing CLI launcher and on-demand application panes; normal shells remain available.
- Fzf app picker and four independently searchable public catalogs, with bounded on-demand downloads, caching, and explicit Homebrew installation. Known installed adapters support tiled/floating/current-menu-pane launch. See [catalogs](catalogs.md).
- Separate Ghostty windows/clients for multiple monitors, with saved Zellij arrangements. OS window positions are not saved by layouts.
- Optional `oh-my-pi` theme: shared semantic JSON, generated Ghostty and Zellij adapters, and `command-center --theme oh-my-pi --session NEW_NAME`. Existing defaults remain the baseline.

## Planned, not implemented

1. Add reviewed palette adapters for full/compact btop, Lazygit, Newsboat, and future launcher tools. Preserve each private file and offer inspectable differences before activation.
2. Add persistent theme preference and a theme-switching command only after defining backup, rollback, live-session and application reload behavior. Keep terminal selection separate from remote app settings; do not imply one flag recolors every process.
3. Associate optional appearance choices with user workspace profiles and an application launcher, independently of pane geometry and saved working directories. Retain native Zellij layouts and keyboard management.
4. Explore monitor-specific workspace profiles and window placement using supported platform facilities. Share the palette across windows without enforcing pane counts or resetting sessions.
5. Add user-defined app registrations and a saved-setup picker to the app menu. Preserve native layouts and distinguish resuming a live session from reconstructing commands after exit. Source catalogs are discovery metadata, not executable launch recipes.

## Theme decision — October 14, 2026

Use the user's nine-color interpretation of Oh My Pi `dark-terminal` as an opt-in palette. Keep one source and generate tool-specific adapters with Python's standard library. Ghostty runs locally on the MacBook Air; Debian Lenovo needs terminfo and application/Zellij configuration, not a remote Ghostty installation. Theme changes remain explicit and reviewable. No installer migration, default-theme change, automatic application recoloring, shell startup edit, or new orchestration layer is part of this milestone. See [theme activation and extension](themes.md) and [validation evidence](validation.md).
