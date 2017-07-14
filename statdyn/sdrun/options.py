#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#
# Copyright © 2017 Malcolm Ramsay <malramsay64@gmail.com>
#
# Distributed under terms of the MIT license.

"""Options for sdrun."""

# type: ignore

import logging
from pathlib import Path

import click

from ..crystals import CRYSTAL_FUNCS

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logging.basicConfig(level=logging.INFO)


def _mkdir_ifempty(ctx, param, value):
    if not value or ctx.resilient_parsing:
        return
    chkpath = Path(value)
    logging.debug(f"Directory {value}, {chkpath}")
    chkpath.mkdir(exist_ok=True)
    return chkpath


def _verbosity(ctx, param, count):
    if not count or ctx.resilient_parsing:
        return
    logger.info('Setting log level to DEBUG')
    logging.basicConfig(level=logging.DEBUG)


opt_space_group = click.option(
    '--space-group',
    default='p2',
    type=click.Choice(CRYSTAL_FUNCS.keys()),
    help='Space group of initial crystal.',
)


opt_lattice_lengths = click.option(
    '--lattice-lengths',
    nargs=2,
    default=(30, 40),
    type=click.Tuple([int, int]),
    help='Number of repetitiions in the a and b lattice vectors',
)


opt_configurations = click.option(
    '-c',
    '--configurations',
    default='.',
    type=click.Path(exists=True),
    help='location of configurations directory',
)


opt_output = click.option(
    '-o',
    '--output',
    default='.',
    type=click.Path(file_okay=False, writable=True,),
    callback=_mkdir_ifempty,
    help='Directory to which output files will be written.',
)


opt_verbose = click.option(
    '-v',
    '--verbose',
    count=True,
    expose_value=False,
    callback=_verbosity,
    help='Enable debug logging flags.',
)


opt_dynamics = click.option(
    '--dynamics/--no-dynamics',
    default=True,
    help='''Enable/diable the collection of dynamics quantities.

Enabling the dynamics quantities will collect in addition to the standard dump
file another trajectory in which the configurations are saved on a logarithmic
scale.
'''
)


opt_steps = click.option(  # type: ignore
    '-s',
    '--steps',
    type=click.IntRange(min=0, max=int(1e12)),
    required=True,
    help='Number of steps to run simulation for.'
)


opt_temperature = click.option(  # type: ignore
    '-t',
    '--temperature',
    type=float,
    required=True,
    help='Temperature for simulation',
)


opt_hoomd_args = click.option(
    '--hoomd-args',
    type=str,
    default='',
    help='Arguments to pass to hoomd on context.initialize',
)
