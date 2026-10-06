"""Keep Windows transport descendants inside their parent's lifetime."""
import os
import threading


def watch_parent_input():
    def wait_for_exit():
        try:
            os.read(0, 1)
        finally:
            os._exit(1)
    threading.Thread(target=wait_for_exit, daemon=True).start()


def own_process_tree():
    if os.name != 'nt':
        return None
    import ctypes as c
    from ctypes import wintypes as w
    class Basic(c.Structure):
        _fields_ = [('process_time', c.c_int64), ('job_time', c.c_int64), ('flags', w.DWORD),
                    ('minimum', c.c_size_t), ('maximum', c.c_size_t), ('active', w.DWORD),
                    ('affinity', c.c_size_t), ('priority', w.DWORD), ('scheduling', w.DWORD)]
    class IO(c.Structure):
        _fields_ = [(name, c.c_uint64) for name in ('read_ops', 'write_ops', 'other_ops', 'read_bytes', 'write_bytes', 'other_bytes')]
    class Limits(c.Structure):
        _fields_ = [('basic', Basic), ('io', IO), ('process_memory', c.c_size_t),
                    ('job_memory', c.c_size_t), ('peak_process', c.c_size_t), ('peak_job', c.c_size_t)]
    api = c.WinDLL('kernel32', use_last_error=True)
    api.CreateJobObjectW.argtypes = [c.c_void_p, w.LPCWSTR]
    api.CreateJobObjectW.restype = w.HANDLE
    api.SetInformationJobObject.argtypes = [w.HANDLE, c.c_int, c.c_void_p, w.DWORD]
    api.AssignProcessToJobObject.argtypes = [w.HANDLE, w.HANDLE]
    api.GetCurrentProcess.restype = w.HANDLE
    api.CloseHandle.argtypes = [w.HANDLE]
    job = api.CreateJobObjectW(None, None)
    limits = Limits()
    limits.basic.flags = 0x2000  # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE.
    if not job or not api.SetInformationJobObject(job, 9, c.byref(limits), c.sizeof(limits)):
        if job:
            api.CloseHandle(job)
        raise ValueError('Owned connection process could not start.')
    if not api.AssignProcessToJobObject(job, api.GetCurrentProcess()):
        api.CloseHandle(job)
        raise ValueError('Owned connection process could not start.')
    # Intentionally retain this non-inheritable handle until process exit. The
    # OS closes it if Near Dot kills this helper, terminating its descendants.
    return job
