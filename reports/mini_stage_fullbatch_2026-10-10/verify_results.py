"""Run only after the closed remote export has been collected here."""
import json
from pathlib import Path
from fastglycan.fullbatch_results import verify_fullbatch_results

if __name__ == '__main__':
    print(json.dumps(verify_fullbatch_results(Path(__file__).resolve().parent)))
