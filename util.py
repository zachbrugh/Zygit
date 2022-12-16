import os


def get_all_paths(worktree, start_dir=None):
    file_paths = set()
    dir_paths = set()

    for root, dirs, files in os.walk(start_dir or worktree):
        if ".zygit" in root:
            continue
        for file in files:
            relroot = os.path.relpath(root, worktree)
            file_paths.add(os.path.join(relroot, file))
        for dir in dirs:
            if dir != ".zygit":
                relroot = os.path.relpath(root, worktree)
                dir_paths.add(os.path.join(relroot, dir))

    return file_paths, dir_paths
