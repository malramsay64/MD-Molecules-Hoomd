#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#
# Copyright © 2017 Malcolm Ramsay <malramsay64@gmail.com>
#
# Distributed under terms of the MIT license.

"""Run simulation with boilerplate taken care of by the statdyn library."""

import argparse
import logging
from pathlib import Path
from subprocess import run
from typing import Callable, List, Tuple

import hoomd.context
from pkg_resources import DistributionNotFound, get_distribution

from ..analysis.run_analysis import comp_dynamics
from ..crystals import CRYSTAL_FUNCS
from ..molecules import Dimer, Disc, Sphere, Trimer
from ..simulation import equilibrate, initialise, simrun
from ..simulation.params import SimulationParams

logger = logging.getLogger(__name__)


try:
    __version__ = get_distribution('statdyn').version
except DistributionNotFound:
    # package is not installed
    __version__ = "dev"


MOLECULE_OPTIONS = {
    'trimer': Trimer,
    'disc': Disc,
    'sphere': Sphere,
    'dimer': Dimer,
}


EQUIL_OPTIONS = {
    'interface': equilibrate.equil_interface,
    'liquid': equilibrate.equil_liquid,
    'crystal': equilibrate.equil_crystal,
}


def sdrun() -> None:
    """Run main function."""
    logging.debug('Running main function')
    func, sim_params = parse_args()
    func(sim_params)


def prod(sim_params: SimulationParams) -> None:
    """Run simulations on equilibrated phase."""
    logger.debug('running prod')
    logger.debug('Reading %s', sim_params.infile)

    snapshot = initialise.init_from_file(sim_params.infile, hoomd_args=sim_params.hoomd_args)
    logger.debug('Snapshot initialised')

    sim_context = hoomd.context.initialize(sim_params.hoomd_args)
    simrun.run_npt(
        snapshot=snapshot,
        context=sim_context,
        sim_params=sim_params,
    )


def equil(sim_params: SimulationParams) -> None:
    """Command group for the equilibration of configurations."""
    logger.debug('Running %s equil', sim_params.equil_type)

    logger.debug('Equil hoomd args: %s', sim_params.hoomd_args)

    # Ensure parent directory exists
    Path(sim_params.outfile).parent.mkdir(exist_ok=True)

    snapshot = initialise.init_from_file(sim_params.infile,
                                         hoomd_args=sim_params.hoomd_args)
    EQUIL_OPTIONS.get(sim_params.equil_type)(
        snapshot,
        sim_params=sim_params,
    )


def create(sim_params: SimulationParams) -> None:
    """Create things."""
    logger.debug('Running create.')
    logger.debug('Interface flag: %s', sim_params.interface)
    # Ensure parent directory exists
    Path(sim_params.outfile).parent.mkdir(exist_ok=True)

    if getattr(sim_params, 'crystal', None):
        snapshot = initialise.init_from_crystal(sim_params)
    else:
        snapshot = initialise.init_from_disperse(sim_params)


    equilibrate.equil_crystal(
        snapshot=snapshot,
        sim_params=sim_params,
    )


def figure(args) -> None:
    """Start bokeh server with the file passed."""
    fig_file = Path(__file__).parents[1] / 'figures/interactive_config.py'
    try:
        run(['bokeh', 'serve', '--show', str(fig_file)] + args.bokeh)
    except ProcessLookupError:
        logger.info('Bokeh server terminated.')


