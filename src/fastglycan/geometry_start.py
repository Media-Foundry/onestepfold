"""Load a pose start without redefining the original raw-coordinate chart."""
import torch

from .anchored_geometry import PoseVariables


def pose_variables_at_start(adapter, raw, start_values=None):
    """Always build the frozen chart from raw; optionally copy detached parameters.

    The caller must likewise build its objective and regularization reference from
    the original raw prediction. A fitted coordinate array is not a replacement
    for raw here. This helper does not differentiate through either optimizer.
    """
    variables = PoseVariables(adapter, raw)
    if start_values is None:
        return variables
    values = tuple(start_values)
    parameters = tuple(variables.variables)
    if len(values) != len(parameters):
        raise ValueError('pose parameter group count mismatch')
    for value, parameter in zip(values, parameters, strict=True):
        if value.shape != parameter.shape or value.dtype != parameter.dtype:
            raise ValueError('pose parameter shape or dtype mismatch')
        if not torch.isfinite(value).all():
            raise ValueError('nonfinite pose start')
    with torch.no_grad():
        for value, parameter in zip(values, parameters, strict=True):
            parameter.copy_(value.detach().to(parameter.device))
    return variables
