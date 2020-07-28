import sys
import os
import subprocess
import whichcraft

name = 'Electron'

def run(path, options, start_url):

    cmd = [path] + options['cmdline_args']
    if "main_js" in options:
        cmd += [options["main_js"]]

    cmd +=  [ start_url ]
    if "main_js_argv" in options:
        cmd += options["main_js_argv"]
    print("launching electron ")
    subprocess.Popen(cmd, stdout=sys.stdout, stderr=sys.stderr, stdin=subprocess.PIPE)


def find_path():
    if sys.platform in ['win32', 'win64']:
        # It doesn't work well passing the .bat file to Popen, so we get the actual .exe
        bat_path = whichcraft.which('electron')
        return os.path.join(bat_path, r'..\node_modules\electron\dist\electron.exe')
    elif sys.platform in ['darwin', 'linux']:
        # This should work find...
        return whichcraft.which('electron')
    else:
        return None