def create_parser() -> argparse.ArgumentParser:
    """Create the argument parser."""
    parser = argparse.ArgumentParser()

    parser.add_argument(
        '-s', '--steps',
        dest='num_steps',
        type=int,
        help='The number of steps for which to run the simulation.',
    )
    parser.add_argument(
        '--output-interval',
        type=int,
        help='Steps between output of dump and thermodynamic quantities.'
    )
    parser.add_argument(
        '--hoomd-args',
        type=str,
        help='Arguments to pass to hoomd on context.initialize',
    )
    parser.add_argument(
        '--pressure',
        type=float,
        help='Pressure for simulation',
    )
    parser.add_argument(
        '-t',
        '--temperature',
        type=float,
        help='Temperature for simulation',
    )
    parser.add_argument(
        '-o',
        '--output',
        dest='outfile_path',
        type=str,
        help='Directory to output files to',
    )

    parse_molecule = parser.add_argument_group('molecule')
    parse_molecule.add_argument(
        '--molecule',
        choices=MOLECULE_OPTIONS.keys(),
    )
    parse_molecule.add_argument(
        '--distance',
        type=float,
        help='Distance at which small particles are situated',
    )
    parse_molecule.add_argument(
        '--radius',
        type=float,
        help='Radius of the small particles',
    )
    parse_molecule.add_argument(
        '--moment-inertia-scale',
        type=float,
        help='Scaling factor for the moment of inertia.',
    )

    parse_crystal = parser.add_argument_group('crystal')
    parse_crystal.add_argument(
        '--space-group',
        choices=list(CRYSTAL_FUNCS.keys()) + ['None'],
        help='Space group of initial crystal.',
    )
    parse_crystal.add_argument(
        '--lattice-lengths',
        dest='cell_dimensions',
        nargs=2,
        type=int,
        help='Number of repetitiions in the a and b lattice vectors',
    )

    parse_steps = parser.add_argument_group('steps')
    parse_steps.add_argument(
        '--gen-steps',
        type=int
    )
    parse_steps.add_argument(
        '--max-gen',
        type=int
    )

    default_parser = argparse.ArgumentParser(add_help=False)
    default_parser.add_argument(
        '-v',
        '--verbose',
        action='count',
        default=0,
        help='Enable debug logging flags.',
    )
    default_parser.add_argument(
        '--version',
        action='version',
        version='sdrun {0}'.format(__version__)
    )


    # TODO write up something useful in the help
    simtype = argparse.ArgumentParser(add_help=False, parents=[default_parser])
    subparsers = simtype.add_subparsers()
    parse_equilibration = subparsers.add_parser('equil', add_help=False, parents=[parser, default_parser])
    parse_equilibration.add_argument(
        '--init-temp',
        type=float,
        help='Temperature to start equilibration from if differnt from the target.'
    )
    parse_equilibration.add_argument(
        '--equil-type',
        default='liquid',
        choices=EQUIL_OPTIONS.keys(),
    )
    parse_equilibration.add_argument('infile', type=str)
    parse_equilibration.add_argument('outfile', type=str)
    parse_equilibration.set_defaults(func=equil)

    parse_production = subparsers.add_parser('prod', add_help=False, parents=[parser, default_parser])
    parse_production.add_argument('--no-dynamics', dest='dynamics', action='store_false')
    parse_production.add_argument('--dynamics', action='store_true')
    parse_production.add_argument('infile', type=str)
    parse_production.set_defaults(func=prod)

    parse_comp_dynamics = subparsers.add_parser('comp_dynamics', add_help=False, parents=[parser, default_parser])
    parse_comp_dynamics.add_argument('infile', type=str)
    parse_comp_dynamics.set_defaults(func=comp_dynamics)

    parse_create = subparsers.add_parser('create', add_help=False, parents=[parser, default_parser])
    parse_create.add_argument('--interface', default=False, action='store_true')
    parse_create.add_argument('outfile', type=str)

    parse_create.set_defaults(func=create)
    parse_figure = subparsers.add_parser('figure', add_help=True, parents=[default_parser])
    parse_figure.add_argument(
        'bokeh',
        nargs='*',
        default=[],
    )
    parse_figure.set_defaults(func=figure)
    return simtype


def _verbosity(level: int=0) -> None:
    root_logger = logging.getLogger('statdyn')
    levels = {
        0: logging.WARNING,
        1: logging.INFO,
        2: logging.DEBUG,
    }
    log_level = levels.get(level, logging.DEBUG)
    logging.basicConfig(level=log_level)
    root_logger.setLevel(log_level)


def parse_args(input_args: List[str]=None
               ) -> Tuple[Callable[[SimulationParams], None], SimulationParams]:
    """Logic to parse the input arguments."""
    parser = create_parser()
    if input_args is None:
        args = parser.parse_args()
    else:
        args = parser.parse_args(input_args)

    # Handle verbosity
    _verbosity(args.verbose)
    del args.verbose

    # Handle subparser function
    try:
        func = args.func
        del args.func
    except AttributeError:
        parser.print_help()
        exit()

    # Parse Molecules
    my_mol = MOLECULE_OPTIONS.get(getattr(args, 'molecule', None))
    if my_mol is None:
        my_mol = Trimer
    mol_kwargs = {}
    for attr in ['distance', 'moment_inertia_scale', 'mol_radius']:
        if getattr(args, attr, None) is not None:
            mol_kwargs[attr] = getattr(args, attr)

    args.molecule = my_mol(**mol_kwargs)

    # Parse space groups
    if func == create:
        print(args.space_group)
        if args.space_group in CRYSTAL_FUNCS:
            args.crystal = CRYSTAL_FUNCS[args.space_group]()
        else:
            args.crystal = None

    set_args = {key: val for key, val in vars(args).items() if val is not None}
    return func, SimulationParams(**set_args)
