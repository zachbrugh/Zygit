import os

import object
import pickle


class GitTreeLeaf:
    def __init__(self, mode, path, sha):
        self.mode = mode
        self.path = path
        self.sha = sha

    def __lt__(self, other):
        return self.sha < other.sha

    def __repr__(self):
        return (
            f"mode: {self.mode}\n"
            f"path: {self.path}\n"
            f"sha: {self.sha}\n"
        )


class GitTree(object.GitObject):
    fmt = b"tree"

    def deserialize(self, data):
        tree = pickle.loads(data)
        self.items = tree.items

    def serialize(self):
        return pickle.dumps(self)

    def __repr__(self):
        try:
            return '\n'.join(sorted(str(item) for item in self.items))
        except AttributeError:
            return ""



def create_tree(abs_dir_path, repository):
    tree = GitTree(repository)
    paths = os.listdir(abs_dir_path)
    
    leaves = []
    sha = ""
    for path in paths:
        if path == ".zygit":
            continue
        abs_path = os.path.join(abs_dir_path, path)
        if os.path.isdir(abs_path):
            sha = object.write(create_tree(abs_path, repository))
        else:
            with open(abs_path, "rb") as f:
                sha = object.hash(f, fmt=b"blob")
        mode = os.stat(abs_path).st_mode
        relpath = os.path.relpath(abs_path, repository.worktree)

        leaves.append(GitTreeLeaf(str(mode).encode(), relpath.encode(), sha))

    tree.items = sorted(leaves)
    return tree
