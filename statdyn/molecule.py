#!/bin/env python3
# -*- coding: utf-8 -*-
#
# copyright Malcolm Ramsay
#
"""Module to define a molecule to use for simulation."""

import logging
from typing import Any, Dict, List, Tuple

import hoomd
import hoomd.md
import numpy as np

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class Molecule(object):
    """Molecule class holding information on the molecule for use in hoomd.

    This class contains all the paramters required to initialise the molecule
    in a hoomd simulation. This includes all interaction potentials, the rigid
    body interactions and the moments of inertia.

    The Molecule class is a template class that defines a number of functions
    subclasses can use to set these variables however it generates no sensible
    molecule itself.

    """

    def __init__(self) -> None:
        """Initialise defualt properties."""
        self.moment_inertia: Tuple[float, float, float] = (0., 0., 0.)
        self.potential = hoomd.md.pair.lj
        self.potential_args: Dict[Any, Any] = dict()
        self.particles = ['A']
        self.dimensions = 3

    @property
    def num_particles(self) -> int:
        """Count of particles in the molecule."""
        return len(self.particles)

    def get_types(self) -> List[str]:
        """Get the types of particles present in a molecule."""
        return sorted(list(set(self.particles)))

    def define_dimensions(self) -> None:
        """Set the number of dimensions for the simulation.

        This takes into accout the number of dimensions of the molecule,
        a 2D molecule can only be a 2D molecule, since there will be no
        rotations in that 3rd dimension anyway.
        """
        if self.dimensions == 2:
            hoomd.md.update.enforce2d()

    def define_potential(self) -> hoomd.md.pair.pair:
        r"""Define the potential in the simulation context.

        A helper function that defines the potential to be used by the  hoomd
        simulation context. The default values for the potential are a
        Lennard-Jones potential with a cutoff of :math:`2.5\sigma` and
        interaction parameters of :math:`\epsilon = 1.0` and
        :math:`\sigma = 2.0`.

        Returns:
            class:`hoomd.md.pair`: The interaction potential object class.

        """
        self.potential_args.setdefault('r_cut', 2.5)
        potential = self.potential(
            **self.potential_args,
            nlist=hoomd.md.nlist.cell()
        )
        potential.pair_coeff.set('A', 'A', epsilon=1, sigma=2.0)
        return potential

    def define_rigid(self, params: Dict[Any, Any]=None
                     ) -> hoomd.md.constrain.rigid:
        """Define the rigid constraints of the molecule.

        This is a helper function to define the rigid body constraints of the
        particular molecules within the hoomd context.

        Args:
            create (bool): Flag that toggles the option of creating the
                additional particles when creating the rigid bodies. Defaults
                to False.
            params (dict): Dictionary defining the rigid body structure. The
                default values for the `type_name` of A and the `types` of the
                `self.particles` variable should work for the vast majority of
                systems, so the only value required should be the topology.

        Returns:
            class:`hoomd.md.constrain.rigid`: Rigid constraint object

        """
        if len(self.particles) <= 1:
            logger.info("Not enough particles for a rigid body")
            return
        if not params:
            params = dict()
        params['type_name'] = self.particles[0]
        params['types'] = self.particles[1:]
        rigid = hoomd.md.constrain.rigid()
        rigid.set_param(**params)
        return rigid


class Disc(Molecule):
    """Defines a 2D particle."""

    def __init__(self) -> None:
        """Initialise 2D disc particle."""
        super().__init__()
        self.dimensions = 2


class Sphere(Molecule):
    """Define a 3D sphere."""

    def __init__(self) -> None:
        """Initialise Spherical particle."""
        super().__init__()


