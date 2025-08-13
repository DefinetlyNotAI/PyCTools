from pyCTools.hwrng import MaxRNG
from pyCTools.processInspect import ProcessMetrics

import os

if os.name != 'nt':
    raise OSError('This package only supports Windows OS.')

VERSION = "0.2.1-beta"
