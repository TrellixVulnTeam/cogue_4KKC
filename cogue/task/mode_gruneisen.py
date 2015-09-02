from cogue.task import TaskElement
import numpy as np

class ModeGruneisenBase(TaskElement):
    """ModeGruneisen class

    Three stages:
    1. structure optimization of input cell
    2. create cells with, e.g. +1% and -1% volumes or strains, and optimize them
    3. calculate phonons for three cells
    4. calculate mode-Gruneisen parameters (This is not yet implemented.)
    
    """
    
    def __init__(self,
                 directory=None,
                 name=None,
                 delta_strain=None,
                 strain=None,
                 bias=None,
                 supercell_matrix=None,
                 primitive_matrix=None,
                 distance=None,
                 lattice_tolerance=None,
                 force_tolerance=None,
                 pressure_target=None,
                 stress_tolerance=None,
                 max_increase=None,
                 max_iteration=None,
                 min_iteration=None,
                 is_cell_relaxed=False,
                 traverse=False):

        TaskElement.__init__(self)

        self._directory = directory
        if not name:
            self._name = directory
        else:
            self._name = name
        self._task_type = "mode_gruneisen"

        self._bias = bias
        if delta_strain is None:
            self._delta_strain = 0.001
        else:
            self._delta_strain = delta_strain
        (self._delta_strain_minus,
         self._delta_strain_orig,
         self._delta_strain_plus) = self._get_delta_strains()
        if strain is None:
            self._strain = np.eye(3)
        else:
            self._strain = self._get_strain(strain)
        
        self._supercell_matrix = supercell_matrix
        self._primitive_matrix = primitive_matrix
        self._distance = distance
        self._lattice_tolerance = lattice_tolerance
        self._pressure_target = pressure_target
        self._stress_tolerance = stress_tolerance
        self._force_tolerance = force_tolerance
        self._max_increase = max_increase
        self._max_iteration = max_iteration
        self._min_iteration = min_iteration
        self._traverse = traverse
        self._is_cell_relaxed = is_cell_relaxed
        
        self._stage = 0
        self._tasks = None

        self._cell = None
        self._mode_gruneisen = None
        self._mg_tasks = None

    def get_mode_gruneisen(self):
        return self._mode_gruneisen

    def set_status(self):
        done = True
        terminate = False
        for task in self._tasks:
            done &= task.done()
            if task.get_status() == "terminate":
                terminate = True
        if done:
            if terminate:
                self._status = "terminate"
            else:
                self._status = "next"

    def begin(self):
        if not self._job:
            print "set_job has to be executed."
            raise

        if self._is_cell_relaxed:
            self._mg_tasks = [None]
            self._prepare_next(self._cell)
        else:
            self._status = "equilibrium"
            self._mg_tasks = [self._get_equilibrium_task()]
            self._tasks = [self._mg_tasks[0]]

    def done(self):
        return (self._status == "done" or
                self._status == "terminate" or
                self._status == "next")

    def next(self):    
        if self._stage == 0:
            if self._status == "next":
                self._prepare_next(self._mg_tasks[0].get_cell())
                return self._tasks
        else:
            if self._status == "next":
                self._calculate_mode_gruneisen()
                self._status = "done"

        self._write_yaml()
        raise StopIteration

    def _calculate_mode_gruneisen(self):
        self._mode_gruneisen = None
        
    def _prepare_next(self, cell):
        self._stage = 1
        self._status = "phonons"
        self._mg_tasks += self._get_phonon_tasks(cell)
        self._tasks = self._mg_tasks[1:]

    def _get_delta_strains(self):
        if self._bias is "plus":
            return (np.eye(3),
                    self._get_strain(self._delta_strain, factor=1),
                    self._get_strain(self._delta_strain, factor=2))
        elif self._bias is "minus":
            return (self._get_strain(self._delta_strain, factor=-2),
                    self._get_strain(self._delta_strain, factor=-1),       
                    np.eye(3))
        else:
            return (self._get_strain(self._delta_strain, factor=-1),
                    np.eye(3),
                    self._get_strain(self._delta_strain, factor=1))
        
    def _get_strain(self, strain, factor=1):
        if isinstance(strain, int) or isinstance(strain, float):
            return (1 + factor * strain) ** (1.0 / 3) * np.eye(3)
        else:
            return np.eye(3) + factor * np.array(strain)
            
    def _write_yaml(self):
        w = open("%s.yaml" % self._directory, 'w')
        if self._mg_tasks[0]:
            if self._lattice_tolerance is not None:
                w.write("lattice_tolerance: %f\n" % self._lattice_tolerance)
            if self._stress_tolerance is not None:
                w.write("stress_tolerance: %f\n" % self._stress_tolerance)
                w.write("pressure_target: %f\n" % self._pressure_target)
            w.write("force_tolerance: %f\n" % self._force_tolerance)
            if self._max_increase is None:
                w.write("max_increase: unset\n")
            else:
                w.write("max_increase: %f\n" % self._max_increase)
            w.write("max_iteration: %d\n" % self._max_iteration)
            w.write("min_iteration: %d\n" % self._min_iteration)
            w.write("iteration: %d\n" % self._mg_tasks[0].get_stage())
        w.write("status: %s\n" % self._status)
        w.write("supercell_matrix:\n")
        for row in self._supercell_matrix:
            w.write("- [ %3d, %3d, %3d ]\n" % tuple(row))
        if self._primitive_matrix is not None:
            w.write("primitive_matrix:\n")
            for row in self._primitive_matrix:
                w.write("- [ %6.3f, %6.3f, %6.3f ]\n" % tuple(row))
        w.write("distance: %f\n" % self._distance)
        if self._is_cell_relaxed:
            cell = self._cell
        else:
            cell = self._mg_tasks[0].get_cell()

        if cell:
            for line in cell.get_yaml_lines():
                w.write(line + "\n")

        w.close()
