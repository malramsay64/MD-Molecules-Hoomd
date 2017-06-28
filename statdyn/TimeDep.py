#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#
# Copyright © 2017 Malcolm Ramsay <malramsay64@gmail.com>
#
# Distributed under terms of the MIT license.

"""Used for computing the dynamic properties of a Hoomd MD simulation."""

from pathlib import Path
from typing import Any, Dict, List  # pylint: disable=unused-import

import hoomd
import numpy as np
import pandas
import quaternion


class TimeDep(object):
    """Compute time dependent characteristics of individual particles."""

    def __init__(self,
                 snapshot: hoomd.data.SnapshotParticleData,
                 timestep: int) -> None:
        """Initialise TimeDep instance.

        Args:
            snapshot (:class:`hoomd.data.SnapshotParticleData`): Hoomd snapshot
                object which is the initial configuration for the purposes of
                the dynamics calculations
            timestep (int): Timestep at which the inital configuration starts.
        """
        self.t_init = snapshot
        self.timestep = timestep
        self._init_snapshot(snapshot)
        self._data = self.get_data(snapshot, timestep)

    def _init_snapshot(self,
                       snapshot: hoomd.data.SnapshotParticleData) -> None:
        """Set the initial snapshot.

        Args:
            snapshot: (class:`hoomd.data.SnapshotParticleData`): The initial
                snapshot
        """
        self.pos_init = snapshot.particles.position
        self.image_init = snapshot.particles.image

    def get_time_diff(self, timestep: int) -> int:
        """Compute the time difference between timesteps.

        The difference in time between the currrent timestep and the
        timestep of the initial configuration.

        Args:
            timestep (int): The timestep at which to compute the difference.

        Returns:
            int: Difference between initial and current timestep

        """
        return timestep - self.timestep

    def _unwrap(self,
                snapshot: hoomd.data.SnapshotParticleData) -> np.array:
        """Unwraps periodic positions to absolute positions.

        Converts the periodic potition of each particle to it's *real* position
        by taking into account the *image* the particle exitsts on.

        Args:
            snapshot (snapshot): Hoomd snapshot of the system to unwrap

        Returns:
            :class:`numpy.array`: A numpy array of position arrays contianing
            the unwrapped positions

        """
        try:
            box_dim = np.array([
                snapshot.box.Lx,
                snapshot.box.Ly,
                snapshot.box.Lz
            ])
        except AttributeError:
            box_dim = np.array([
                snapshot.configuration.box[0],
                snapshot.configuration.box[1],
                snapshot.configuration.box[2]
            ])

        pos = snapshot.particles.position
        image = snapshot.particles.image - self.image_init
        return pos + image * box_dim

    def _displacement(self,
                      snapshot: hoomd.data.SnapshotParticleData) -> np.array:
        """Calculate the squared displacement for all bodies in the system.

        This is the function that computes the per body displacements for all
        the dynamic quantities. This is where the most computation takes place
        and can be called once for a number of further calculations.

        Args:
            snapshot (snapshot): The configuration at which the difference is
                computed

        Returns:
            :class:`numpy.array`: An array containing per body displacements

        """
        curr = self._unwrap(snapshot)
        return np.sqrt(np.power(curr - self.pos_init, 2).sum(1))

    def get_data(self,
                 snapshot: hoomd.data.SnapshotParticleData,
                 timestep: int) -> pandas.DataFrame:
        """Get translational and rotational data.

        Args:
            system (:class:`hoomd.data.SnapshotParticleData`): Hoomd system
                object in the configuration to be saved

        Returns:
            :class:`TransData`: Data object

        """
        data = pandas.DataFrame({
            'displacement': self._displacement(snapshot),
            'time': self.get_time_diff(timestep)
        })
        data.time_diff = self.get_time_diff(timestep)
        return data

    def get_all_data(self) -> pandas.DataFrame:
        """Return all the data.

        Returns:
            class:`pandas.DataFrame`: All the data

        """
        return self._data


