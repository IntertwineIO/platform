#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Manages the execution of Intertwine's platform app

Usage:
    run [options] [<command>]

Options:
    -h --help           This message
    -d --debug          Turn on debug
    -H --host HOST      Set host [default: 0.0.0.0]
    -p --port PORT      Set port [default: 5000]
    -c --config CONFIG  Set config [default: demo] (options: dev, demo, local)
    -r --rebuild        Rebuilds local database
"""
import os

from intertwine import create_app
from config import DevConfig, DemoConfig, LocalDemoConfig


def main(**options):
    if options.get('rebuild'):
        # destroy old database
        fp = 'sqlite.db'
        fp = os.path.realpath(os.path.join(os.path.dirname(__file__), fp))
        os.system('rm {}'.format(fp))
        print('Removed file: {}'.format(fp))
    app = create_app(config=options.get('config'))
    if options.get('_run_', False):
        debug = app.config.get('DEBUG') or options.get('debug')
        host = app.config.get('HOST') or options.get('host')
        port = int(app.config.get('PORT') or options.get('port'))
        app.run(host=host, port=port, debug=debug)
    return app


if __name__ == '__main__':
    import sys
    from textwrap import dedent as dd

    # Catch if local system doesn't have docopt installed
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
    options['_run_'] = True
    main(**options)
