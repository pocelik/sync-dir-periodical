#!/usr/bin/env python3

"""Mirroring one directory to another directory.

Script compares two directories (src and dst) and synchronizes them periodically.

Warning: multiple nested directories can cause crash this script
         due to recursion limit (maximum depth of stack) in Python interpreter.
         If this happens, you can try to increase this limit (default 1000):
         sys.setrecursionlimit(limit)
"""
from __future__ import annotations

import logging
from argparse import ArgumentParser, ArgumentTypeError, RawDescriptionHelpFormatter
from filecmp import cmpfiles, dircmp
from pathlib import Path
from shutil import rmtree, copytree, copy2
from sys import exit
from time import sleep


class DirCmpByContents(dircmp):
    """Modified dircmp class to compare two directories by contents (shallow=False) ... hack to python 3.10 - 3.12."""

    def phase3(self) -> None:  # Find out differences between common files
        """Modify phase3 to compare common files by contents (shallow=False) ... hack to python 3.10 - 3.12."""
        xx = cmpfiles(self.left, self.right, self.common_files, shallow=False)
        self.same_files, self.diff_files, self.funny_files = xx

    methodmap = dict(dircmp.methodmap, same_files=phase3, diff_files=phase3, funny_files=phase3)


DirCmp: type(dircmp) = dircmp  # DirCmp default compare files by shallow=True


def remove_inodes(dst_dir: str, inodes: list[str]) -> None:
    """Remove files and directories in inodes list from directory dst_dir."""
    for inode in inodes:
        try:
            path = Path(dst_dir, inode)
            if path.is_dir():
                logging.debug("--- Remove directory tree [%s]", str(path))
                rmtree(path, ignore_errors=True)
            else:
                logging.debug("--- Remove file '%s'", str(path))
                path.unlink(missing_ok=True)  # ignore nonexistent files (rm -f)
        except Exception:
            logging.exception("--- Problem in directory [%s] with removing inode: '%s'", dst_dir, inode)


def copy_inodes(src_dir: str, dst_dir: str, inodes: list[str], *, follow_symlinks: bool = False) -> None:
    """Copy files and directories in inodes list from directory src_dir to directory dst_dir."""
    for inode in inodes:
        try:
            path = Path(src_dir, inode)
            if path.is_dir():
                logging.debug("--- Copy directory tree [%s] to [%s]", str(path), dst_dir)
                copytree(path, Path(dst_dir, inode),
                         symlinks=not follow_symlinks,
                         ignore_dangling_symlinks=True,
                         dirs_exist_ok=True)
            else:
                logging.debug("--- Copy file '%s' to [%s]", str(path), dst_dir)
                copy2(path, Path(dst_dir, inode), follow_symlinks=follow_symlinks)
        except Exception:
            logging.exception("--- Problem with copying from directory [%s] to directory[%s] with inode: '%s'",
                              src_dir, dst_dir, inode)


def mirror_dircmp(dir_cmp: dircmp, *, follow_symlinks: bool = False, dry: bool = False) -> None:  # noqa: C901
    """Mirror src directory to dst directory."""
    if dir_cmp.funny_files:
        logging.warning("- Directory [%s] contains uncomparable files: %s", dir_cmp.left, str(dir_cmp.funny_files))
    if dir_cmp.common_funny:
        logging.warning("- Directory [%s] contains uncomparable inodes: %s", dir_cmp.left, str(dir_cmp.common_funny))

    if dir_cmp.right_only:  # files and directory only in dst directory to remove:
        logging.info("- From destination directory [%s] to remove inodes: %s", dir_cmp.right, str(dir_cmp.right_only))
        if not dry:
            remove_inodes(dir_cmp.right, dir_cmp.right_only)
    if dir_cmp.left_only:  # files and directory only in src directory to copy:
        logging.info("- From source directory [%s] to copy inodes: %s", dir_cmp.left, str(dir_cmp.left_only))
        if not dry:
            copy_inodes(dir_cmp.left, dir_cmp.right, dir_cmp.left_only, follow_symlinks=follow_symlinks)
    if dir_cmp.diff_files:  # different files to rewrite (copy) from src to dst:
        logging.info("- From source directory [%s] to rewrite (copy) files: %s", dir_cmp.left, str(dir_cmp.diff_files))
        if not dry:
            copy_inodes(dir_cmp.left, dir_cmp.right, dir_cmp.diff_files, follow_symlinks=follow_symlinks)

    if dir_cmp.subdirs:  # subdirectories to mirror from src to dst:
        logging.debug("- From source directory [%s] to mirror subdirectories: %s",
                      dir_cmp.left, str(dir_cmp.subdirs.keys()))
        for subdir in dir_cmp.subdirs.values():
            logging.debug("--- Mirror subdirectory [%s] to [%s]", subdir.left, subdir.right)
            mirror_dircmp(subdir, follow_symlinks=follow_symlinks, dry=dry)


