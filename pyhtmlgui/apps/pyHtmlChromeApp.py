import shlex, os, sys
import subprocess
import tempfile
import threading

from pyhtmlgui import Observable


class PyHtmlChromeApp():
    def __init__(self, url, executable=None, commandline_args = [], ):
        self.url = url
        self.executable = executable
        self.commandline_args = commandline_args
        if self.executable == None:
            self.executable = self._find_path()
        if self.executable == None or not os.path.exists(self.executable):
            raise Exception("Chrome executable not found at path '%s'" % self.executable)
        self.on_closed_event = Observable()
        self.on_show_event = Observable()

        self._subthread = None
        self._subprocess = None

    def close(self):
        if self._subprocess is not None:
            self._subprocess.terminate()

    def show(self):
        if self._subthread == None:
            self._subthread = threading.Thread(target=self._chrome_thread, daemon=True)
            self._subthread.start()


    def join(self):
        if self._subprocess is not None:
            self._subprocess.wait()

    def _chrome_thread(self):
        with tempfile.TemporaryDirectory() as tmpdirname:
            cmd = [self.executable]
            cmd.extend(self.commandline_args)
            # cmd.append("--kiosk")
            cmd.append("--no-default-browser-check")
            cmd.append("--disable-logging")
            cmd.append("--content-shell-hide-toolbar")
            cmd.append("--bwsi")
            cmd.append("--no-service-autorun")
            cmd.append("--no-first-run")
            cmd.append("--no-report-upload")
            cmd.append("--overscroll-history-navigation=0")
            cmd.append("--disable-pinch")
            cmd.append("--user-data-dir=\"%s\"" % tmpdirname)
            cmd.append("--app=%s" % self.url)
            print(cmd)
            self._subprocess = subprocess.Popen(shlex.split(shlex.join(cmd)), shell=False)
            self.on_show_event.notify_observers()
            self._subprocess.wait()
        self._subthread = None
        self._subprocess = None
        self.on_closed_event.notify_observers()

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
