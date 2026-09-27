import ast
from pathlib import Path
import torch
from fastglycan.models.differentiable_mini import directional_check, full_recycle_pairformer


def test_upstream_forward_body_preserved_except_gradient_guard():
    source = Path('reports/stage0_confirmation_2026-09-19/runtime_inspection/protenix/model/protenix.py').read_text()
    import inspect
    old = next(n for n in ast.walk(ast.parse(source)) if isinstance(n, ast.FunctionDef) and n.name == 'get_pairformer_output')
    new = ast.parse(inspect.getsource(full_recycle_pairformer)).body[0]
    old.name = new.name
    guards = [n for n in ast.walk(old) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == 'set_grad_enabled']
    assert len(guards) == 1
    guards[0].args = [ast.parse('torch.is_grad_enabled()', mode='eval').body]
    old.body = old.body[1:]  # Ignore docstring indentation after dedenting.
    new.body = new.body[1:]
    assert ast.dump(old, include_attributes=False) == ast.dump(new, include_attributes=False)


def test_directional_check_detects_detached_recurrence():
    x = torch.tensor([.4, -.2], dtype=torch.float64)
    v = torch.tensor([1., 2.], dtype=torch.float64)
    def objective(x, broken=False):
        y = x
        for _ in range(4):
            y = x + .3 * (y.detach() if broken else y)
        return y.square().sum()
    # Avoid a direction orthogonal to the quadratic gradient.
    v = torch.tensor([2., 1.], dtype=torch.float64)
    _, good = directional_check(objective, x, v)
    _, bad = directional_check(lambda x: objective(x, True), x, v)
    assert max(r['relative_error'] for r in good) < 1e-8
    assert min(r['relative_error'] for r in bad) > .1
