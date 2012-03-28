import hashlib

import h5py
import numpy as np

from hyperion.util.meshgrid import meshgrid_nd
from hyperion.util.functions import FreezableClass, is_numpy_array, monotonically_increasing, link_or_copy


class SphericalPolarGrid(FreezableClass):

    def __init__(self, *args):

        self.nr = None
        self.nt = None
        self.np = None

        self.shape = None

        self.r_wall = None
        self.t_wall = None
        self.p_wall = None

        self.r = None
        self.t = None
        self.p = None

        self.gr = None
        self.gt = None
        self.gp = None

        self.gw = None
        self.gz = None

        self.volumes = None
        self.areas = None
        self.widths = None

        self.quantities = {}

        self._freeze()

        if len(args) > 0:
            self.set_walls(*args)

    def set_walls(self, r_wall, t_wall, p_wall):

        if type(r_wall) in [list, tuple]:
            r_wall = np.array(r_wall)
        if type(t_wall) in [list, tuple]:
            t_wall = np.array(t_wall)
        if type(p_wall) in [list, tuple]:
            p_wall = np.array(p_wall)

        if not is_numpy_array(r_wall) or r_wall.ndim != 1:
            raise ValueError("r_wall should be a 1-D sequence")
        if not is_numpy_array(t_wall) or t_wall.ndim != 1:
            raise ValueError("t_wall should be a 1-D sequence")
        if not is_numpy_array(p_wall) or p_wall.ndim != 1:
            raise ValueError("p_wall should be a 1-D sequence")

        if not monotonically_increasing(r_wall):
            raise ValueError("r_wall should be monotonically increasing")
        if not monotonically_increasing(t_wall):
            raise ValueError("t_wall should be monotonically increasing")
        if not monotonically_increasing(p_wall):
            raise ValueError("p_wall should be monotonically increasing")

        # Find number of grid cells
        self.nr = len(r_wall) - 1
        self.nt = len(t_wall) - 1
        self.np = len(p_wall) - 1

        self.shape = (self.np, self.nt, self.nr)

        # Store wall positions
        self.r_wall = r_wall
        self.t_wall = t_wall
        self.p_wall = p_wall

        # Compute cell centers
        self.r = 10. ** ((np.log10(r_wall[:-1]) + np.log10(r_wall[1:])) / 2.)
        if r_wall[0] == 0.:
            self.r[0] = r_wall[1] / 2.
        self.t = (t_wall[:-1] + t_wall[1:]) / 2.
        self.p = (p_wall[:-1] + p_wall[1:]) / 2.

        # Generate 3D versions of r, t, p
        #(each array is 3D and defined in every cell)
        self.gr, self.gt, self.gp = meshgrid_nd(self.r, self.t, self.p)

        # Compute cell centers in cylindrical coordinates
        self.gz = self.gr * np.cos(self.gt)
        self.gw = self.gr * np.sin(self.gt)

        # Generate 3D versions of the inner and outer wall positions respectively
        gr_wall_min, gt_wall_min, gp_wall_min = \
                    meshgrid_nd(r_wall[:-1], t_wall[:-1], p_wall[:-1])
        gr_wall_max, gt_wall_max, gp_wall_max = \
                    meshgrid_nd(r_wall[1:], t_wall[1:], p_wall[1:])

        # USEFUL QUANTITIES

        dr = gr_wall_max - gr_wall_min
        dr2 = gr_wall_max ** 2 - gr_wall_min ** 2
        dr3 = gr_wall_max ** 3 - gr_wall_min ** 3
        dt = gt_wall_max - gt_wall_min
        dcost = np.cos(gt_wall_min) - np.cos(gt_wall_max)
        dp = gp_wall_max - gp_wall_min

        # CELL VOLUMES

        #   dV = dr * (r*dtheta) * (r*sin(theta)*dphi)
        #    V = [r_2^3 - r_1^3] / 3. * [cos(theta_1) - cos(theta_2)] * [phi_2 - phi_1]

        self.volumes = dr3 * dcost * dp / 3.

        # WALL AREAS

        self.areas = np.zeros((6, self.np, self.nt, self.nr))

        # R walls:
        #   dA = r^2 * sin(theta) * dtheta * dphi
        #    A = r^2 * [cos(theta_1) - cos(theta_2)] * [phi_2 - phi_1]

        self.areas[0, :, :, :] = gr_wall_min ** 2 * dcost * dp
        self.areas[1, :, :, :] = gr_wall_max ** 2 * dcost * dp

        # Theta walls:
        #   dA = r * sin(theta) * dr * dphi
        #    A = 0.5 * [r_2^2 - r_1^2] * sin(theta) * [phi_2 - phi_1]

        self.areas[2, :, :, :] = 0.5 * dr2 * np.sin(gt_wall_min) * dp
        self.areas[3, :, :, :] = 0.5 * dr2 * np.sin(gt_wall_max) * dp

        # Phi walls:
        #   dA = r * dr * dtheta
        #    A = 0.5 * [r_2^2 - r_1^2] * [theta_2 - theta_1]

        self.areas[4, :, :, :] = 0.5 * dr2 * dt
        self.areas[5, :, :, :] = 0.5 * dr2 * dt

        # CELL WIDTHS

        self.widths = np.zeros((3, self.np, self.nt, self.nr))

        # R direction:
        #   dS = dr
        #    S = r_2 - r_1

        self.widths[0, :, :, :] = dr

        # Theta direction:
        #   dS = r * dtheta
        #    S = r * [theta_2 - theta_1]

        self.widths[1, :, :, :] = self.gr * dt

        # Phi direction:
        #   dS = r * sin(theta) * dphi
        #    S = r * sin(theta) * [phi_2 - phi_1]

        self.widths[2, :, :, :] = self.gr * np.sin(self.gt) * dp

    def _check_array_dimensions(self, array):

        if type(array) in [list, tuple]:

            # Check that dimensions are compatible
            for item in array:
                if item.shape != self.shape:
                    raise ValueError("Arrays in list do not have the right "
                                     "dimensions: %s instead of %s"
                                     % (item.shape, self.shape))

            # Convert list of 3D arrays to a single 4D array
            shape = list(self.shape)
            shape.insert(0, len(array))
            array = np.vstack(array).reshape(*shape)

        elif type(array) == np.ndarray:

            if array.shape != self.shape:
                raise ValueError("Array does not have the right "
                                 "dimensions: %s instead of %s"
                                 % (array.shape, self.shape))

        else:

            raise ValueError("Array should be a list or a Numpy array")

    def read(self, group, quantities='all'):
        '''
        Read in a spherical polar grid

        Parameters
        ----------
        group: h5py.Group
            The HDF5 group to read the grid from
        quantities: 'all' or list
            Which physical quantities to read in. Use 'all' to read in all
            quantities or a list of strings to read only specific quantities.
        '''

        # Extract HDF5 groups for geometry and physics

        g_geometry = group['Geometry']
        g_physics = group['Physics']

        # Read in geometry

        if g_geometry.attrs['grid_type'] != 'sph_pol':
            raise ValueError("Grid is not spherical polar")

        self.set(g_geometry['Walls 1'], g_geometry['Walls 2'], g_geometry['Walls 3'])

        # Check that advertised hash matches real hash
        if g_geometry.attrs['geometry'] != self.get_geometry_id():
            raise Exception("Calculated geometry hash does not match hash in file")

        # Read in physical quantities

        for quantity in g_physics:
            if quantities == 'all' or quantity in quantities:
                # TODO - if array is 4D, need to convert to list
                self.quantities[quantity] = np.array(g_physics[quantity].array)

    def write(self, group, quantities='all', copy=True, absolute_paths=False, compression=True, wall_dtype=float, physics_dtype=float):
        '''
        Write out the spherical polar grid

        Parameters
        ----------
        group: h5py.Group
            The HDF5 group to write the grid to
        quantities: 'all' or list
            Which physical quantities to write out. Use 'all' to write out all
            quantities or a list of strings to write only specific quantities.
        compression: bool
            Whether to compress the arrays in the HDF5 file
        wall_dtype: type
            The datatype to use to write the wall positions
        physics_dtype: type
            The datatype to use to write the physical quantities
        '''

        # Create HDF5 groups if needed

        if 'Geometry' not in group:
            g_geometry = group.create_group('Geometry')
        else:
            g_geometry = group['Geometry']

        if 'Physics' not in group:
            g_physics = group.create_group('Physics')
        else:
            g_physics = group['Physics']

        # Write out geometry

        g_geometry.attrs['grid_type'] = 'sph_pol'
        g_geometry.attrs['geometry'] = self.get_geometry_id()

        dset = g_geometry.create_dataset("Walls 1", data=np.array(zip(self.r_wall), dtype=[('r', wall_dtype)]), compression=compression)
        dset.attrs['Unit'] = 'cm'

        dset = g_geometry.create_dataset("Walls 2", data=np.array(zip(self.t_wall), dtype=[('t', wall_dtype)]), compression=compression)
        dset.attrs['Unit'] = 'cm'

        dset = g_geometry.create_dataset("Walls 3", data=np.array(zip(self.p_wall), dtype=[('p', wall_dtype)]), compression=compression)
        dset.attrs['Unit'] = 'cm'

        # Write out physical quantities

        for quantity in self.quantities:
            if quantities == 'all' or quantity in quantities:
                if isinstance(self.quantities[quantity], h5py.ExternalLink):
                    link_or_copy(g_physics, quantity, self.quantities[quantity], copy, absolute_paths=absolute_paths)
                else:
                    self._check_array_dimensions(self.quantities[quantity])
                    dset = g_physics.create_dataset(quantity, data=self.quantities[quantity],
                                                    compression=compression,
                                                    dtype=physics_dtype)
                    dset.attrs['geometry'] = self.get_geometry_id()


    def get_geometry_id(self):
        geo_hash = hashlib.md5()
        geo_hash.update(self.r_wall)
        geo_hash.update(self.t_wall)
        geo_hash.update(self.p_wall)
        return geo_hash.hexdigest()
