#!/Users/zacharybrugh/.pyenv/versions/pygit/bin/python

import argparse

from libzygit import (
    cmd_init,
    cmd_cat_file,
    cmd_hash_object,
    cmd_commit,
    cmd_log,
    cmd_ls_tree,
    cmd_checkout,
    cmd_show_ref,
    cmd_tag,
    cmd_rev_parse,
    cmd_ls_files,
    cmd_status,
    cmd_update_index,
    cmd_diff,
    cmd_add,
    cmd_write_tree,
)


def parse_args():
    parser = argparse.ArgumentParser(description="The stupid content tracker")
    subparsers = parser.add_subparsers(title="Commands", dest="command")
    subparsers.required = True

    # init
    argsp = subparsers.add_parser("init", help="Initialize a new, empty repository.")
    argsp.add_argument(
        "path",
        metavar="directory",
        nargs="?",
        default=".",
        help="Where to create the repository.",
    )


    # cat-file
    argsp = subparsers.add_parser(
        "cat-file", help="Provide content of repository objects"
    )
    argsp.add_argument(
        "type",
        metavar="type",
        choices=["blob", "commit", "tag", "tree"],
        help="Specify the type",
    )
    argsp.add_argument("object", metavar="object", help="The object to display")


    # hash-object
    argsp = subparsers.add_parser(
        "hash-object", help="Compute object ID and optionally creates a blob from a file"
    )
    argsp.add_argument(
        "-t",
        metavar="type",
        dest="type",
        choices=["blob", "commit", "tag", "tree"],
        default="blob",
        help="Specify the type",
    )
    argsp.add_argument(
        "-w",
        dest="write",
        action="store_true",
        help="Actually write the object into the database",
    )
    argsp.add_argument("path", help="Read object from <file>")


    # log
    argsp = subparsers.add_parser("log", help="Display history of a given commit.")
    argsp.add_argument("commit", default="HEAD", nargs="?", help="Commit to start at.")


    # ls-tree
    argsp = subparsers.add_parser("ls-tree", help="Pretty-print a tree object.")
    argsp.add_argument("object", help="The object to show.")


    # checkout
    argsp = subparsers.add_parser(
        "checkout", help="Checkout a commit inside of a directory."
    )
    argsp.add_argument("commit", help="The commit or tree to checkout.")
    argsp.add_argument("path", help="The EMPTY directory to checkout on.")


    # refs
    argsp = subparsers.add_parser("show-ref", help="List references.")


    # tag
    argsp = subparsers.add_parser("tag", help="List and create tags")
    argsp.add_argument(
        "-a",
        action="store_true",
        dest="create_tag_object",
        help="Whether to create a tag object",
    )
    argsp.add_argument("name", nargs="?", help="The new tag's name")
    argsp.add_argument(
        "object", default="HEAD", nargs="?", help="The object the new tag will point to"
    )


    # rev-parse
    argsp = subparsers.add_parser(
        "rev-parse", help="Parse revision (or other objects )identifiers"
    )
    argsp.add_argument(
        "--wyag-type",
        metavar="type",
        dest="type",
        choices=["blob", "commit", "tag", "tree"],
        default=None,
        help="Specify the expected type",
    )
    argsp.add_argument("name", help="The name to parse")


    # ls-files
    argsp = subparsers.add_parser("ls-files", help="List all the stage files")


    # status
    argsp = subparsers.add_parser("status", help="show status of working copy")


    # add
    argsp = subparsers.add_parser("add", help="Add file contents to the index")
    argsp.add_argument("paths", nargs="*", help="Add file contents to the index")
    argsp.add_argument(
        "-A",
        dest="all",
        action="store_true",
        help=(
            "Update the index not only where the working tree has a file matching <pathspec> "
            "but also where the index already has an entry."
        ),
    )


    # diff
    argsp = subparsers.add_parser(
        "diff", help="show diff of files changed between index and working copy"
    )   


    # commit
    argsp = subparsers.add_parser(
        "commit", help="commit current state of index to master branch"
    )
    argsp.add_argument(
        "-a",
        "--author",
        help='commit author in format "A U Thor <author@example.com>" '
        "(uses GIT_AUTHOR_NAME and GIT_AUTHOR_EMAIL environment "
        "variables by default)",
    )
    argsp.add_argument("-m", "--message", required=True, help="text of commit message")


    # write-tree
    argsp = subparsers.add_parser(
        "write-tree", help="Create a tree object from the current index"
    )


    # update-index
    argsp = subparsers.add_parser(
        "update-index", help="Modifies directory cache or the index ."
    )

    return parser.parse_args()


def main():
    args = parse_args()

    # COMMANDS FROM GUIDE
    if args.command == "init":
        cmd_init(args)
    elif args.command == "cat-file":
        cmd_cat_file(args)
    elif args.command == "hash-object":
        cmd_hash_object(args)
    elif args.command == "commit":
        cmd_commit(args)
    elif args.command == "log":
        cmd_log(args)
    elif args.command == "ls-tree":
        cmd_ls_tree(args)
    elif args.command == "checkout":
        cmd_checkout(args)
    elif args.command == "show-ref":
        cmd_show_ref(args)
    elif args.command == "tag":
        cmd_tag(args)
    elif args.command == "rev-parse":
        cmd_rev_parse(args)
    elif args.command == "ls-files":
        cmd_ls_files(args)

    # ADDED COMMANDS
    elif args.command == "status":
        cmd_status(args)
    elif args.command == "update-index":
        cmd_update_index(args)
    elif args.command == "diff":
        cmd_diff(args)
    elif args.command == "add":
        cmd_add(args)
    elif args.command == "write-tree":
        cmd_write_tree(args)


if __name__ == "__main__":
    main()
