#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests conversion

Usage:
   test_encoding [options] <filepath>

Options:
   -e --encoding ENCODE    Describes the file format for the filepath
   -d --decoding DECODE    Describes the final file format desired  [default: utf-8]
   -v --verbose            More spam
"""
import os

import docopt
import magic


def main(**opts):
    verbose = opts.get('verbose')
    filepath = os.path.abspath(opts.get('filepath'))
    codec_mapping = {
        'ISO-8859': 'iso-8859-1',
    }
    detected_encoding = magic.from_file(filepath).split(' ')[0]
    codec = codec_mapping.get(detected_encoding, detected_encoding)
    encoding = opts.get('encoding') or codec
    decoding = opts.get('decoding')
    if verbose:
        print('File encoding: {}'.format(encoding))
        print('File output: {}'.format(decoding))
    with open(opts.get('filepath'), 'r') as fd:
        for idx, line in enumerate(fd):
            try:
                print(line.strip().decode(encoding).encode(decoding))
            except Exception:
                print('Error on line: {} of file "{}".'.format(idx, filepath))
                try:
                    print('         line: {}.'.format(line))
                except:
                    print('         line: ***could not display line***')
                print('Entering pdb.')
                import pdb; pdb.set_trace()


if __name__ == '__main__':
    from docopt import docopt

    def fix(k):
        return k.lstrip('-<').rstrip('>').replace('-', '_')

    opts = {fix(k): v for k, v in docopt(__doc__).items()}

    main(**opts)
