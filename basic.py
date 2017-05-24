"""Run a basic simulation"""

import os

import tempfile
import hoomd
from hoomd import md
import molecule
import numpy as np
import pandas
import TimeDep
import gsd.hoomd
from StepSize import generate_steps


def run_npt(snapshot, temp, steps, **kwargs):
    """Initialise a hoomd simulation"""
    with hoomd.context.initialize(kwargs.get('init_args', '')):
        system = hoomd.init.read_gsd(snapshot, time_step=0)
        md.update.enforce2d()
        mol = kwargs.get('mol', molecule.Trimer())
        mol.initialize(create=False)
        md.integrate.mode_standard(kwargs.get('dt', 0.005))
        md.integrate.npt(
            group=hoomd.group.rigid_center(),
            kT=temp,
            tau=kwargs.get('tau', 1.),
            P=kwargs.get('press', 13.5),
            tauP=kwargs.get('tauP', 1.)
        )
        dynamics = TimeDep.TimeDep2dRigid(system.take_snapshot(all=True), 0)
        for curr_step in generate_steps(steps):
            hoomd.run_upto(curr_step)
            dynamics.append(system.take_snapshot(all=True), curr_step)
        return dynamics.get_all_data()


def read_snapshot(fname, rand=False):
    """Read a hoomd snapshot from a hoomd gsd file

    Args:
        fname (string): Filename of GSD file to read in

    Returns:
        class:`hoomd.data.Snapshot`: Hoomd snapshot
    """
    with gsd.hoomd.open(fname) as trj:
        snapshot = trj.read_frame(0)
        if rand:
            nbodies = snapshot.particles.body.max() + 1
            np.random.shuffle(snapshot.particles.velocity[:nbodies])
            np.random.shuffle(snapshot.particles.angmom[:nbodies])
        tmp = tempfile.NamedTemporaryFile(delete=False)
        with gsd.hoomd.open(tmp.name, 'wb') as tfile:
            tfile.append(snapshot)
        return tmp.name


def main(directory, temp, steps, iterations=2):
    """Main function to run stuff"""
    init_file = directory + "/Trimer-{press:.2f}-{temp:.2f}.gsd".format(
        press=13.50, temp=temp)
    for iteration in range(iterations):
        dynamics = run_npt(read_snapshot(init_file, rand=True), temp, steps)
        with pandas.HDFStore(os.path.splitext(init_file)[0]+'.hdf5') as store:
            store['dyn{i}'.format(i=iteration)] = dynamics

if __name__ == '__main__':
    main(".", 1.30, 1000, 20)
