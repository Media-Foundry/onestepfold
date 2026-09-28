"""Separate development utility from the unchanged full hard acceptance gate."""
from .hybrid_geometry import hard_accept


def utility_decision(task, parent_task, geometry, parent_geometry):
    full = hard_accept(task, parent_task, geometry, parent_geometry)
    blocking = [reason for reason in full['reasons']
                if reason in ('nonfinite', 'no_task_improvement') or reason.endswith('_regression')]
    return dict(task_delta=task-parent_task,
                task_improved=task < parent_task-1e-4,
                task_and_nonregression=not blocking,
                utility_reasons=blocking, full=full)
