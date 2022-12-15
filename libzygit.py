import argparse
import collections
import difflib
import os
import sys
import time, difflib, operator
import logging
import pathlib

import index
import util
import object
import repo

_log = logging.getLogger("zyag commands")


def repo_create(path):
    """Create a new repository at path."""

    repository = repo.GitRepository(path, True)

    # First, we make sure the path either doesn't exist or is an
    # empty dir.

    if os.path.exists(repository.worktree):
        if not os.path.isdir(repository.worktree):
            raise Exception("%s is not a directory!" % path)
        if os.listdir(repository.worktree):
            raise Exception("%s is not empty!" % path)
    else:
        os.makedirs(repository.worktree)

    assert repo.directory(repository, "branches", mkdir=True)
    assert repo.directory(repository, "objects", mkdir=True)
    assert repo.directory(repository, "refs", "tags", mkdir=True)
    assert repo.directory(repository, "refs", "heads", mkdir=True)

    # .zygit/description
    with open(repo.file(repository, "description"), "w") as f:
        f.write(
            "Unnamed repository; edit this file 'description' to name the repository.\n"
        )

    # .zygit/HEAD
    with open(repo.file(repository, "HEAD"), "w") as f:
        f.write("ref: refs/heads/master\n")

    with open(repo.file(repository, "config"), "w") as f:
        config = repo.default_config()
        config.write(f)

    return repository


def cmd_init(args):
    repo_create(args.path)


def cat_file(repository, obj, fmt=None):
    obj = object.read(repository, object.find(repository, obj, fmt=fmt))
    sys.stdout.buffer.write(obj.serialize())


def cmd_cat_file(args):
    repository = repo.find()
    cat_file(repository, args.object, fmt=args.type.encode())


def cmd_hash_object(args):
    if args.write:
        repository = repo.GitRepository(".")
    else:
        repository = None

    with open(args.path, "rb") as fd:
        sha = object.hash(fd, args.type.encode(), repository)
        print(sha)


def log_graphviz(repository, sha, seen):

    if sha in seen:
        return
    seen.add(sha)

    commit = object.read(repository, sha)
    assert commit.fmt == b"commit"

    if not b"parent" in commit.kvlm.keys():
        # Base case: the initial commit.
        return

    parents = commit.kvlm[b"parent"]

    if type(parents) != list:
        parents = [parents]

    for p in parents:
        p = p.decode("ascii")
        print("c_{0} -> c_{1};".format(sha, p))
        log_graphviz(repository, p, seen)


def cmd_log(args):
    repository = repo.find()

    print("digraph wyaglog{")
    log_graphviz(repository, object.find(repository, args.commit), set())
    print("}")


def cmd_ls_tree(args):
    repository = repo.find()
    obj = object.read(repository, object.find(repository, args.object, fmt=b"tree"))

    for item in obj.items:
        print(
            "{0} {1} {2}\t{3}".format(
                "0" * (6 - len(item.mode)) + item.mode.decode("ascii"),
                # Git's ls-tree displays the type
                # of the object pointed to.  We can do that too :)
                object.read(repository, item.sha).fmt.decode("ascii"),
                item.sha,
                item.path.decode("ascii"),
            )
        )


def tree_checkout(repository, tree, path):
    for item in tree.items:
        obj = object.read(repository, item.sha)
        dest = os.path.join(path, item.path)

        if obj.fmt == b"tree":
            os.mkdir(dest)
            tree_checkout(repository, obj, dest)
        elif obj.fmt == b"blob":
            with open(dest, "wb") as f:
                f.write(obj.blobdata)


def cmd_checkout(args):
    repository = repo.find()

    obj = object.read(repository, object.find(repository, args.commit))

    # If the object is a commit, we grab its tree
    if obj.fmt == b"commit":
        obj = object.read(repository, obj.kvlm[b"tree"].decode("ascii"))

    # Verify that path is an empty directory
    if os.path.exists(args.path):
        if not os.path.isdir(args.path):
            raise Exception("Not a directory {0}!".format(args.path))
        if os.listdir(args.path):
            raise Exception("Not empty {0}!".format(args.path))
    else:
        os.makedirs(args.path)

    tree_checkout(repository, obj, os.path.realpath(args.path).encode())


