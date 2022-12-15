import collections
import hashlib
from math import ceil
import os
import struct

import repo
import util 

HEADER_FORMAT = "!4sLL"
ENTRY_FORMAT = "!LLLLLLLLLL20sH"

class GitIndexEntry(object):
    def __init__(
        self,
        ctime=None,
        mtime=None,
        dev=None,
        ino=None,
        mode_type=None,
        mode_perms=None,
        uid=None,
        gid=None,
        fsize=None,
        object_hash=None,
        flag_assume_valid=None,
        flag_extended=None,
        flag_stage=None,
        flag_name_length=None,
        name=None,
    ):
        """The last time a file's metadata changed.  This is a tuple (seconds, nanoseconds)"""
        self.ctime = ctime
        """The last time a file's data changed.  This is a tuple (seconds, nanoseconds)"""
        self.mtime = mtime
        """The ID of device containing this file"""
        self.dev = dev
        """The file's inode number"""
        self.ino = ino
        """The object type, either b1000 (regular), b1010 (symlink), b1110 (gitlink). """
        self.mode_type = mode_type
        """The object permissions, an integer."""
        self.mode_perms = mode_perms
        """User ID of owner"""
        self.uid = uid
        """Group ID of ownner (according to stat 2.  Isn'th)"""
        self.gid = gid
        """Size of this object, in bytes"""
        self.fsize = fsize
        """The object's hash as a hex string"""
        self.object_hash = object_hash
        self.flag_assume_valid = flag_assume_valid
        self.flag_extended = flag_extended
        self.flag_stage = flag_stage
        """Length of the name if < 0xFFF (yes, three Fs), -1 otherwise"""
        self.flag_name_length = flag_name_length
        self.name = name


class GitIndex(object):
    signature = None
    version = None
    entries = []
    # ext = None
    # sha = None

    def __init__(self, file):
        raw = None
        with open(file, "rb") as f:
            raw = f.read()

        header = raw[:12]
        self.signature = header[:4]
        self.version = hex(int.from_bytes(header[4:8], "big"))
        nindex = int.from_bytes(header[8:12], "big")

        self.entries = list()

        content = raw[12:]
        idx = 0
        for i in range(0, nindex):
            ctime = content[idx : idx + 8]
            mtime = content[idx + 8 : idx + 16]
            dev = content[idx + 16 : idx + 20]
            ino = content[idx + 20 : idx + 24]
            mode = content[idx + 24 : idx + 28]  # TODO
            uid = content[idx + 28 : idx + 32]
            gid = content[idx + 32 : idx + 36]
            fsize = content[idx + 36 : idx + 40]
            object_hash = content[idx + 40 : idx + 60]
            flag = content[idx + 60 : idx + 62]  # TODO
            null_idx = content.find(b"\x00", idx + 62)  # TODO
            name = content[idx + 62 : null_idx]

            idx = null_idx + 1
            idx = 8 * ceil(idx / 8)

            self.entries.append(
                GitIndexEntry(
                    ctime=ctime,
                    mtime=mtime,
                    dev=dev,
                    ino=ino,
                    mode_type=mode,
                    uid=uid,
                    gid=gid,
                    fsize=fsize,
                    object_hash=object_hash,
                    name=name,
                )
            )

IndexEntry = collections.namedtuple(
    "IndexEntry",
    [
        "ctime_s",
        "ctime_n",
        "mtime_s",
        "mtime_n",
        "dev",
        "ino",
        "mode",
        "uid",
        "gid",
        "size",
        "sha1",
        "flags",
        "path",
    ],
)


def read_index():
    """Read git index file and return list of IndexEntry objects."""
    try:
        data = util.read_file(os.path.join(".zygit", "index"))
    except FileNotFoundError:
        return []
    digest = hashlib.sha1(data[:-20]).digest()
    assert digest == data[-20:], "invalid index checksum"
    signature, version, num_entries = struct.unpack("!4sLL", data[:12])
    assert signature == b"DIRC", "invalid index signature {}".format(signature)
    assert version == 2, "unknown index version {}".format(version)
    entry_data = data[12:-20]
    entries = []
    i = 0
    while i + 62 < len(entry_data):
        fields_end = i + 62
        fields = struct.unpack("!LLLLLLLLLL20sH", entry_data[i:fields_end])
        path_end = entry_data.index(b"\x00", fields_end)
        path = entry_data[fields_end:path_end]
        entry = IndexEntry(*(fields + (path.decode(),)))
        entries.append(entry)
        entry_len = ((62 + len(path) + 8) // 8) * 8
        i += entry_len
    assert len(entries) == num_entries
    return entries


def write_index(entries) -> None:
    packed_entries = []
    for entry in entries:
        entry_head = struct.pack(
            ENTRY_FORMAT,
            entry.ctime[0],
            entry.ctime[1],
            entry.mtime[0],
            entry.mtime[1],
            entry.dev,
            entry.ino,
            entry.mode,
            entry.uid,
            entry.gid,
            entry.size,
            entry.obj,
            entry.flags,
        )
        path = entry.name.encode()
        length = ((62 + len(path) + 8) // 8) * 8
        packed_entry = entry_head + path + b"\x00" * (length - 62 - len(path))
        packed_entries.append(packed_entry)
    header = struct.pack(HEADER_FORMAT, b"DIRC", 2, len(entries))
    all_data = header + b"".join(packed_entries)
    digest = hashlib.sha1(all_data).digest()
    repository = repo.find()
    assert repository is not None
    with open(str(repo.file(repository, "index", write=True)), "wb") as f:
        f.write(all_data + digest)