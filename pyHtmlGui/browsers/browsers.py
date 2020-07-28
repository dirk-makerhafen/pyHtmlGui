import subprocess as sps
import webbrowser as wbr
from ..browsers import chrome as Chrome
from ..browsers import edge as Edge
from ..browsers import electron as Electron

_browser_paths = {}
_browser_modules = {'chrome':   Chrome,
                    'electron': Electron,
                    'edge': Edge}

def open(start_url, options):
    print(start_url, options)
    mode = options.get('mode')

    if mode in [None, False]:
        # Don't open a browser
        pass
    elif mode == 'custom':
        # Just run whatever command the user provided
        sps.Popen(options['cmdline_args'], stdout=sps.PIPE, stderr=sps.PIPE, stdin=sps.PIPE)
    elif mode in _browser_modules:
        # Run with a specific browser
        browser_module = _browser_modules[mode]
        path = _browser_paths.get(mode)
        if path is None:
            # Don't know this browser's path, try and find it ourselves
            path = browser_module.find_path()
            _browser_paths[mode] = path

        if path is not None:
            browser_module.run(path, options, start_url)
        else:
            raise EnvironmentError("Can't find %s installation" % browser_module.name)
    else:
        # Fall back to system default browser
        wbr.open(start_url)


def set_path(browser_name, path):
    _browser_paths[browser_name] = path


def get_path(browser_name):
    return _browser_paths.get(browser_name)

