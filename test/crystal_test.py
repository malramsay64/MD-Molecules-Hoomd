#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#
# Copyright © 2017 Malcolm Ramsay <malramsay64@gmail.com>
#
# Distributed under terms of the MIT license.

"""Testing the crystal class of statdyn."""

from pathlib import Path

import hoomd
import numpy as np
import pytest
from hypothesis import given, settings
from hypothesis.extra.numpy import arrays
from hypothesis.strategies import floats, integers, tuples

from statdyn import crystals
from statdyn.simulation import initialise
from statdyn.simulation.helper import SimulationParams

TEST_CLASSES = [
    crystals.Crystal,
    crystals.CrysTrimer,
    crystals.TrimerP2,
    crystals.TrimerP2gg,
    crystals.TrimerPg,
    crystals.SquareCircle,
    crystals.CubicSphere,
]

output_dir = Path('test/output')
output_dir.mkdir(exist_ok=True)

PARAMETERS = SimulationParams(
    temperature=0.4,
    num_steps=100,
    outfile_path=output_dir,
    crystal=crystals.TrimerP2(),
    cell_dimensions=(32, 40),
)


@pytest.mark.parametrize("crys_class", TEST_CLASSES)
def test_init(crys_class):
    """Check the class will initialise."""
    crys_class()


@pytest.mark.parametrize("crys_class", TEST_CLASSES)
def test_get_orientations(crys_class):
    """Test the orientation is returned as a float."""
    crys = crys_class()
    orient = crys.get_orientations()
    assert orient.dtype == np.float32


@pytest.mark.parametrize("crys_class", TEST_CLASSES)
def test_get_unitcell(crys_class):
    """Test the return type is correct."""
    crys = crys_class()
    assert isinstance(crys.get_unitcell(), hoomd.lattice.unitcell)


@pytest.mark.parametrize("crys_class", TEST_CLASSES)
def test_compute_volume(crys_class):
    """Test the return type of the volume computation."""
    crys = crys_class()
    assert isinstance(crys.compute_volume(), float)


@pytest.mark.parametrize("crys_class", TEST_CLASSES)
def test_abs_positions(crys_class):
    """Check the absolute positions function return corectly shaped matrix."""
    crys = crys_class()
    assert crys.get_abs_positions().shape == np.array(crys.positions).shape


def get_distance(pos_a, pos_b, box):
    """Compute the periodic distance between two numpy arrays."""
    ortho_box = np.array((box.Lx, box.Ly, box.Lz))
    delta_x = pos_b - pos_a
    delta_x -= ortho_box * (delta_x > ortho_box * 0.5)
    delta_x += ortho_box * (delta_x <= -ortho_box * 0.5)
    return np.sqrt(np.square(delta_x).sum(axis=1))


class mybox(object):
    """Simple box class."""

    def __init__(self):
        """init."""
        self.Lx = 1.
        self.Ly = 1.
        self.Lz = 1.


@given(arrays(np.float, 3, elements=floats(min_value=-1, max_value=1)),
       arrays(np.float, 3, elements=floats(min_value=-1, max_value=1)))
def test_get_distance(pos_a, pos_b):
    """Test the periodic distance function."""
    box = mybox()
    diff = get_distance(np.array([pos_a]), np.array([pos_b]), box)
    print(diff, diff-np.sqrt(2))
    assert get_distance(np.array([pos_a]), np.array([pos_b]), box) <= np.sqrt(3)


@given(tuples(integers(max_value=30, min_value=1),
              integers(max_value=30, min_value=1)))
@settings(max_examples=3, deadline=None)
def test_cell_dimensions(cell_dimensions):
    """Test cell paramters work properly."""
    snap = initialise.init_from_crystal(PARAMETERS)
    for i in snap.particles.position:
        distances = get_distance(i, snap.particles.position, snap.box) < 1.1
        assert np.sum(distances) <= 3
