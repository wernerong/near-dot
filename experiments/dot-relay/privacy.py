"""Owner-only relay storage on POSIX and Windows. No credential diagnostics."""
import os
from pathlib import Path
import stat


def state_directory():
    if os.name == 'nt':
        return Path(os.environ['LOCALAPPDATA']) / 'Near Dot/live-connection'
    return Path.home() / 'Library/Application Support/Near Dot/transport-proof'


if os.name == 'nt':
    import ctypes as c
    from ctypes import wintypes as w
    adv = c.WinDLL('advapi32', use_last_error=True)
    kernel = c.WinDLL('kernel32', use_last_error=True)
    adv.ConvertStringSecurityDescriptorToSecurityDescriptorW.argtypes = [w.LPCWSTR, w.DWORD, c.POINTER(c.c_void_p), c.c_void_p]
    adv.ConvertStringSecurityDescriptorToSecurityDescriptorW.restype = w.BOOL
    adv.GetNamedSecurityInfoW.argtypes = [w.LPCWSTR, w.DWORD, w.DWORD, c.POINTER(c.c_void_p), c.c_void_p, c.POINTER(c.c_void_p), c.c_void_p, c.POINTER(c.c_void_p)]
    adv.GetNamedSecurityInfoW.restype = w.DWORD
    adv.ConvertSecurityDescriptorToStringSecurityDescriptorW.argtypes = [c.c_void_p, w.DWORD, w.DWORD, c.POINTER(w.LPWSTR), c.c_void_p]
    adv.ConvertSecurityDescriptorToStringSecurityDescriptorW.restype = w.BOOL
    adv.SetFileSecurityW.argtypes = [w.LPCWSTR, w.DWORD, c.c_void_p]
    adv.SetFileSecurityW.restype = w.BOOL
    kernel.LocalFree.argtypes = [c.c_void_p]
    kernel.LocalFree.restype = c.c_void_p
    kernel.GetCurrentProcess.restype = w.HANDLE
    kernel.CloseHandle.argtypes = [w.HANDLE]
    adv.OpenProcessToken.argtypes = [w.HANDLE, w.DWORD, c.POINTER(w.HANDLE)]
    adv.GetTokenInformation.argtypes = [w.HANDLE, c.c_int, c.c_void_p, w.DWORD, c.POINTER(w.DWORD)]
    adv.ConvertSidToStringSidW.argtypes = [c.c_void_p, c.POINTER(w.LPWSTR)]
    adv.ConvertStringSidToSidW.argtypes = [w.LPCWSTR, c.POINTER(c.c_void_p)]
    adv.EqualSid.argtypes = [c.c_void_p, c.c_void_p]
    adv.GetAce.argtypes = [c.c_void_p, w.DWORD, c.POINTER(c.c_void_p)]
    adv.GetSecurityDescriptorControl.argtypes = [c.c_void_p, c.POINTER(w.WORD), c.POINTER(w.DWORD)]
    adv.SetTokenInformation.argtypes = [w.HANDLE, c.c_int, c.c_void_p, w.DWORD]

    def own_new_files():
        # Elevated Windows tokens may default to the Administrators group as
        # owner. Set this helper's default owner to its own user SID before
        # SQLite or a child client creates files. Never repair existing files.
        token, sid = w.HANDLE(), c.c_void_p()
        if not adv.OpenProcessToken(kernel.GetCurrentProcess(), 8 | 0x80, c.byref(token)):
            raise ValueError('Private file ownership unavailable.')
        try:
            if not adv.ConvertStringSidToSidW(user_sid(), c.byref(sid)):
                raise ValueError('Private file ownership unavailable.')
            class Owner(c.Structure):
                _fields_ = [('sid', c.c_void_p)]
            owner = Owner(sid)
            if not adv.SetTokenInformation(token, 4, c.byref(owner), c.sizeof(owner)):
                raise ValueError('Private file ownership unavailable.')
        finally:
            if sid:
                kernel.LocalFree(sid)
            kernel.CloseHandle(token)

    def user_sid():
        token = w.HANDLE()
        if not adv.OpenProcessToken(kernel.GetCurrentProcess(), 8, c.byref(token)):
            raise ValueError('Private storage unavailable.')
        try:
            length = w.DWORD()
            adv.GetTokenInformation(token, 1, None, 0, c.byref(length))
            buffer = c.create_string_buffer(length.value)
            if not adv.GetTokenInformation(token, 1, buffer, length, c.byref(length)):
                raise ValueError('Private storage unavailable.')
            sid = c.cast(buffer, c.POINTER(c.c_void_p))[0]
            value = w.LPWSTR()
            if not adv.ConvertSidToStringSidW(sid, c.byref(value)):
                raise ValueError('Private storage unavailable.')
            try:
                return value.value
            finally:
                kernel.LocalFree(value)
        finally:
            kernel.CloseHandle(token)

    def protect_new_directory(path):
        # Protect the empty directory before writing any private data. No broad
        # administrators/SYSTEM grants: only this user's SID can read it.
        descriptor = c.c_void_p()
        sid = user_sid()
        inheritance = 'OICI' if path.is_dir() else ''
        sddl = 'O:' + sid + 'D:P(A;' + inheritance + ';FA;;;' + sid + ')'
        if not adv.ConvertStringSecurityDescriptorToSecurityDescriptorW(sddl, 1, c.byref(descriptor), None):
            raise ValueError('Private storage unavailable.')
        try:
            if not adv.SetFileSecurityW(str(path), 1 | 4 | 0x80000000, descriptor):
                raise ValueError('Private storage unavailable.')
        finally:
            kernel.LocalFree(descriptor)

    def check_windows(path):
        owner, acl, descriptor = c.c_void_p(), c.c_void_p(), c.c_void_p()
        if adv.GetNamedSecurityInfoW(str(path), 1, 1 | 4, c.byref(owner), None, c.byref(acl), None, c.byref(descriptor)):
            raise ValueError('Private file permissions required.')
        current = c.c_void_p()
        try:
            if not acl.value or not adv.ConvertStringSidToSidW(user_sid(), c.byref(current)):
                raise ValueError('Private file permissions required.')
            if not adv.EqualSid(owner, current):
                raise ValueError('Private file ownership required.')
            control, revision = w.WORD(), w.DWORD()
            if not adv.GetSecurityDescriptorControl(descriptor, c.byref(control), c.byref(revision)):
                raise ValueError('Private file permissions required.')
            if path.is_dir() and not control.value & 0x1000:
                raise ValueError('Private directory inheritance must be disabled.')
            # Reject every ACE other than an allow for the current user. This
            # also rejects a null DACL, Everyone, inherited public access and
            # unfamiliar conditional/object ACEs rather than guessing.
            class ACL(c.Structure):
                _fields_ = [('revision', w.BYTE), ('reserved', w.BYTE), ('size', w.WORD),
                            ('count', w.WORD), ('reserved2', w.WORD)]
            count = c.cast(acl, c.POINTER(ACL)).contents.count
            if not count:
                raise ValueError('Private file permissions required.')
            for index in range(count):
                ace = c.c_void_p()
                if not adv.GetAce(acl, index, c.byref(ace)) or c.cast(ace, c.POINTER(w.BYTE))[0] != 0:
                    raise ValueError('Private file permissions required.')
                # ACCESS_ALLOWED_ACE has a four-byte header, four-byte access
                # mask, then the SID. Compare binary SIDs: SDDL may abbreviate
                # a built-in account and cannot be used for identity equality.
                if not adv.EqualSid(c.c_void_p(ace.value + 8), current):
                    raise ValueError('Private file permissions required.')
        finally:
            if current:
                kernel.LocalFree(current)
            kernel.LocalFree(descriptor)


