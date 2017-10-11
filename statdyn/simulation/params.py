#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#
# Copyright © 2017 Malcolm Ramsay <malramsay64@gmail.com>
#
# Distributed under terms of the MIT license.

"""Parameters for passing between functions."""

import logging
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, Tuple, Union

import hoomd

from ..crystals import Crystal
from ..molecules import Molecule, Trimer

logger = logging.getLogger(__name__)


class SimulationParams(object):
    """Store the parameters of the simulation."""

    defaults = {
        'hoomd_args': '',
        'step_size': 0.005,
        'temperature': 0.4,
        'tau': 1.0,
        'pressure': 13.5,
        'tauP': 1.0,
        'cell_dimensions': (30, 42),
        'outfile_path': Path.cwd(),
        'max_gen': 500,
        'gen_steps': 20000,
        'output_interval': 10000,
    }  # type: Dict[str, Any]

    def __init__(self, **kwargs) -> None:
        """Create SimulationParams instance."""
        self.parameters = deepcopy(self.defaults)  # type: Dict[str, Any]
        self.parameters.update(kwargs)

    # I am using getattr over getattribute becuase of the lower search priority
    # of getattr. This makes it a fallback, rather than the primary location
    # for looking up attributes.
    def __getattr__(self, key):
        try:
            return self.parameters.__getitem__(key)
        except KeyError:
            raise AttributeError

    def __setattr__(self, key, value):
        # setattr has a higher search priority than other functions, custom
        # setters need to be added to the list below
        if key in ['parameters']:
            super().__setattr__(key, value)
        else:
            self.parameters.__setitem__(key, value)

    def __delattr__(self, attr):
        return self.parameters.__delitem__(attr)

    @property
    def temperature(self) -> Union[float, hoomd.variant.linear_interp]:
        """Temperature of the system."""
        try:
            return hoomd.variant.linear_interp([
                (0, self.init_temp),
                (int(self.num_steps*0.75), self.parameters.get('temperature', self.init_temp)),
                (self.num_steps, self.parameters.get('temperature', self.init_temp)),
            ], zero='now')
        except AttributeError:
            return self.parameters.get('temperature')

    @temperature.setter
    def temperature(self, value: float) -> None:
        self.parameters['temperature'] = value

    @property
    def molecule(self) -> Molecule:
        """Return the appropriate molecule.

        Where there is no custom molecule defined then we return the molecule of
        the crystal.

        """
        if self.parameters.get('molecule') is not None:
            mol = self.parameters.get('molecule')
        elif self.parameters.get('crystal') is not None:
            mol = self.crystal.molecule
        else:
            mol = Trimer()

        return mol

    @property
    def cell_dimensions(self) -> Tuple[int, int]:
        try:
            self.crystal
            return self.parameters.get('cell_dimensions')
        except AttributeError:
            raise AttributeError

    @property
    def group(self) -> hoomd.group.group:
        """Return the appropriate group."""
        if self.parameters.get('group'):
            return self.parameters.get('group')
        if self.molecule.num_particles == 1:
            return hoomd.group.all()
        return hoomd.group.rigid_center()

    @property
    def outfile_path(self) -> Path:
        """Ensure the output directory is a path."""
        if self.parameters.get('outfile_path'):
            return Path(self.parameters.get('outfile_path'))
        return Path.cwd()

    @property
    def outfile(self) -> str:
        """Ensure the output file is a string."""
        if self.parameters.get('outfile') is not None:
            return str(self.parameters.get('outfile'))
        raise AttributeError('Outfile does not exist')

    def filename(self, prefix: str=None) -> str:
        """Use the simulation parameters to construct a filename."""
        base_string = '{molecule}-P{pressure:.2f}-T{temperature:.2f}'
        if prefix:
            base_string = '{prefix}-' + base_string
        if self.parameters.get('moment_inertia_scale') is not None:
            base_string += '-I{mom_inertia:.2f}'

        fname = base_string.format(
            prefix=prefix,
            molecule=self.molecule,
            pressure=self.pressure,
            temperature=self.parameters.get('temperature'),
            mom_inertia=self.parameters.get('moment_inertia_scale'),
        )
        return str(self.outfile_path / fname)