def ref_list(repository, path=None):
    if not path:
        path = repo.directory(repository, "refs")
    ret = collections.OrderedDict()
    # Git shows refs sorted.  To do the same, we use
    # an OrderedDict and sort the output of listdir
    for f in sorted(os.listdir(path)):
        can = os.path.join(path, f)
        if os.path.isdir(can):
            ret[f] = ref_list(repository, can)
        else:
            ret[f] = object.ref_resolve(repository, can)

    return ret


def show_ref(repository, refs, with_hash=True, prefix=""):
    for k, v in refs.items():
        if type(v) == str:
            print(
                "{0}{1}{2}".format(
                    v + " " if with_hash else "", prefix + "/" if prefix else "", k
                )
            )
        else:
            show_ref(
                repository,
                v,
                with_hash=with_hash,
                prefix="{0}{1}{2}".format(prefix, "/" if prefix else "", k),
            )


def cmd_show_ref(args):
    repository = repo.find()
    refs = ref_list(repository)
    show_ref(repository, refs, prefix="refs")


def tag_create(repository, name, reference, type):
    # get the GitObject from the object reference
    sha = object.find(repository, reference)

    if type == "object":
        # create tag object (commit)
        tag = object.GitTag(repository)
        tag.kvlm = collections.OrderedDict()
        tag.kvlm[b"object"] = sha.encode()
        tag.kvlm[b"type"] = b"commit"
        tag.kvlm[b"tag"] = name.encode()
        # Feel free to let the user give their name!
        tag.kvlm[b"tagger"] = b"Wyag <wyag@example.com>"
        # …and a tag message!
        tag.kvlm[
            b""
        ] = b"A tag generated by wyag, which won't let you customize the message!"
        tag_sha = object.write(tag, repository)
        # create reference
        object.ref_create(repository, "tags/" + name, tag_sha)
    else:
        # create lightweight tag (ref)
        object.ref_create(repository, "tags/" + name, sha)


def cmd_tag(args):
    repository = repo.find()

    if args.name:
        tag_create(
            repository,
            args.name,
            args.object,
            type="object" if args.create_tag_object else "ref",
        )
    else:
        refs = ref_list(repository)
        show_ref(repository, refs["tags"], with_hash=False)


def cmd_rev_parse(args):
    if args.type:
        fmt = args.type.encode()
    else:
        fmt = None

    repository = repo.find()

    print(object.find(repository, args.name, fmt, follow=True))


def cmd_ls_files(args):
    repository = repo.find()
    for e in index.GitIndex(os.path.join(repository.zygitdir, "index")).entries:
        print("{0}".format(e.name.decode("utf8")))


def cmd_status(args):
    """Show status of working copy."""

    paths = set()
    for root, dirs, files in os.walk("."):
        dirs[:] = [d for d in dirs if d != ".zygit"]
        for file in files:
            path = os.path.join(root, file)
            path = path.replace("\\", "/")
            if path.startswith("./"):
                path = path[2:]
            paths.add(path)
    entries_by_path = {e.path: e for e in index.read_index()}
    entry_paths = set(entries_by_path)
    changed = {
        p
        for p in (paths & entry_paths)
        if object.hash(util.read_file(p), "blob", write=False)
        != entries_by_path[p].sha1.hex()
    }

    new = paths - entry_paths
    deleted = entry_paths - paths

    changed = sorted(changed)
    new = sorted(new)
    deleted = sorted(deleted)
    if changed:
        print("changed files:")
        for path in changed:
            print("   ", path)
    if new:
        print("new files:")
        for path in new:
            print("   ", path)
    if deleted:
        print("deleted files:")
        for path in deleted:
            print("   ", path)


def add_path(path: pathlib.Path) -> index.GitIndexEntry:

    sha1 = object.hash(path, write=True, fmt="blob")
    st = path.stat()
    flags = len(str(path).encode())
    assert flags < (1 << 12)
    entry = index.GitIndexEntry(
        int(st.st_ctime),
        st.st_ctime_ns % 1000000000,
        int(st.st_mtime),
        st.st_mtime_ns % 1000000000,
        st.st_dev,
        st.st_ino,
        st.st_mode,
        st.st_uid,
        st.st_gid,
        st.st_size,
        bytes.fromhex(sha1),
        flags,
        str(path),
    )
    return entry


