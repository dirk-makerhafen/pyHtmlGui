import sys
import os
import subprocess
import whichcraft
import webbrowser


class Browser:
    def __init__(self, browsername="default", executable=None):
        self.browsername = browsername
        self.executable = executable
        self.browserInstance = None
        if browsername == "default":
            self.browserInstance = BrowserDefault(self.executable)
        elif browsername == "chrome":
            self.browserInstance = BrowserChrome(self.executable)
        elif browsername == "electron":
            self.browserInstance = BrowserElectron(self.executable)
        else:
            raise Exception("Unknown mode '%s', use 'default' for system browser or 'chrome' or 'electron'")
    def open(self, browser_args, **kwargs) -> None:
        self.browserInstance.run(browser_args, **kwargs)


class BrowserDefault:
    def __init__(self, executable:str = None):
        self.executable = executable

    def run(self,browser_args, **kwargs) -> None:
        start_url = browser_args[0]
        if not start_url.startswith("http"):
            start_url = "http://" + start_url
        if self.executable is None:
            webbrowser.open(start_url)
        else:
            cmd = [ self.executable, start_url ]
            subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=sys.stderr, stdin=subprocess.PIPE)


class BrowserElectron:
    def __init__(self, executable: str) -> None:
        self.executable = executable
        if self.executable is None:
            self.executable = self._find_path()
        if self.executable is None:
            raise Exception("Electron executable could not be found")
        if not os.path.isfile(self.executable):
            raise Exception("Electron executable could not be found at '%s'" % self.executable)

    def run(self, browser_args, env=None, **kwargs) -> None:
        if env is None:
            env = os.environ.copy()
        cmd = [
                  self.executable,
                  '--no-sandbox',
                  '--disable-http-cache',
              ] + browser_args
        subprocess.Popen(cmd, stdout=sys.stdout, stderr=sys.stderr, stdin=subprocess.PIPE, env=env)

    @staticmethod
    def _find_path():
        if sys.platform in ['win32', 'win64']:
            # It doesn't work well passing the .bat file to Popen, so we get the actual .exe
            bat_path = whichcraft.which('electron')
            if bat_path is None:
                return None
            return os.path.join(bat_path, r'..\node_modules\electron\dist\electron.exe')
        elif sys.platform in ['darwin', 'linux']:
            return whichcraft.which('electron')
        else:
            return None


class BrowserChrome:
    def __init__(self, executable: str) -> None:
        self.executable = executable
        if self.executable is None:
            self.executable = self._find_path()
        if self.executable is None:
            raise Exception("Chrome executable could not be found")
        if not os.path.isfile(self.executable):
            raise Exception("Chrome executable could not be found at '%s'" % self.executable)

    def run(self, browser_args, env=None, **kwargs) -> None:
        start_url = browser_args[0]
        if not start_url.startswith("http"):
            start_url = "http://" + start_url
        cmd = [
            self.executable,
            start_url,
        ]
        subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=sys.stderr, stdin=subprocess.PIPE)

    def _find_path(self):
        if sys.platform in ['win32', 'win64']:
            return self._find_chrome_win()
        elif sys.platform == 'darwin':
            return self._find_chrome_mac()
        elif sys.platform.startswith('linux'):
            return self._find_chrome_linux()
        else:
            return None

    @staticmethod
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

    @staticmethod
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

    @staticmethod
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
