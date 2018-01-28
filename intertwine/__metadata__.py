# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

__all__ = (
    '__project__', '__description__', '__versionstr__', '__author__',
    '__author_email__', '__maintainer__', '__maintainer_email__',
    '__copyright_years__', '__license__', '__url__', '__version__',
    '__classifiers__', '__keywords__', 'package_metadata',
)

# ----------------------------------------------------------------------
# Package Metadata
# ----------------------------------------------------------------------
__project__ = 'intertwine'
__description__ = "Untangle the world's problems"
__versionstr__ = '0.3.0-dev'

__author__ = 'Intertwine'
__author_email__ = 'engineering@intertwine.io'

__maintainer__ = 'Intertwine'
__maintainer_email__ = 'engineering@intertwine.io'

__copyright_years__ = '2015-2018'
__license__ = 'Copyright Intertwine'
__url__ = 'https://github.com/IntertwineIO/platform.git'
__version__ = tuple([
    int(ver_i.split('-')[0])
    for ver_i in __versionstr__.split('.')
])

__classifiers__ = [
    'Programming Language :: Python',
    'Natural Language :: English',
    'Development Status :: 3 - Alpha',
    'Environment :: Console',
    'Environment :: No Input/Output',
    'Environment :: Other Environment',
    'Intended Audience :: Developers',
    'License :: Other/Proprietary License',
    'Natural Language :: English',
    'Operating System :: POSIX',
    'Programming Language :: Python :: 2.7',
    'Programming Language :: Python :: 3.5',
    'Programming Language :: Python :: 3.6',
    'Programming Language :: Python :: Implementation :: CPython',
    'Programming Language :: Python :: Implementation :: PyPy',
    'Topic :: Software Development',
]

__keywords__ = [
    'utilities', 'tools',
]

# Package everything above into something nice and convenient for extracting
package_metadata = {
    k.strip('_'): v for k, v in locals().items() if k.startswith('__')
}
