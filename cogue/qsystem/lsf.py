"""Store and control jobs

1. A job is registered. Task-ID is used as the identifier.
   --> Task-ID is pushed to self._tid_queue. [preparing]

2. The job is submitted to queueing system if number of submitted
   jobs are less then specified max number of jobs. [submitted]
   --> Task-ID is removed from self._tid_queue.
   --> Job-ID is mapped to the task-ID by self._tid2jobid.

3. If the job-ID is not in the list of job-IDs in queueing system,
   the job is recognized as finished. [done]
   --> The key of task-ID in self._tid2jobid is removed.

4. If the job-ID is in the list of job-IDs in queueing system and
   the status of the job in queueing system is 'R':
   the job is recognized as running. [running]

"""

__all__ = ['queue', 'job']

import subprocess
import shlex
import os
import sys
import shutil
import tarfile
from cogue.qsystem import QueueBase, LocalQueueBase, RemoteQueueBase, JobBase

def queue(max_jobs=None,
          ssh_shell=None,
          temporary_dir=None):
    if ssh_shell is None:
        return LocalQueue(max_jobs=max_jobs)
    elif temporary_dir is not None:
        return RemoteQueue(ssh_shell,
                           temporary_dir,
                           max_jobs=max_jobs)

def job(script=None,
        shell=None,
        jobname=None,
        q=None,
        W="24:00",
        stdout=None,
        stderr=None):
    return Job(script=script,
               shell=shell,
               jobname=jobname,
               q=q,
               W=W,
               stdout=stdout,
               stderr=stderr)

class Qstat:
    def qstat(self):
        """qstatout

        Text of output of 'qjobs'

        """
        qstat_out = self._shell.run(["qjobs"]).output.split('\n')
        self._qstatus = {}

        for line in qstat_out[1:]:
            if len(line.split()) > 6:
                jobid = line.split()[0]
                if jobid.isdigit():
                    jobid = int(jobid)
                    s = line.split()[2]
                    self._qstatus[jobid] = s
                    if s == 'RUN':
                        self._qstatus[jobid] = 'Running'
                    elif s == 'PEND':
                        self._qstatus[jobid] = 'Pending'
        
class RemoteQueue(QueueBase,Qstat):
    def __init__(self,
                 ssh_shell,
                 temporary_dir,
                 max_jobs=None,
                 qsub_command="qsub"):
        QueueBase.__init__(self, max_jobs=max_jobs)
        self._qsub_command = qsub_command
        self._shell = ssh_shell
        self._temporary_dir = temporary_dir

    def submit(self, task):
        job = task.get_job()
        tid = task.get_tid()
        remote_dir = "%s/c%05d" % (self._temporary_dir, tid)
        self._set_job_status(job, tid)
        if "ready" in job.get_status():
            job.write_script()
            self._shell.run(["mkdir", "-p", remote_dir])
            tar = tarfile.open("cogue.tar", "w")
            for name in os.listdir("."):
                tar.add(name)
            tar.close()
            with open("cogue.tar", "rb") as local_file:
                with self._shell.open("%s/%s" % (remote_dir, "cogue.tar"),
                                      "wb") as remote_file:
                    shutil.copyfileobj(local_file, remote_file)
                    os.remove("cogue.tar")
                    self._shell.run(["tar", "xvf", "cogue.tar"], cwd=remote_dir)
                    self._shell.run(["rm", "cogue.tar"], cwd=remote_dir)
            if task.get_traverse():
                jobid = None
            else:
                qsub_out = self._shell.run(
                    shlex.split(self._qsub_command + " " + "job.sh"),
                    cwd=remote_dir).output
                jobid = int(qsub_out.split()[2]) # GE specific
            self._tid2jobid[tid] = jobid
            self._tid_queue.pop(0)
            job.set_status("submitted", jobid)

        elif "done" in job.get_status():
            names = self._shell.run(["/bin/ls"], cwd=remote_dir).output.split()
            self._shell.run(["tar", "cvf", "cogue.tar"] + names, cwd=remote_dir)
            with self._shell.open("%s/%s" % (remote_dir, "cogue.tar"),
                                  "rb") as remote_file:
                with open("cogue.tar", "wb") as local_file:
                    shutil.copyfileobj(remote_file, local_file)
                    tar = tarfile.open("cogue.tar")
                    tar.extractall()
                    tar.close()
                    os.remove("cogue.tar")
                    self._shell.run(["rm", "cogue.tar"], cwd=remote_dir)

def _get_jobid(qsub_out):
    return int(qsub_out.split()[1].replace("<", "").replace(">", ""))

class LocalQueue(LocalQueueBase,Qstat):
    def __init__(self,
                 max_jobs=None,
                 qsub_command="qsub"):
        LocalQueueBase.__init__(self,
                                max_jobs=max_jobs,
                                qsub_command=qsub_command)

    def _get_jobid(self, qsub_out):
        return _get_jobid(qsub_out)

class RemoteQueue(RemoteQueueBase,Qstat):
    def __init__(self,
                 ssh_shell,
                 temporary_dir,
                 max_jobs=None,
                 qsub_command="qsub"):
        QueueBase.__init__(self, max_jobs=max_jobs)
        self._qsub_command = qsub_command
        self._shell = ssh_shell
        self._temporary_dir = temporary_dir

    def _get_jobid(self, qsub_out):
        return _get_jobid(qsub_out)

class Job(JobBase):
    def __init__(self,
                 script=None,
                 shell=None,
                 jobname=None,
                 q=None,
                 W="24:00",
                 stdout=None,
                 stderr=None):

        if script is None:
            print "Queue script not found"
            sys.exit(1)
        else:
            self._script = script

        if q is None:
            print "Queue name must be set."
            sys.exit(1)
        else:
            self._q = q

        if shell is None:
            self._shell = "/bin/bash"
        else:
            self._shell = shell

        if jobname is None:
            self._jobname = "cogue-job"
        else:
            self._jobname = jobname

        self._W = W
        self._stdout = stdout
        self._stderr = stderr

        self._status = ""

    def copy(self, jobname=None):
        if jobname is None:
            jobname_new = self._jobname 
        else:
            jobname_new = jobname
        return Job(script=self._script,
                   shell=self._shell,
                   jobname=jobname_new,
                   q=self._q,
                   W=self._W,
                   stdout=self._stdout,
                   stderr=self._stderr)

    def write_script(self, filename="job.sh"):
        """
        #!/bin/bash
        #QSUB -q gr10260f
        #QSUB -W 1:00
        #QSUB -A p=20:t=1:c=1:m=3072M
        #QSUB -rn
        #QSUB -J togo
        #QSUB -e err.log
        #QSUB -o std.log
        
        module switch impi/4.0.3
        mpiexec.hydra vasp5.3.5
        """
        
        w = open(filename, 'w')
        w.write("#!%s\n" % self._shell)
        w.write("#QSUB -q %s\n" % self._q)
        w.write("#QSUB -W %s\n" % self._W)
        w.write("#QSUB -A p=20:t=1:c=1:m=3072M\n")
        w.write("#QSUB -rn\n")
        w.write("#QSUB -J %s\n" % self._jobname)
        if self._stderr:
            w.write("#QSUB -e %s\n" % self._stderr)
        if self._stdout:
            w.write("#QSUB -o %s\n" % self._stdout)
        
        w.write("\n")

        w.write(self._script)

        w.close()
