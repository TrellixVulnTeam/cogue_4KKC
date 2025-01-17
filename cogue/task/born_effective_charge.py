"""Born effective charge class."""
from cogue.crystal.converter import cell2atoms
from cogue.task import TaskElement
from cogue.task.structure_optimization import StructureOptimizationYaml

try:
    from phonopy.structure.symmetry import symmetrize_borns_and_epsilon
except ImportError:
    print("You need to install phonopy.")
    import sys

    sys.exit(1)


class BornEffectiveChargeYaml(StructureOptimizationYaml):
    """Mix-in of yaml output of Born effective charge."""

    def _get_bec_yaml_lines(self, cell):
        lines = self._get_structopt_yaml_lines()
        if self._born is not None and self._epsilon is not None:
            lines.append("dielectric_constant:")
            for v in self._epsilon:
                lines.append("- [ %13.8f, %13.8f, %13.8f ]" % tuple(v))
            lines.append("born_effective_charge:")
            for i, z_ion in enumerate(self._born):
                lines.append("- # %d" % (i + 1))
                for v in z_ion:
                    lines.append("  - [ %13.8f, %13.8f, %13.8f ]" % tuple(v))

        if cell:
            lines += cell.get_yaml_lines()

        return lines


class BornEffectiveChargeBase(TaskElement, BornEffectiveChargeYaml):
    """BornEffectiveCharge class.

    Calculate Born effective charge and dielectric constant
    1. Structure optimization to obtain equilibrium structure
    2. Calculate Born effective charge and dielectric constant by a task that
       returns elastic constants.

    """

    def __init__(
        self,
        directory=None,
        name=None,
        lattice_tolerance=None,
        force_tolerance=None,
        pressure_target=None,
        stress_tolerance=None,
        max_increase=None,
        max_iteration=None,
        min_iteration=None,
        is_cell_relaxed=False,
        symmetry_tolerance=None,
        traverse=False,
    ):
        """Init method."""
        TaskElement.__init__(self)

        self._directory = directory
        if not name:
            self._name = directory
        else:
            self._name = name
        self._task_type = "born_effective_charge"
        self._lattice_tolerance = lattice_tolerance
        self._pressure_target = pressure_target
        self._stress_tolerance = stress_tolerance
        self._force_tolerance = force_tolerance
        self._max_increase = max_increase
        self._max_iteration = max_iteration
        self._min_iteration = min_iteration
        self._is_cell_relaxed = is_cell_relaxed
        self._symmetry_tolerance = symmetry_tolerance
        self._traverse = traverse

        self._stage = 0
        self._tasks = None

        self._cell = None
        self._all_tasks = None
        self._born = None
        self._epsilon = None
        self._energy = None

    def get_born_effective_charge(self):
        return self._born

    def get_dielectric_constant(self):
        return self._epsilon

    def get_cell(self):
        if self._is_cell_relaxed:
            return self._cell
        else:
            return self._all_tasks[0].get_cell()

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
            print("set_job has to be executed.")
            raise RuntimeError

        if self._is_cell_relaxed:
            self._all_tasks = [None]
            self._set_stage1()
        else:
            self._set_stage0()

    def done(self):
        return (
            self._status == "done"
            or self._status == "terminate"
            or self._status == "next"
        )

    def __next__(self):
        return self.next()

    def next(self):
        if self._stage == 0:
            if self._status == "next":
                self._energy = self._tasks[0].get_energy()
                self._set_stage1()
                return self._tasks
            elif self._status == "terminate" and self._traverse == "restart":
                self._traverse = False
                self._set_stage0()
                return self._tasks
        else:
            if self._status == "next":
                self._set_born_and_epsilon()
                self._status = "done"
            elif self._status == "terminate" and self._traverse == "restart":
                self._traverse = False
                self._set_stage1()
                return self._tasks

        self._write_yaml()
        raise StopIteration

    def _set_stage0(self):
        self._status = "equilibrium"
        task = self._get_equilibrium_task()
        self._all_tasks = [task]
        self._tasks = [task]

    def _set_stage1(self):
        self._stage = 1
        self._status = "born effective charge"
        bec_task = self._get_bec_task(self.get_cell())
        if len(self._all_tasks) == 2:
            self._all_tasks[1] = bec_task
        else:
            self._all_tasks.append(bec_task)
        self._tasks = [self._all_tasks[1]]

    def _set_born_and_epsilon(self):
        borns = self._all_tasks[1].get_born_effective_charge()
        epsilon = self._all_tasks[1].get_dielectric_constant()
        cell = cell2atoms(self.get_cell())
        self._born, self._epsilon = symmetrize_borns_and_epsilon(
            borns, epsilon, cell, symprec=self._symmetry_tolerance
        )

    def get_yaml_lines(self):
        lines = TaskElement.get_yaml_lines(self)
        cell = self.get_cell()
        lines += self._get_bec_yaml_lines(cell)
        if self._all_tasks[0] is not None:
            if self._energy:
                lines.append("electric_total_energy: %20.10f" % self._energy)

        return lines
