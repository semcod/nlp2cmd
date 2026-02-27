"""
Desktop automation domain templates for NLP2CMD.

Contains templates for desktop app control, window management,
email client operations, and multi-tab browser management.
"""

DESKTOP_TEMPLATES = {
    # --- App Launch ---
    'launch_app': "{app} &",
    'launch_terminal': "xfce4-terminal &",
    'launch_browser': "firefox &",
    'launch_firefox': "firefox &",
    'launch_chrome': "google-chrome &",
    'launch_thunderbird': "thunderbird &",
    'launch_editor': "mousepad &",
    'launch_calculator': "galculator &",
    'launch_file_manager': "thunar &",
    'launch_vscode': "code &",
    'launch_libreoffice': "libreoffice &",
    'launch_libreoffice_writer': "libreoffice --writer &",
    'launch_libreoffice_calc': "libreoffice --calc &",
    'launch_gimp': "gimp &",
    'launch_vlc': "vlc &",
    'launch_settings': "xfce4-settings-manager &",

    # --- App with URL ---
    'open_url_in_browser': "firefox '{url}' &",
    'open_url_in_chrome': "google-chrome '{url}' &",
    'open_url_generic': "xdg-open '{url}'",

    # --- Window Management ---
    'minimize_all': "wmctrl -k on",
    'restore_all': "wmctrl -k off",
    'show_desktop': "wmctrl -k on",
    'list_windows': "wmctrl -l",
    'close_window': 'wmctrl -c "{title}"',
    'focus_window': 'wmctrl -a "{title}"',
    'maximize_window': 'wmctrl -r "{title}" -b add,maximized_vert,maximized_horz',
    'minimize_window': "xdotool getactivewindow windowminimize",
    'close_active': "xdotool key alt+F4",

    # --- Tab Management ---
    'new_tab': "xdotool key ctrl+t",
    'close_tab': "xdotool key ctrl+w",
    'next_tab': "xdotool key ctrl+Tab",
    'prev_tab': "xdotool key ctrl+shift+Tab",
    'tab_1': "xdotool key ctrl+1",
    'tab_2': "xdotool key ctrl+2",
    'tab_3': "xdotool key ctrl+3",

    # --- Email (Thunderbird) ---
    'email_check': "thunderbird & sleep 2 && xdotool key ctrl+shift+t",
    'email_compose': "thunderbird & sleep 2 && xdotool key ctrl+n",
    'email_reply': "xdotool key ctrl+r",
    'email_reply_all': "xdotool key ctrl+shift+r",
    'email_forward': "xdotool key ctrl+l",
    'email_search': "xdotool key ctrl+k",
    'email_send': "xdotool key ctrl+Return",
    'email_address_book': "xdotool key ctrl+shift+b",

    # --- Email compose with details ---
    'email_compose_to': 'thunderbird & sleep 2 && xdotool key ctrl+n && sleep 1 && xdotool type "{to}" && xdotool key Tab',
    'email_compose_full': 'thunderbird & sleep 2 && xdotool key ctrl+n && sleep 1 && xdotool type "{to}" && xdotool key Tab Tab && xdotool type "{subject}" && xdotool key Tab',

    # --- Screenshot ---
    'screenshot_full': "gnome-screenshot -f /tmp/nlp2cmd_screenshot.png",
    'screenshot_window': "gnome-screenshot -w -f /tmp/nlp2cmd_screenshot.png",
    'screenshot_area': "gnome-screenshot -a -f /tmp/nlp2cmd_screenshot.png",
    'screenshot_delay': "gnome-screenshot -d {delay} -f /tmp/nlp2cmd_screenshot.png",

    # --- Keyboard & Typing ---
    'type_text': 'xdotool type --delay 30 "{text}"',
    'type_and_enter': 'xdotool type --delay 30 "{text}" && xdotool key Return',
    'press_key': "xdotool key {key}",
    'shortcut': "xdotool key {keys}",

    # --- xdotool/wmctrl combos ---
    'open_app_and_type': '{app} & sleep 2 && xdotool type --delay 30 "{text}"',
    'focus_and_type': 'wmctrl -a "{title}" && xdotool type --delay 30 "{text}"',
    'terminal_command': 'xfce4-terminal -e "bash -c \\"{command}; exec bash\\""',

    # --- Desktop actions ---
    'lock_screen': "xfce4-screensaver-command -l",
    'logout': "xfce4-session-logout --logout",
    'volume_up': "pactl set-sink-volume @DEFAULT_SINK@ +5%",
    'volume_down': "pactl set-sink-volume @DEFAULT_SINK@ -5%",
    'volume_mute': "pactl set-sink-mute @DEFAULT_SINK@ toggle",
    'brightness_up': "xbacklight -inc 10",
    'brightness_down': "xbacklight -dec 10",
}