class TimeDep2dRigid(TimeDep):
    """Compute the time dependent characteristics of 2D rigid bodies.

    This class extends on from :class:`TimeDep` computing rotational properties
    of the 2D rigid bodies in the system. The distinction of two dimensional
    molecules makes for a simpler analysis of the rotational characteristics.

    Note:
        This class computes positional properties for each rigid body in the
        system. This means that for computations of rigid bodies it would be
        expected to get different translational quantities using the
        :class:`TimeDep` and the :class:`TimeDep2dRigid` classes.

    """

    def __init__(self, snapshot, timestep):
        """Initialise TimeDep2dRigid class.

        Args:
            snapshot (:class:`hoomd.data.SnapshotParticleData`): Hoomd snapshot
                object at the initial time for the dyanamics computations

        """
        super(TimeDep2dRigid, self).__init__(snapshot, timestep)

    def _init_snapshot(self, snapshot):
        super()._init_snapshot(snapshot)
        self.bodies = np.max(self.t_init.particles.body) + 1
        self.orient_init = self.array2quat(
            self.t_init.particles.orientation[:self.bodies])

    @staticmethod
    def array2quat(array):
        """Convert a numpy array to an array of quaternions."""
        return quaternion.as_quat_array(array.astype(float))

    def _rotations(self, snapshot):
        r"""Calculate the rotation for every rigid body in the system.

        This calculates the angle rotated between the initial configuration and
        the current configuration. It doesn't take into accout multiple
        rotations with values falling in the range :math:`[\-pi,\pi)`.

        Args:
            snapshot (:class:`hoomd.data.SnapshotParticleData`): The final
                configuration

        Return:
            :class:`numpy.array`: Array of all the rotations
        """
        orient_final = self.array2quat(
            snapshot.particles.orientation[:self.bodies])
        rot_q = orient_final / self.orient_init
        rot = quaternion.as_rotation_vector(rot_q).sum(axis=1)
        rot[rot > np.pi] -= 2 * np.pi
        rot[rot <= -np.pi] += 2 * np.pi
        return rot

    def _displacement(self, snapshot):
        """Calculate the squared displacement for all bodies in the system.

        This is the function that computes the per body displacements for all
        the dynamic quantities. This is where the most computation takes place
        and can be called once for a number of further calculations.

        Args:
            snapshot (:class:'hoomd.data.SnapshotParticleData'): The
                configuration at which the difference is computed

        Returns:
            :class:`numpy.array`: An array containing per body displacements

        """
        curr = self._unwrap(snapshot)[:self.bodies]
        return np.sqrt(np.power(curr - self.pos_init[:self.bodies], 2).sum(1))

    def _all_displacement(self, snapshot):
        """Calculate the squared displacement for all bodies in the system.

        This is the function that computes the per body displacements for all
        the dynamic quantities. This is where the most computation takes place
        and can be called once for a number of further calculations.

        Args:
            snapshot (:class:'hoomd.data.SnapshotParticleData'): The
                configuration at which the difference is computed

        Returns:
            :class:`numpy.array`: An array containing per body displacements

        """
        curr = self._unwrap(snapshot)
        return np.sqrt(np.power(curr - self.pos_init, 2).sum(1))

    def append(self, snapshot, timestep):
        """Append measurement to data."""
        self._data = self._data.append(self.get_data(snapshot, timestep))

    def get_data(self,
                 snapshot: hoomd.data.SnapshotParticleData,
                 timestep: int) -> pandas.DataFrame:
        """Get translational and rotational data.

        Args:
            snapshot (:class:`hoomd.data.SnapshotParticleData`): Hoomd data
                object

        Returns:
            class:`pandas.DataFrame`: The displacements, rotations and time
                difference as a pandas dataframe.

        """
        data = pandas.DataFrame({
            'displacement': self._displacement(snapshot),
            'rotation': self._rotations(snapshot),
            'time': self.get_time_diff(timestep),
        })
        data.bodies = self.bodies
        return data

    def get_all_data(self) -> List[pandas.DataFrame]:
        """Get all the data."""
        return self._data


class TimeDepMany(object):
    """Class to hold many TimeDep instances.

    The data at each analysis step is saved to an HDF5 file so that large
    datasets can be analysed without having to deal with memory issues.
    """

    def __init__(self, filename: Path=None) -> None:
        """Initialise TimeDepMany class."""
        if filename:
            self._path = filename.with_suffix('.hdf5')
        else:
            self._path = Path('TimeDepMany.hdf5')
        self._snapshots = {}  # type: Dict[int, Any]
        self._check_files()

    def _check_files(self) -> None:
        if self._path.exists():
            self._path.rename(self._path.with_suffix('.hdf5.bak'))

    def add_init(self, snapshot: hoomd.data.SnapshotParticleData,
                 index: int, timestep: int) -> None:
        """Add an initial snapshot at index."""
        self._snapshots[index] = TimeDep2dRigid(snapshot, timestep)
        self.append(snapshot, index, timestep)

    def append(self,
               snapshot: hoomd.data.SnapshotParticleData,
               index: int,
               timestep: int) -> None:
        """Add a measurement to dataset.

        Args:
            snapshot (class`hoomd.data.SnapshotParticleData`): Hoomd snapshot
            index (int): The index of the starting position
            timestep (int): Current timestep
        """
        try:
            data = self._snapshots[index].get_data(snapshot, timestep)
            data['start_index'] = index
            self._write_file(data)
        except (IndexError, KeyError):
            self.add_init(snapshot, index, timestep)

    def _write_file(self, data: pandas.DataFrame) -> None:
        """Write data to hdf5 file."""
        with pandas.HDFStore(str(self._path)) as dst:
            dst.append('dynamics', data,
                       format='table', data_columns=['time', 'start_index'])

    def get_datafile(self) -> Path:
        """Return all the data."""
        return self._path
