""" """

from cogue.crystal.cell import Cell
from cogue.crystal.symmetry import get_symmetry_dataset
from cogue.controller.autocalc import AutoCalc

def cell(lattice=None,
          points=None,
          symbols=None,
          masses=None,
          numbers=None):
    """ """
    return Cell(lattice,
                points,
                symbols,
                masses,
                numbers)

def symmetry(cell, tolerance=1e-5):
    """ """
    return get_symmetry_dataset(cell, tolerance)

def autocalc(name=None, verbose=False):
    """ """
    return AutoCalc(name=name, verbose=verbose)

