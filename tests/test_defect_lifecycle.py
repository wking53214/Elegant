"""Defect lifecycle: the transition table refuses moves it does not allow.

The allowed moves are exactly the ones Transformation.authorize and
Transformation.apply perform. Everything else is refused, and a refused move
leaves the defect where it was.
"""
from types import SimpleNamespace

import pytest

from warden.models import (
    VALID_DEFECT_TRANSITIONS,
    DefectLifecycle,
    InvalidDefectTransition,
    _move_defect,
)


def _defect(state):
    return SimpleNamespace(lifecycle=state)


@pytest.mark.parametrize(
    "start, target",
    [
        (DefectLifecycle.PROPOSED, DefectLifecycle.AUTHORIZED),
        (DefectLifecycle.PROPOSED, DefectLifecycle.MODIFIED),
        (DefectLifecycle.AUTHORIZED, DefectLifecycle.MODIFIED),
    ],
)
def test_allowed_moves_go_through(start, target):
    defect = _defect(start)

    _move_defect(defect, target)

    assert defect.lifecycle is target


@pytest.mark.parametrize(
    "start, target",
    [
        (DefectLifecycle.IDENTIFIED, DefectLifecycle.FIXED),
        (DefectLifecycle.AUTHORIZED, DefectLifecycle.PROPOSED),
        (DefectLifecycle.MODIFIED, DefectLifecycle.AUTHORIZED),
        (DefectLifecycle.FIXED, DefectLifecycle.IDENTIFIED),
        (DefectLifecycle.REJECTED, DefectLifecycle.AUTHORIZED),
    ],
)
def test_refused_moves_leave_the_defect_unchanged(start, target):
    defect = _defect(start)

    with pytest.raises(InvalidDefectTransition):
        _move_defect(defect, target)

    assert defect.lifecycle is start


def test_refusal_is_a_value_error():
    assert issubclass(InvalidDefectTransition, ValueError)


def test_table_only_names_real_lifecycle_states():
    for source, targets in VALID_DEFECT_TRANSITIONS.items():
        assert isinstance(source, DefectLifecycle)
        assert all(isinstance(target, DefectLifecycle) for target in targets)
