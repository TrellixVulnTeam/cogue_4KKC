import numpy as np
from mayavi import mlab
from cogue.crystal.atom import atomic_jmol_colors, covalent_radii

def set_figure():
    mlab.figure(bgcolor=(1,1,1))

def show():
    mlab.show()

def savefig(filename, size=None):
    mlab.savefig(filename, size=size)

def line_plot(m, n, pt, color=None):
    mlab.plot3d([pt[m][0], pt[n][0]],
                [pt[m][1], pt[n][1]],
                [pt[m][2], pt[n][2]],
                tube_radius=0.015, opacity=1, color=color)

def plot_lattice(lattice, color=None):
    lat = lattice.T
    origin = np.zeros(3)
    pt = [origin,
          lat[0],
          lat[1],
          lat[2],
          lat[0] + lat[1],
          lat[1] + lat[2],
          lat[2] + lat[0],
          lat[0] + lat[1] + lat[2]]

    pt = np.array(pt)
    
    line_plot(0, 1, pt, color)
    line_plot(0, 2, pt, color)
    line_plot(0, 3, pt, color)
    line_plot(4, 7, pt, color)
    line_plot(5, 7, pt, color)
    line_plot(6, 7, pt, color)
    line_plot(1, 4, pt, color)
    line_plot(2, 5, pt, color)
    line_plot(3, 6, pt, color)
    line_plot(1, 6, pt, color)
    line_plot(2, 4, pt, color)
    line_plot(3, 5, pt, color)

def plot_axes(lattice, color=(1, 0, 0)):
    lat = np.transpose([x/np.linalg.norm(x) for x in lattice.T])
    mlab.quiver3d([0, 0, 0],
                  [0, 0, 0],
                  [0, 0, 0],
                  lat[0],
                  lat[1],
                  lat[2],
                  color=color,
                  line_width=3,
                  scale_factor=1)

    for c, v in zip(('a','b','c'), (lat * 1.3).T):
        mlab.text3d(v[0]+0.15, v[1], v[2], c, color=color, scale=0.3)

def plot_lattice_points(lattice, dim):
    lat_points = []
    for i in range(-dim[0], dim[0] + 1):
        for j in range(-dim[1], dim[1] + 1):
            for k in range(-dim[2], dim[2] + 1):
                lat_points.append([i, j, k])

    lp = np.dot(lattice, np.transpose(lat_points))
    mlab.points3d(lp[0], lp[1], lp[2],
                  scale_factor=0.2, opacity=0.2, color=(0,0,0))              

def plot_atoms(cell, shift=[0,0,0], atom_scale=0.4):
    points = cell.get_points()
    points += np.reshape(shift, (3, 1))
    points -= np.floor(points)
    symbols = cell.get_symbols()
    
    xs, ys, zs = np.dot(cell.get_lattice(), points)
    for x, y, z, s in zip(xs, ys, zs, symbols):
        color = tuple(np.array(atomic_jmol_colors[s], dtype=float) / 256)
        mlab.points3d(x, y, z,
                      resolution=16,
                      scale_factor=covalent_radii[s],
                      color=color)

# def plot_modulation(lattice, positions, modulation):
#     modu = np.dot(modulation, lattice)
#     x = positions[:,0]
#     y = positions[:,1]
#     z = positions[:,2]
#     u = modu[:,0]
#     v = modu[:,1]
#     w = modu[:,2]
#     mlab.quiver3d(x, y, z, u, v, w,
#                    color=(0,0,0),
#                    line_width=3,
#                    scale_factor=10*options.amp_modulation)
#     plot_atoms(positions)

