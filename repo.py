import configparser
import os

class GitRepository(object):
    """A git repository"""

    worktree = None
    gitdir = None
    conf = None

    def __init__(self, path, force=False):
        self.worktree = path
        self.zygitdir = os.path.join(path, ".zygit")

        if not (force or os.path.isdir(self.zygitdir)):
            raise Exception("Not a Git repository %s" % path)

        # Read configuration file in .zygit/config
        self.conf = configparser.ConfigParser()
        cf = file(self, "config")

        if cf and os.path.exists(cf):
            self.conf.read([cf])
        elif not force:
            raise Exception("Configuration file missing")

        if not force:
            vers = int(self.conf.get("core", "repositoryformatversion"))
            if vers != 0:
                raise Exception("Unsupported repositoryformatversion %s" % vers)


def find(path=".", required=True):
    path = os.path.realpath(path)

    if os.path.isdir(os.path.join(path, ".zygit")):
        return GitRepository(path)

    # If we haven't returned, recurse in parent, if w
    parent = os.path.realpath(os.path.join(path, ".."))

    if parent == path:
        # Bottom case
        # os.path.join("/", "..") == "/":
        # If parent==path, then path is root.
        if required:
            raise Exception("No git directory.")
        else:
            return None

    # Recursive case
    return find(parent, required)


def get_path(repo, *path):
    """Compute path under repo's gitdir."""
    return os.path.join(repo.zygitdir, *path)


def file(repo, *path, mkdir=False):
    """Same as path, but create dirname(*path) if absent.  For
    example, file(r, \"refs\", \"remotes\", \"origin\", \"HEAD\") will create
    .zygit/refs/remotes/origin."""

    if directory(repo, *path[:-1], mkdir=mkdir):
        return get_path(repo, *path)


def directory(repo, *path, mkdir=False):
    """Same as path, but mkdir *path if absent if mkdir."""

    path = get_path(repo, *path)

    if os.path.exists(path):
        if os.path.isdir(path):
            return path
        else:
            raise Exception("Not a directory %s" % path)

    if mkdir:
        os.makedirs(path)
        return path
    else:
        return None


def default_config():
    ret = configparser.ConfigParser()

    ret.add_section("core")
    ret.set("core", "repositoryformatversion", "0")
    ret.set("core", "filemode", "false")
    ret.set("core", "bare", "false")

    return ret
