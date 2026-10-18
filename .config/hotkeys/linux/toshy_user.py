# Linux side of ~/.config/HOTKEYS.md: the Karabiner rules, re-expressed for Toshy (xwaykeyz).
# `converge sync` splices each "### toshy-slice: NAME" block below into the matching
# SLICE_MARK_START/END block of ~/.config/toshy/toshy_config.py (Toshy keeps slices on upgrade).
#
# Toshy's model: Cmd = RC (physical Alt on the Keychron), Option = Alt (physical Win),
# Ctrl = LC in terminals and Super in GUI apps. Hyper (Caps held) emits Shift+Ctrl+Alt+Super+key,
# which GNOME binds (~/.config/hotkeys/linux/gnome.dconf): the Linux stand-in for Karabiner -> Magnet/open -a.

### toshy-slice: kbtype_override
keyboards_UserCustom_dct = {
    # Add your keyboard device here if its type is misidentified.
    # Valid types to map device to: Apple, Windows, IBM, Chromebook (case sensitive)
    'Keychron K1 K1-Keyboard': 'Windows',
}

### toshy-slice: user_custom_functions
# Registered here, ahead of Toshy's own modmaps, because the first matching modmap wins.

# Karabiner "Caps Lock + App Switching": tap = Esc, hold = Hyper.
setup_hyper(Key.CAPSLOCK, tap_output=Key.ESC,
            when=lambda ctx: cnfg.screen_has_focus and not ctx_app_is_remote)

# Karabiner "Right Cmd held -> Ctrl": the thumb key takes Ctrl's role (Super in GUI apps, Ctrl in terminals).
modmap("home-gpu Right Cmd is Ctrl - GUI", {
    Key.RIGHT_ALT:              Key.LEFT_META,
}, when=lambda ctx: cnfg.screen_has_focus and ctx_kbd_is_windows and
                    not ctx_app_is_terminal and not ctx_app_is_remote)
modmap("home-gpu Right Cmd is Ctrl - Terms", {
    Key.RIGHT_ALT:              Key.LEFT_CTRL,
}, when=lambda ctx: cnfg.screen_has_focus and ctx_kbd_is_windows and ctx_app_is_terminal)

### toshy-slice: user_apps
keymap("home-gpu terminals (Karabiner terminal rules)", {
    C("RC-Space"):              C("LC-Space"),          # Cmd+Space -> tmux leader
    C("LC-Space"):              C("LC-Space"),          # Ctrl+Space stays the leader (not GNOME input switching)
    C("RC-p"):                  C("F12"),               # Cmd+P -> tmux switcher / Neovim smart open
    C("RC-h"):                  C("LC-h"),              # Cmd+h/j/k/l -> pane moves
    C("RC-j"):                  C("LC-j"),
    C("RC-k"):                  C("LC-k"),
    C("RC-l"):                  C("LC-l"),
}, when=lambda ctx: cnfg.screen_has_focus and ctx_app_is_terminal)

keymap("home-gpu Cursor/VS Code", {
    C("Super-Space"):           C("LC-Space"),          # Ctrl+Space: suggest in the editor, tmux leader in its terminal
}, when=lambda ctx: cnfg.screen_has_focus and hmp_is_vscode(ctx))

keymap("home-gpu global", {
    C("RC-Tab"):                [bind, C("Super-Tab")],         # Cmd+Tab -> switcher; frees Option+Tab for tmux
    C("Shift-RC-Tab"):          [bind, C("Shift-Super-Tab")],
    C("F3"):                    C("SysRq"),                     # F3 -> screenshot UI (copies to clipboard)
    C("RC-F3"):                 C("C-Super-d"),                 # Cmd+F3 -> show desktop
    C("Super-RC-q"):            C("C-Super-l"),                 # Ctrl+Cmd+Q -> lock screen (GUI apps)
    C("LC-RC-q"):               C("C-Super-l"),                 # Ctrl+Cmd+Q -> lock screen (terminals)
}, when=lambda ctx: cnfg.screen_has_focus and not ctx_app_is_remote)