class Trimer(Molecule):
    """Defines a Trimer molecule for initialisation within a hoomd context.

    This defines a molecule of three particles, shaped somewhat like Mickey
    Mouse. The central particle is of type `'A'` while the outer two
    particles are of type `'B'`. The type `'B'` particles, have a variable
    radius and are positioned at a specified distance from the central
    type `'A'` particle. The angle between the two type `'B'` particles,
    subtended by the type `'A'` particle is the other degree of freedom.


    TODO:
        Compute the moment of inertia
    """

    def __init__(self,
                 radius: float=0.637556,
                 distance: float=1.0,
                 angle: float=120) -> None:
        """Initialise trimer molecule.

        Args:
            radius (float): Radius of the small particles. Default is 0.637556
            distance (float): Distance of the outer particles from the central
                one. Default is 1.0
            angle (float): Angle between the two outer particles in degrees.
                Default is 120

        """
        super(Trimer, self).__init__()
        self.radius = radius
        self.distance = distance
        self.angle = angle
        self.particles = ['A', 'B', 'B']
        self.moment_inertia = (0., 0., 1.65)
        self.dimensions = 2

    def define_potential(self) -> hoomd.md.pair.pair:
        r"""Define the potential in the simulation context.

        A helper function that defines the potential to be used by the  hoomd
        simulation context. The default values for the potential are a
        Lennard-Jones potential with a cutoff of 2.5 and interaction parameters
        of :math:`\epsilon = 1.0` and :math:`\sigma = 2.0`.

        Returns:
            class:`hoomd.md.pair`: The interaction potential object class.

        """
        potential = super(Trimer, self).define_potential()
        potential.pair_coeff.set('B', 'B', epsilon=1, sigma=self.radius * 2)
        potential.pair_coeff.set('A', 'B', epsilon=1, sigma=1.0 + self.radius)
        return potential

    def define_rigid(self, params: Dict[Any, Any]=None
                     ) -> hoomd.md.constrain.rigid:
        """Define the rigid constraints of the Trimer molecule.

        This is a helper function to define the rigid body constraints of the
        particular molecules within the hoomd context.

        Args:
            params (dict): Dictionary defining the rigid body structure. The
                default values for the `type_name` of A and the `types` of the
                `self.particles` variable should work for the vast majority of
                systems, so the only value required should be the topology.

        Returns:
            class:`hoomd.md.constrain.rigid`: Rigid constraint object

        """
        angle = (self.angle / 2) * np.pi / 180.
        if not params:
            params = dict()
        params.setdefault('positions', [
            (np.sin(angle), np.cos(angle), 0),
            (-np.sin(angle), np.cos(angle), 0)
        ])
        rigid = super(Trimer, self).define_rigid(params)
        return rigid


class Dimer(Molecule):
    """Defines a Trimer molecule for initialisation within a hoomd context.

    This defines a molecule of three particles, shaped somewhat like Mickey
    Mouse. The central particle is of type `'A'` while the outer two
    particles are of type `'B'`. The type `'B'` particles, have a variable
    radius and are positioned at a specified distance from the central
    type `'A'` particle. The angle between the two type `'B'` particles,
    subtended by the type `'A'` particle is the other degree of freedom.

    """

    def __init__(self, radius: float=0.637556, distance: float=1.0) -> None:
        """Intialise Dimer molecule.

        Args:
            radius (float): Radius of the small particles. Default is 0.637556
            distance (float): Distance of the outer particles from the central
                one. Default is 1.0
            angle (float): Angle between the two outer particles in degrees.
                Default is 120

        """
        super(Dimer, self).__init__()
        self.radius = radius
        self.distance = distance
        self.particles = ['A', 'B']
        self.moment_inertia = self.compute_moment_intertia()
        self.dimensions = 2

    def compute_moment_intertia(self) -> Tuple[float, float, float]:
        """Compute the moment of inertia from the particle paramters."""
        return (0., 0., 2 * (self.distance / 2)**2)

    def define_potential(self) -> hoomd.md.pair.pair:
        r"""Define the potential in the simulation context.

        A helper function that defines the potential to be used by the  hoomd
        simulation context. The default values for the potential are a
        Lennard-Jones potential with a cutoff of 2.5 and interaction parameters
        of :math:`\epsilon = 1.0` and :math:`\sigma = 2.0`.

        Returns:
            class:`hoomd.md.pair`: The interaction potential object class.

        """
        potential = super(Dimer, self).define_potential()
        potential.pair_coeff.set('B', 'B', epsilon=1, sigma=self.radius * 2)
        potential.pair_coeff.set('A', 'B', epsilon=1, sigma=1.0 + self.radius)
        return potential

    def define_rigid(self, params: Dict[Any, Any]=None
                     ) -> hoomd.md.constrain.rigid:
        """Define the rigid constraints of the molecule.

        This is a helper function to define the rigid body constraints of the
        particular molecules within the hoomd context.

        Args:
            params (dict): Dictionary defining the rigid body structure. The
                default values for the `type_name` of A and the `types` of the
                `self.particles` variable should work for the vast majority of
                systems, so the only value required should be the topology.

        Returns:
            class:`hoomd.md.constrain.rigid`: Rigid constraint object

        """
        if not params:
            params = dict()
        params.setdefault('positions', [(self.distance, 0, 0)])
        rigid = super(Dimer, self).define_rigid(params)
        return rigid