def add_all(paths) -> None:
    all_entries = index.read_index()
    entries = [e for e in all_entries if e.name not in paths]
    for path in paths:
        _log.debug(f"add_all - path {path}")
        if path.is_dir():
            if not path.parts:
                _log.debug(f"Path {path} appears to be cwd")
                continue
            if not str(path.parts[-1]).startswith("."):
                for subpath in path.rglob("*"):
                    _log.debug(f"add_all subpath: {subpath}")
                    if not subpath.is_dir():
                        entries.append(add_path(subpath))
            else:
                _log.debug(
                    f"not adding {path} because {path.parts[-1]} starts with '.'"
                )
        else:
            _log.debug(f"add_all path not_dir: {path}")
            entries.append(add_path(path))
    entries.sort(key=operator.attrgetter("name"))
    # git update-index
    index.write_index(entries)


def cmd_add(args: argparse.Namespace) -> None:
    if args.all:
        repository = repo.find()
        assert repository is not None
        all_paths = [repo.get_path(repository, ".").parent]
    else:
        all_paths = [pathlib.Path(path) for path in args.paths]
    add_all(all_paths)


def cmd_update_index(args: argparse.Namespace) -> None:
    if args.add:
        cmd_add(args)


def cmd_diff(args):
    """Show diff of files changed (between index and working copy)."""
    paths = set()
    for root, dirs, files in os.walk("."):
        dirs[:] = [d for d in dirs if d != ".zygit"]
        for file in files:
            path = os.path.join(root, file)
            path = path.replace("\\", "/")
            if path.startswith("./"):
                path = path[2:]
            paths.add(path)
    entries_by_path = {e.path: e for e in index.read_index()}
    entry_paths = set(entries_by_path)
    changed = {
        p
        for p in (paths & entry_paths)
        if object.hash(util.read_file(p), "blob", write=False)
        != entries_by_path[p].sha1.hex()
    }

    new = paths - entry_paths
    deleted = entry_paths - paths

    print("hi")
    changed = sorted(changed)

    entries_by_path = {e.path: e for e in index.read_index()}

    print("hi")
    print(changed)
    for i, path in enumerate(changed):
        print("hi")
        sha1 = entries_by_path[path].sha1.hex()
        obj_type, data = object.read(sha1)
        assert obj_type == "blob"
        index_lines = data.decode().splitlines()
        working_lines = util.read_file(path).decode().splitlines()
        diff_lines = difflib.unified_diff(
            index_lines,
            working_lines,
            "{} (index)".format(path),
            "{} (working copy)".format(path),
            lineterm="",
        )
        for line in diff_lines:
            print(line)
        if i < len(changed) - 1:
            print("-" * 70)
        print("hi")


def cmd_write_tree(args):
    tree_entries = []
    for entry in index.read_index():
        assert (
            "/" not in entry.path
        ), "currently only supports a single, top-level directory"
        mode_path = "{:o} {}".format(entry.mode, entry.path).encode()
        tree_entry = mode_path + b"\x00" + entry.sha1
        tree_entries.append(tree_entry)
    temp = object.hash(b"".join(tree_entries), "tree")
    print(temp)
    return temp


def get_local_master_hash():
    """Get current commit hash (SHA-1 string) of local master branch."""
    master_path = os.path.join(".zygit", "refs", "heads", "master")
    try:
        return util.read_file(master_path).decode().strip()
    except FileNotFoundError:
        return None


def cmd_commit(message, author=None):
    """Commit the current state of the index to master with given message.
    Return hash of commit object.
    """
    tree = cmd_write_tree(author)
    parent = get_local_master_hash()
    if author is None:
        author = "{} <{}>".format(
            os.environ["GIT_AUTHOR_NAME"], os.environ["GIT_AUTHOR_EMAIL"]
        )
    timestamp = int(time.mktime(time.localtime()))
    utc_offset = -time.timezone
    author_time = "{} {}{:02}{:02}".format(
        timestamp,
        "+" if utc_offset > 0 else "-",
        abs(utc_offset) // 3600,
        (abs(utc_offset) // 60) % 60,
    )
    lines = ["tree " + tree]
    if parent:
        lines.append("parent " + parent)
    lines.append("author {} {}".format(author, author_time))
    lines.append("committer {} {}".format(author, author_time))
    lines.append("")
    lines.append(message)
    lines.append("")
    data = "\n".join(lines).encode()
    sha1 = object.hash(data, "commit")
    master_path = os.path.join(".zygit", "refs", "heads", "master")
    util.write_file(master_path, (sha1 + "\n").encode())
    print("committed to master: {:7}".format(sha1))
    return sha1

