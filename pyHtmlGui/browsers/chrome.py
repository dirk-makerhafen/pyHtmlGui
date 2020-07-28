import sys, subprocess, os

# Every browser specific module must define run(), find_path() and name like this

name = 'Google Chrome/Chromium'

def run(path, options, start_url):
    if "app_mode" not in options:
        options['app_mode'] = False
    if options['app_mode']:
        print(start_url, options)
        subprocess.Popen([path, '--app=%s' % start_url] + options['cmdline_args'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.PIPE)
    else:
        args = options['cmdline_args'] + [start_url]
        subprocess.Popen([path, '--new-window'] + args, stdout=subprocess.PIPE, stderr=sys.stderr, stdin=subprocess.PIPE)


def find_path():
    if sys.platform in ['win32', 'win64']:
        return _find_chrome_win()
    elif sys.platform == 'darwin':
        return _find_chrome_mac()
    elif sys.platform.startswith('linux'):
        return _find_chrome_linux()
    else:
        return None


def _find_chrome_mac():
    default_dir = r'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'
    if os.path.exists(default_dir):
        return default_dir
    # use mdfind ci to locate Chrome in alternate locations and return the first one
    name = 'Google Chrome.app'
    alternate_dirs = [x for x in subprocess.check_output(["mdfind", name]).decode().split('\n') if x.endswith(name)] 
    if len(alternate_dirs):
        return alternate_dirs[0] + '/Contents/MacOS/Google Chrome'
    return None


def _find_chrome_linux():
    import whichcraft as wch
    chrome_names = ['chromium-browser',
                    'chromium',
                    'google-chrome',
                    'google-chrome-stable']

    for name in chrome_names:
        chrome = wch.which(name)
        if chrome is not None:
            return chrome
    return None


def _find_chrome_win():
    import winreg as reg
    reg_path = r'SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\chrome.exe'

    for install_type in reg.HKEY_CURRENT_USER, reg.HKEY_LOCAL_MACHINE:
        try:
            reg_key = reg.OpenKey(install_type, reg_path, 0, reg.KEY_READ)
            chrome_path = reg.QueryValue(reg_key, None)
            reg_key.Close()
        except WindowsError:
            chrome_path = None
        else:
            break

    return chrome_path
