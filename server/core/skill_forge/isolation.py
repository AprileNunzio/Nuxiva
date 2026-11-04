import ctypes
import os
import platform

PR_SET_DUMPABLE = 4
PR_SET_SECCOMP = 22
PR_SET_NO_NEW_PRIVS = 38
SECCOMP_MODE_FILTER = 2

CLONE_NEWNS = 0x00020000
CLONE_NEWUTS = 0x04000000
CLONE_NEWIPC = 0x08000000
CLONE_NEWUSER = 0x10000000
CLONE_NEWNET = 0x40000000

BPF_LD_W_ABS = 0x20
BPF_JEQ_K = 0x15
BPF_JGE_K = 0x35
BPF_RET_K = 0x06
RET_ALLOW = 0x7FFF0000
RET_KILL = 0x80000000
X32_FLAG = 0x40000000

ARCHITECTURES = {
    "x86_64": 0xC000003E,
    "aarch64": 0xC00000B7,
}

DENIED = {
    "x86_64": (
        41, 42, 43, 44, 45, 46, 47, 49, 50, 51, 53, 288, 56, 57, 58, 59, 322, 435, 101, 310, 311, 165, 166, 155, 161,
        169, 175, 176, 313, 246, 320, 248, 249, 250, 272, 308, 298, 321, 323, 425, 426, 427, 304, 167, 168, 105, 106,
        259,
    ),
    "aarch64": (
        198, 199, 200, 201, 202, 203, 204, 206, 207, 211, 212, 242, 220, 221, 281, 435, 117, 270, 271, 40, 39, 41, 51,
        142, 105, 106, 273, 104, 294, 217, 218, 219, 97, 268, 241, 280, 282, 425, 426, 427, 265, 224, 225, 146, 144,
        33,
    ),
}


class _Instruction(ctypes.Structure):
    _fields_ = [("code", ctypes.c_ushort), ("jt", ctypes.c_ubyte), ("jf", ctypes.c_ubyte), ("k", ctypes.c_uint32)]


class _Program(ctypes.Structure):
    _fields_ = [("length", ctypes.c_ushort), ("filter", ctypes.POINTER(_Instruction))]


def program(machine: str) -> list[tuple[int, int, int, int]]:
    denied = DENIED[machine]
    guard_x32 = machine == "x86_64"
    checks = len(denied) + (1 if guard_x32 else 0)
    first = 4
    kill_index = first + checks + 1
    steps = [(BPF_LD_W_ABS, 0, 0, 4), (BPF_JEQ_K, 1, 0, ARCHITECTURES[machine]), (BPF_RET_K, 0, 0, RET_KILL),
             (BPF_LD_W_ABS, 0, 0, 0)]
    if guard_x32:
        steps.append((BPF_JGE_K, kill_index - (len(steps) + 1), 0, X32_FLAG))
    for number in denied:
        steps.append((BPF_JEQ_K, kill_index - (len(steps) + 1), 0, number))
    steps.append((BPF_RET_K, 0, 0, RET_ALLOW))
    steps.append((BPF_RET_K, 0, 0, RET_KILL))
    return steps


def _libc() -> ctypes.CDLL:
    return ctypes.CDLL(None, use_errno=True)


def _namespaces(libc: ctypes.CDLL) -> bool:
    attempts = (CLONE_NEWUSER | CLONE_NEWNET | CLONE_NEWIPC | CLONE_NEWUTS | CLONE_NEWNS,
                CLONE_NEWUSER | CLONE_NEWNET | CLONE_NEWIPC | CLONE_NEWUTS,
                CLONE_NEWNET | CLONE_NEWIPC | CLONE_NEWUTS)
    return any(libc.unshare(flags) == 0 for flags in attempts)


def _seccomp(libc: ctypes.CDLL, machine: str) -> bool:
    if machine not in ARCHITECTURES:
        return False
    steps = program(machine)
    filters = (_Instruction * len(steps))(*[_Instruction(*step) for step in steps])
    compiled = _Program(len(steps), filters)
    if libc.prctl(PR_SET_SECCOMP, SECCOMP_MODE_FILTER, ctypes.byref(compiled), 0, 0) != 0:
        return False
    return True


def apply() -> dict[str, bool]:
    state = {"namespaces": False, "no_new_privs": False, "seccomp": False}
    if not hasattr(os, "uname") or platform.system() != "Linux":
        return state
    try:
        libc = _libc()
        libc.prctl(PR_SET_DUMPABLE, 0, 0, 0, 0)
        state["namespaces"] = _namespaces(libc)
        state["no_new_privs"] = libc.prctl(PR_SET_NO_NEW_PRIVS, 1, 0, 0, 0) == 0
        state["seccomp"] = state["no_new_privs"] and _seccomp(libc, platform.machine())
    except (OSError, AttributeError, TypeError):
        return state
    return state
