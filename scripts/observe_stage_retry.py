"""Run the unmodified locked training script with diagnostic Python stack logs."""
import faulthandler
import os
from pathlib import Path
import runpy
import signal
import sys

original=Path(os.environ['FASTGLYCAN_LOCKED_STAGE_SCRIPT'])
with Path(os.environ['FASTGLYCAN_RUNTIME_STACK_LOG']).open('x') as log:
    faulthandler.enable(file=log,all_threads=True)
    faulthandler.register(signal.SIGUSR1,file=log,all_threads=True,chain=False)
    faulthandler.dump_traceback_later(180,repeat=True,file=log)
    print('STACK_HANDLER_READY',os.getpid(),flush=True)
    sys.argv[0]=str(original)
    try:
        runpy.run_path(str(original),run_name='__main__')
    finally:
        faulthandler.cancel_dump_traceback_later()
