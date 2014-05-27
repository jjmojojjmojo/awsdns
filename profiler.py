"""
Profiling Test
"""

from awsdns import main

import cProfile

cProfile.run('main()')
