"""Summarize every fixed node after independent result verification."""
from pathlib import Path
from fastglycan.fullbatch_results import analyze_fullbatch_results

if __name__ == '__main__':
    result = analyze_fullbatch_results(Path(__file__).resolve().parent)
    print('ANALYZED', len(result['runs']), 'runs; no checkpoint selection')
