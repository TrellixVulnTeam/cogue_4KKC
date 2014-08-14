import sys
import os
import numpy as np
from cogue.crystal.converter import frac2val, reduce_points
from cogue.crystal.supercell import get_supercell

r2h_observe_R3 = [[-1, 1, 1],
                  [ 0,-1, 1],
                  [ 1, 0, 1]]

h2r_observe_R3 = [[-1./3,-1./3, 2./3],
                  [ 1./3,-2./3, 1./3],
                  [ 1./3, 1./3, 1./3]]

r2h_reverse_R3 = [[ 1,-1, 1],
                  [ 0, 1, 1],
                  [-1, 0, 1]]

h2r_reverse_R3 = [[ 1./3, 1./3,-2./3],
                  [-1./3, 2./3,-1./3],
                  [ 1./3, 1./3, 1./3]]

r2h = r2h_observe_R3

def get_options(parser=None):
    if parser:
        (options, args) = parser.parse_args()
    else:
        (options, args) = get_parser().parse_args()

    return options, args

def get_parser():
    from optparse import OptionParser

    parser = OptionParser()
    parser.set_defaults(is_r2h=False,
                        is_bravais=False,
                        is_verbose=False,
                        output_filename=None,
                        s_mat=None,
                        t_mat=None,
                        shift=None)
    parser.add_option("--r2h",
                      dest="is_r2h",
                      action="store_true",
                      help="Transform primitive Rhombohedral to hexagonal Rhombohedral. This has to be used exclusively to the other options.")
    parser.add_option("--bravais",
                      dest="is_bravais",
                      action="store_true",
                      help="Transform to cell with Bravais lattice.")
    parser.add_option("--tmat",
                      dest="t_mat",
                      action="store",
                      type="string",                      
                      help="Multiply transformation matrix. Absolute value of determinant has to be 1 or less than 1.")
    parser.add_option("--dim",
                      dest="s_mat",
                      action="store",
                      type="string",                      
                      help="Supercell matrix")
    parser.add_option("--shift",
                      dest="shift",
                      action="store",
                      type="string",                      
                      help="Origin shift")
    parser.add_option("-o",
                      dest="output_filename",
                      action="store",
                      type="string",                      
                      help="Output filename")
    parser.add_option("-v",
                      dest="is_verbose",
                      action="store_true",
                      help="More information is output.")
    return parser

def get_lines(filenames):
    import fileinput
    file_obj = fileinput.input(filenames)
    lines = []
    filelines = []
    for line in file_obj:
        if file_obj.filelineno() == 1:
            if filelines:
                lines.append(filelines)
            filelines = []
        filelines.append(line)
    lines.append(filelines)
    return lines

def set_shift(cell, options):
    shift = np.array([float(x) for x in options.shift.split()])
    if len(shift) == 3:
        points = cell.get_points()
        points += shift.reshape(3, 1)
    else:
        sys.stderr.write("Atomic position shift is not correctly set.\n")

def transform_cell(cell, options, is_shift=True):
    if options.shift and is_shift:
        set_shift(cell, options)
    if options.t_mat:
        cell = _get_tmat_cell(cell, options)
    if options.is_r2h:
        if options.is_verbose:
            print "Transform cell by transformation matrix of rhombohedral to hexagonal:"
            print np.array(r2h)
        cell = get_supercell(cell, r2h)
    if options.s_mat:
        cell = _get_smat_cell(cell, options)
            
    return cell

def write_cells(write_func, cells,
                input_filenames=None, output_filename=None):
    for i, cell in enumerate(cells):
        if len(cells) > 1:
            if output_filename:
                root, ext = os.path.splitext(output_filename)
                write_func(cell, root + "-%03d" % (i + 1) + ext)
            else:
                print "-" * len(input_filenames[i])
                print input_filenames[i]
                print "-" * len(input_filenames[i])
                print write_func(cell)
        else:
            if output_filename:
                write_func(cell, output_filename)
            else:
                print write_func(cell),

def _get_matrix(mat):
    if len(mat) == 3:
        return np.diag(mat)
    elif len(mat) == 9:
        mat.shape = (3, 3)
        return mat
    else:
        return False

def _get_tmat_cell(cell, options):
    t_mat = np.array([frac2val(x) for x in options.t_mat.split()])
    t_mat = _get_matrix(t_mat)
    if t_mat is False:
        sys.stderr.write("Transformation matrix is not correctly set.\n")
        return False
    else:
        if options.is_verbose:
            print "Transform cell using transformation matrix:"
            print t_mat
        return reduce_points(t_mat, cell)

def _get_smat_cell(cell, options):
    s_mat = np.array([int(x) for x in options.s_mat.split()])
    s_mat = _get_matrix(s_mat)
    if s_mat is False:
        sys.stderr.write("Supercell matrix is not correctly set.\n")
        return False
    else:
        if options.is_verbose:
            print "Transform cell using supercell matrix:"
            print s_mat
        return get_supercell(cell, s_mat)

    