def valid_dir(_path: str) -> str:
    """Test if path is existing directory."""
    if Path(_path).is_dir():
        return _path
    _msg = f"[{_path}] is not existing directory"
    raise ArgumentTypeError(_msg)


if __name__ == "__main__":

    # CLI:
    parser = ArgumentParser(
        prog=Path(__file__).name,
        formatter_class=RawDescriptionHelpFormatter,
        description=__doc__,
        epilog="Press <Ctrl-C> to stop.",
    )
    parser.add_argument("--debug", action="store_true", help="logging debug messages")
    parser.add_argument("--dry", action="store_true", help="only compare directories, do not copy or delete files")
    parser.add_argument("--follow-symlinks", action="store_true",
                        help="follow symlinks to source when copy, if not set, default symlinks copy as link")
    parser.add_argument("-b", "--by-content", action="store_true", help="compare files by binary content")
    parser.add_argument("-i", "--interval", default=0, type=lambda x: abs(int(x)),
                        help="interval for periodical sync in seconds, default 0 (no periodical sync, run only once)")
    parser.add_argument("-f", "--log-file", default="", help="path to log file, default empty (no log file)")
    parser.add_argument("src", type=valid_dir, help="path to existing source directory")
    parser.add_argument("dst", type=valid_dir, help="path to existing destination directory")

    args = parser.parse_args()

    # check for directory nesting:
    src = Path(args.src)
    dst = Path(args.dst)
    msg = "Argument error: "
    if src == dst:
        msg += f"src [{args.src}] and dst [{args.dst}] must be different!"
        raise SystemExit(msg)
    if src in dst.parents:
        msg += f"dst [{args.dst}] must be outside src [{args.src}], otherwise the copy will loop endlessly!"
        raise SystemExit(msg)
    if dst in src.parents:
        msg += f"src [{args.src}] must be outside dst [{args.dst}], otherwise src will be broken!"
        raise SystemExit(msg)

    # set logging:
    log_handlers = [logging.StreamHandler()]
    if args.log_file:
        log_handlers.append(logging.FileHandler(args.log_file))

    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=log_handlers,
    )

    # set comparison type:
    if args.by_content:
        DirCmp = DirCmpByContents
        logging.info("Compare files by binary content (shallow=False)")
    else:
        DirCmp = dircmp
        logging.info("Shallow compare (default - compare files only by name, size, mtime)")

    # mirror:
    if args.dry:
        logging.info("Only compare directories, do not copy or delete files:")
    else:
        logging.info("Start mirroring directories:")

    try:
        while True:
            logging.debug("Start compare.")
            _dir_cmp = DirCmp(args.src, args.dst, ignore=[])  # compare directories
            mirror_dircmp(_dir_cmp, follow_symlinks=args.follow_symlinks, dry=args.dry)
            if args.interval:
                logging.debug("Pause to next compare.")
                sleep(args.interval)
            else:
                logging.info("End of mirroring directories.")
                exit(0)
    except KeyboardInterrupt:
        logging.warning("End of mirroring directories by keyboard interrupt (Ctrl-C).")
        exit(0)
    except Exception:
        logging.exception("Exception when mirroring directories.")
        exit(1)