def reject_links(path):
    for item in [path, *path.parents]:
        if item.is_symlink() or (item.exists() and getattr(item.lstat(), 'st_file_attributes', 0) & 0x400):
            raise ValueError('Private files cannot use links or reparse points.')


def private_path(path):
    path = Path(path).absolute()
    reject_links(path)
    if path.exists():
        if os.name == 'nt':
            check_windows(path)
        elif path.stat().st_uid != os.getuid() or stat.S_IMODE(path.stat().st_mode) & 0o077:
            raise ValueError('Private file permissions required.')
    return path


def private_directory(path):
    path = Path(path).absolute()
    reject_links(path)
    if os.name == 'nt':
        own_new_files()
    if not path.exists():
        path.mkdir(parents=True, mode=0o700)
        if os.name == 'nt':
            protect_new_directory(path)
    return private_path(path)


def write_new(path, value):
    path = private_path(path)
    private_path(path.parent)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, 'O_NOFOLLOW', 0), 0o600)
    if os.name == 'nt':
        try:
            protect_new_directory(path)
        except Exception:
            os.close(descriptor)
            path.unlink()
            raise
    with os.fdopen(descriptor, 'w', encoding='utf-8') as stream:
        stream.write(value)
        stream.flush()
        os.fsync(stream.fileno())
    private_path(path)
