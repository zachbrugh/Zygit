import os
import os.path
import pickle


class GitIndexEntry(object):
    def __init__(
        self,
        ctime=None,
        mtime=None,
        uid=None,
        fsize=None,
        object_hash=None,
        name=None,
    ):
        """The last time a file's metadata changed.  This is a tuple (seconds, nanoseconds)"""
        self.ctime = ctime
        """The last time a file's data changed.  This is a tuple (seconds, nanoseconds)"""
        self.mtime = mtime
        """User ID of owner"""
        self.uid = uid
        """Size of this object, in bytes"""
        self.fsize = fsize
        """The object's hash"""
        self.object_hash = object_hash
        """The object's path relative to the root"""
        self.name = name

    def __repr__(self):
        return (
            f"ctime: {self.ctime}\n"
            f"mtime: {self.mtime}\n"
            f"uid: {self.uid}\n"
            f"fsize: {self.fsize}\n"
            f"object_hash: {self.object_hash}\n"
            f"name: {self.name}\n"
        )

class GitIndex(object):
    entries = []

    def __init__(self, entries):
        self.entries = entries

    def update_index_file(self, gitdir):
        with open(os.path.join(gitdir, "index"), "wb") as f:
            pickle.dump(self.entries, f)

    def __repr__(self):
        return '\n'.join(sorted(str(entry) for entry in self.entries))


def create_index(gitdir):
    with open(os.path.join(gitdir, "index"), "rb") as f:
        return GitIndex(pickle.load(f))


def exists(gitdir):
    return os.path.exists(os.path.join(gitdir, "index"))
