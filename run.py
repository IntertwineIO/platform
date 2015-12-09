#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
Manages the execution of Intertwine's platform app

Usage:
    run [options] [<command>]

Options:
    -h --help           This message
    -d --debug          Turn on debug
    -H --host HOST      Set host [default: 0.0.0.0]
    -p --port PORT      Set port [default: 8000]
    -c --config CONFIG  Set config [default: demo] (options: dev, demo, local)
'''
from __future__ import print_function

from intertwine import create_app
from config import DevConfig, DemoConfig, LocalDemoConfig


def main(**options):
    app = create_app(options.get('config'))
    host = app.config.get('HOST') or options.get('host')
    port = app.config.get('PORT') or options.get('port')
    debug = app.config.get('DEBUG') or options.get('debug')
    app.run(host=host, port=int(port), debug=debug)


if __name__ == '__main__':
    import sys
    from textwrap import dedent as dd

    try:
        from docopt import docopt
    except ImportError as e:
        err_msg = dd('''
        ERROR: Docopt is not installed.  Please install to proceed.

            > pip install docopt
        ''')
        print(err_msg, file=sys.stderr)
        sys.exit()

    options = {k.lstrip('--'): v for k, v in docopt(__doc__).items()}
    config_mapping = {
        'dev': DevConfig,
        'demo': DemoConfig,
        'local': LocalDemoConfig
    }
    options['config'] = config_mapping.get(options['config'], DemoConfig)
    main(**options)
