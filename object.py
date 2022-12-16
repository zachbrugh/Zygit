import hashlib
import os
import pickle
import re
import zlib

import repo

class GitObject(object):
    repository = None

    def __init__(self, repository, data=None):
        self.repository = repository

        if data != None:
            self.deserialize(data)

    def serialize(self):
        """This function MUST be implemented by subclasses.

        It must read the object's contents from self.data, a byte string, and do
        whatever it takes to convert it into a meaningful representation.  What exactly that means depend on each subclass."""
        raise Exception("Unimplemented!")

    def deserialize(self, data):
        raise Exception("Unimplemented!")


class GitBlob(GitObject):
    fmt = b"blob"

    def serialize(self):
        return self.blobdata

    def deserialize(self, data):
        self.blobdata = data

def create_blob(abs_path, repository):
    with open(abs_path, 'rb') as f:
        data = f.read()
        return GitBlob(repository, data)

class GitCommit(GitObject):
    fmt = b"commit"

    def deserialize(self, data):
        data_from_commit = pickle.loads(data)
        self.parent = data_from_commit.parent
        self.author = data_from_commit.author
        self.message = data_from_commit.message
        self.tree = data_from_commit.tree


    def serialize(self):
        return pickle.dumps(self)

    def __repr__(self):
        return (
            f"parent: {self.parent}\n"
            f"author: {self.author}\n"
            f"message: {self.message}\n"
            f"tree: {self.tree}\n"
        )


class GitTag(GitCommit):
    fmt = b"tag"


def ref_create(repository, ref_name, sha):
    with open(repo.file(repository, "refs/" + ref_name), "w") as fp:
        fp.write(sha + "\n")


def ref_resolve(repository, ref):
    with open(repo.file(repository, ref), "r") as fp:
        data = fp.read()[:-1]
        # Drop final \n ^^^^^
    if data.startswith("ref: "):
        return ref_resolve(repository, data[5:])
    else:
        return data


def read(repository, sha):
    """Read object id from Git repositorysitory repository.  Return a
    GitObject whose exact type depends on the object."""
    from tree import GitTree

    path = repo.file(repository, "objects", sha[0:2], sha[2:])

    with open(path, "rb") as f:
        raw = zlib.decompress(f.read())

        # Read object type
        x = raw.find(b" ")
        fmt = raw[0:x]

        # Read and validate object size
        y = raw.find(b"\x00", x)
        size = int(raw[x:y].decode("ascii"))
        if size != len(raw) - y - 1:
            raise Exception("Malformed object {0}: bad length".format(sha))

        # Pick constructor
        if fmt == b"commit":
            c = GitCommit
        elif fmt == b"tree":
            c = GitTree
        elif fmt == b"tag":
            c = GitTag
        elif fmt == b"blob":
            c = GitBlob
        else:
            raise Exception(
                "Unknown type {0} for object {1}".format(fmt.decode("ascii"), sha)
            )

        # Call constructor and return object
        return c(repository, raw[y + 1 :])


def write(obj, actually_write=True):
    # Serialize object data
    data = obj.serialize()
    # Add header
    result = obj.fmt + b" " + str(len(data)).encode() + b"\x00" + data
    # Compute hash
    sha = hashlib.sha1(result).hexdigest()

    if actually_write:
        # Compute path
        path = repo.file(
            obj.repository, "objects", sha[0:2], sha[2:], mkdir=actually_write
        )

        with open(path, "wb") as f:
            # Compress and write
            f.write(zlib.compress(result))

    return sha


def hash(fd, fmt, repository=None):
    data = fd.read()

    # Choose constructor depending on
    # object type found in header.
    if fmt == b"commit":
        obj = GitCommit(repository, data)
    elif fmt == b"tag":
        obj = GitTag(repository, data)
    elif fmt == b"blob":
        obj = GitBlob(repository, data)
    else:
        raise Exception("Unknown type %s!" % fmt)

    return write(obj, repository)


def obj_resolve(repository, name):
    """Resolve name to an object hash in repository.

    This function is aware of:

     - the HEAD literal
     - short and long hashes
     - tags
     - branches
     - remote branches"""
    candidates = list()
    hashRE = re.compile(r"^[0-9A-Fa-f]{4,40}$")

    # Empty string?  Abort.
    if not name.strip():
        return None

    # Head is nonambiguous
    if name == "HEAD":
        return [ref_resolve(repository, "HEAD")]

    if hashRE.match(name):
        if len(name) == 40:
            # This is a complete hash
            return [name.lower()]

        # This is a small hash 4 seems to be the minimal length
        # for git to consider something a short hash.
        # This limit is documented in man git-rev-parse
        name = name.lower()
        prefix = name[0:2]
        path = repo.dir(repository, "objects", prefix, mkdir=False)
        if path:
            rem = name[2:]
            for f in os.listdir(path):
                if f.startswith(rem):
                    candidates.append(prefix + f)

    return candidates


def find(repository, name, fmt=None, follow=True):
    sha = obj_resolve(repository, name)

    if not sha:
        raise Exception("No such reference {0}.".format(name))

    if len(sha) > 1:
        raise Exception(
            "Ambiguous reference {0}: Candidates are:\n - {1}.".format(
                name, "\n - ".join(sha)
            )
        )

    sha = sha[0]

    if not fmt:
        return sha

    while True:
        obj = read(repository, sha)

        if obj.fmt == fmt:
            return sha

        if not follow:
            return None

        # Follow tags
        if obj.fmt == b"tag":
            sha = obj.kvlm[b"object"].decode("ascii")
        elif obj.fmt == b"commit" and fmt == b"tree":
            sha = obj.kvlm[b"tree"].decode("ascii")
        else:
            return None
