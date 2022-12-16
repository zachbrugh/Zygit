import os
import os.path
import sys
from pathlib import Path
import index
import object
import repo
import tree
import util


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
    if isinstance(obj, object.GitBlob):
        sys.stdout.buffer.write(obj.serialize())
    else:
        print(obj)


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


def cmd_status(args):
    """Show status of working copy."""
    repository = repo.find()
    file_paths, dir_paths = util.get_all_paths(repository.worktree)

    index_entries = []
    index_paths = set()
    if index.exists(repository.gitdir):
        curr_index = index.create_index(repository.gitdir)
        index_entries = curr_index.entries
        index_paths = {index_entry.name for index_entry in index_entries}
    change_check_index_entries = [
        entry for entry in index_entries if entry.name in (file_paths | dir_paths)
    ]

    def compute_hash(path):
        abs_path = os.path.join(repository.worktree, path)
        if path in file_paths:
            return object.hash(open(abs_path, 'rb'), b"blob")
        else:
            return object.write(tree.create_tree(
                    abs_path, repository
                )
            )

    new_paths = (file_paths | dir_paths) - index_paths
    deleted_paths = index_paths - (file_paths | dir_paths)
    changed_paths = {
        entry.name
        for entry in change_check_index_entries
        if compute_hash(entry.name) != entry.object_hash
    }

    if new_paths:
        print("Untracked files: \n", "\n".join(sorted(new_paths)))
    if deleted_paths:
        print("\nDeleted files: \n", "\n".join(sorted(deleted_paths)))
    if changed_paths:
        print("\nChanged files: \n", "\n".join(sorted(changed_paths)))

    if not new_paths and not deleted_paths and not changed_paths:
        print("No changes in your working directory")


def cmd_add(args):
    repository = repo.find()
    file_paths, dir_paths = util.get_all_paths(repository.worktree)

    index_objects = []
    for path in file_paths | dir_paths:
        abs_path = os.path.join(repository.worktree, path)
        m_time = os.path.getmtime(abs_path)
        c_time = os.path.getctime(abs_path)
        user_id = Path(abs_path).owner()
        size = os.path.getsize(abs_path)
        if path in dir_paths:
            path_hash = object.write(tree.create_tree(abs_path, repository), actually_write=True)
        else:
            path_hash = object.write(object.create_blob(abs_path, repository), actually_write=True)

        index_objects.append(
            index.GitIndexEntry(c_time, m_time, user_id, size, path_hash, path)
        )
    index.GitIndex(index_objects).update_index_file(repository.gitdir)


def cmd_commit(args):
    repository = repo.find()
    new_tree = tree.create_tree(repository.worktree, repository)
    trees_hash = object.write(new_tree)

    new_commit = object.GitCommit(repository)

    new_commit.parent = args.parent
    new_commit.author = args.author
    new_commit.message = args.message
    new_commit.tree = trees_hash

    print("committed succesfully with hash", object.write(new_commit, actually_write=True))
