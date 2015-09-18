from cogue.task import TaskElement
from cogue.crystal.cell import get_strained_cells
from cogue.task.structure_optimization import StructureOptimizationYaml


class BulkModulusBase(TaskElement, StructureOptimizationYaml):
    """BulkModulus class

    Three stages:
    1. Structure optimization of input cell
    2. Total energiy calculations with +1 and -1 % volumes
    3. Calculate bulk modulus from stress of two cells
    or 
    1. Structure optimization of input cell
    2. Total energy calculations at strains specified
    3. Calculate bulk modulus by fitting EOS (not yet implemented)
    
    """
    
    def __init__(self,
                 directory=None,
                 name=None,
                 strains=None,
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
        self._task_type = "bulk_modulus"

        self._strains = strains

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
        self._bulk_modulus = None
        self._all_tasks = None

    def get_bulk_modulus(self):
        return self._bulk_modulus

    def set_status(self):
        done = True
        terminate = False

        if self._stage == 0:
            task = self._tasks[0]
            if task.done():
                status = task.get_status()
                if status == "terminate" or status == "max_iteration":
                    self._status = status
                else:
                    self._status = "next"
        else:
            for task in self._tasks:
                done &= task.done()
                if task.get_status() == "terminate":
                    terminate = True
            if done:
                if terminate:
                    self._status = "terminate"
                else:
                    self._status = "next"

        self._write_yaml()
        
    def begin(self):
        if not self._job:
            print "set_job has to be executed."
            raise

        if self._is_cell_relaxed:
            self._all_tasks = [None]
            self._prepare_next()
        else:
            self._status = "equilibrium"
            self._all_tasks = [self._get_equilibrium_task()]
            self._tasks = [self._all_tasks[0]]

    def done(self):
        return (self._status == "done" or
                self._status == "terminate" or
                self._status == "max_iteration" or
                self._status == "next")

    def next(self):    
        if self._stage == 0:
            if self._status == "next":
                self._prepare_next()
                return self._tasks
        else:
            if self._status == "next":
                if self._strains is None:
                    stress_p = self._all_tasks[1].get_stress()
                    stress_m = self._all_tasks[2].get_stress()
    
                    if (stress_p is None or stress_m is None):
                        self._status = "terminate"
                    else:
                        self._calculate_bulk_modulus()
                        self._status = "done"
                else:
                    self._status = "done"

        self._write_yaml()
        raise StopIteration

    def _calculate_bulk_modulus(self):
        if self._is_cell_relaxed:
            V = self._cell.get_volume()
        else:
            V = self._all_tasks[0].get_cell().get_volume()
        V_p = self._all_tasks[1].get_cell().get_volume()
        V_m = self._all_tasks[2].get_cell().get_volume()
        s_p = self._all_tasks[1].get_stress()
        s_m = self._all_tasks[2].get_stress()

        self._bulk_modulus = - (s_p - s_m).trace() / 3 * V / (V_p - V_m)
        
    def _prepare_next(self):
        if self._is_cell_relaxed:
            cell = self._cell
        else:
            cell = self._all_tasks[0].get_cell()

        self._stage = 1
        self._status = "strains"

        if self._strains is None:
            tasks = self._get_plus_minus_tasks(cell)
        else:
            tasks = self._get_strained_cell_tasks(cell)

        self._all_tasks += tasks
        self._tasks = self._all_tasks[1:]

    def _get_plus_minus_tasks(self, cell):
        cell_plus, cell_minus = get_strained_cells(cell, [0.01, -0.01])
        plus = self._get_equilibrium_task(index=1,
                                          cell=cell_plus,
                                          max_iteration=3,
                                          min_iteration=1,
                                          directory="plus")
        minus = self._get_equilibrium_task(index=1,
                                           cell=cell_minus,
                                           max_iteration=3,
                                           min_iteration=1,
                                           directory="minus")
        return plus, minus

    def _get_strained_cell_tasks(self, cell_orig):
        tasks = []
        for i, cell in enumerate(get_strained_cells(cell_orig, self._strains)):
            tasks.append(
                self._get_equilibrium_task(index=1,
                                           cell=cell,
                                           max_iteration=3,
                                           min_iteration=1,
                                           directory="strain-%d" % (i + 1)))
        return tasks

    def get_yaml_lines(self):
        lines = TaskElement.get_yaml_lines(self)
        lines += self._get_structopt_yaml_lines()
        if self._is_cell_relaxed:
            cell = self._cell
        else:
            cell = self._all_tasks[0].get_cell()
        lines += cell.get_yaml_lines()

        if self._bulk_modulus:
            lines.append("bulk_modulus: %f\n" % self._bulk_modulus)

        return lines
