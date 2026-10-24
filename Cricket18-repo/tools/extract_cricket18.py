"""Cuts the Cricket 07 executable out of the Cricket 18 mod's launcher and undoes the launcher's hooks.

  python3 tools/extract_cricket18.py <Cricket18.exe> <out/cricket07.exe>

The mod's Cricket18.exe is a Visual Basic launcher with the game's executable embedded in it. It starts that
executable and then fills four code caves in its uninitialised data (0xa3d759..0xa3d78f) with
WriteProcessMemory; the embedded executable's call sites already call into them. Each cave bumps a counter
only the launcher reads and then runs the one instruction its call replaced. Without the launcher the caves
are empty, so the game would crash the first time one runs (as a match starts). Putting the replaced
instructions back makes the caves unused.

It also enlarges the game's main heap: the mod's high-resolution kits and faces outgrow Cricket 07's 96 MB,
and a match then dies with "OUT OF MEMORY!" (usually in the second innings, when the other side loads).
"""
import struct
import sys

# call site -> (bytes there in the mod: call cave + nop padding, the original instruction from the cave)
HOOKS = {
    0x556958: ("e8fc6d4e0090", "8b881c010000"),    # mov ecx, [eax+0x11c]
    0x420995: ("e8cecd61009090", "898c96500c0000"),  # mov [esi+edx*4+0xc50], ecx
    0x4209bc: ("e8b5cd61009090", "899486500c0000"),  # mov [esi+eax*4+0xc50], edx
    0x43d792: ("e8edff5f0090", "898680000000"),    # mov [esi+0x80], eax
}

# the main heap's size: 0x6ff4e0 is `mov eax, 0x6000000; ret` (96 MB) -> 160 MB
# (runtime/runtime.h leaves room for it in the browser build)
HEAP_SIZE = (0x6ff4e3, "b800000006", "b80000000a")


def embedded_exe(data):
    """The PE image inside the launcher: the second 'MZ' with a valid PE header, cut at its last section's end."""
    i = 2
    while (i := data.find(b"MZ", i)) >= 0:
        pe = i + struct.unpack_from("<I", data, i + 0x3C)[0] if i + 0x40 <= len(data) else 0
        if pe and pe + 4 <= len(data) and data[pe:pe + 4] == b"PE\0\0":
            nsec = struct.unpack_from("<H", data, pe + 6)[0]
            sh = pe + 24 + struct.unpack_from("<H", data, pe + 20)[0]
            end = max(sum(struct.unpack_from("<II", data, sh + 40 * k + 16)) for k in range(nsec))
            return bytearray(data[i:i + end])
        i += 2
    sys.exit("no embedded executable found")


def file_offset(exe, va):
    pe = struct.unpack_from("<I", exe, 0x3C)[0]
    base = struct.unpack_from("<I", exe, pe + 24 + 28)[0]
    nsec = struct.unpack_from("<H", exe, pe + 6)[0]
    sh = pe + 24 + struct.unpack_from("<H", exe, pe + 20)[0]
    for k in range(nsec):
        vsize, rva, rawsize, rawptr = struct.unpack_from("<IIII", exe, sh + 40 * k + 8)
        if rva <= va - base < rva + rawsize:
            return rawptr + va - base - rva
    sys.exit(f"{va:08x} is not in the file")


def main():
    exe = embedded_exe(open(sys.argv[1], "rb").read())
    for va, (before, after) in [*HOOKS.items(), (HEAP_SIZE[0], HEAP_SIZE[1:])]:
        off, before, after = file_offset(exe, va), bytes.fromhex(before), bytes.fromhex(after)
        have = bytes(exe[off:off + len(before)])
        if have == before:
            exe[off:off + len(after)] = after
        elif have != after:
            sys.exit(f"unexpected bytes at {va:08x}: {have.hex()} (a different version of the mod?)")
    open(sys.argv[2], "wb").write(exe)
    print(f"wrote {sys.argv[2]} ({len(exe)} bytes, {len(HOOKS)} hooks restored, main heap 160 MB)")


if __name__ == "__main__":
    main()
