Test Task
=========

Please implement a program that synchronizes two folders: source and replica. The
program should maintain a full, identical copy of source folder at replica folder.
Solve the test task by writing a program in one of these programming languages::

    Python
    C/C++
    C#

- Synchronization must be one-way: after the synchronization content of the
  replica folder should be modified to exactly match content of the source
  folder;
- Synchronization should be performed periodically;
- File creation/copying/removal operations should be logged to a file and to the
  console output;
- Folder paths, synchronization interval and log file path should be provided
  using the command line arguments;
- It is undesirable to use third-party libraries that implement folder
  synchronization;

- It is allowed (and recommended) to use external libraries implementing other
  well-known algorithms. For example, there is no point in implementing yet
  another function that calculates MD5 if you need it for the task – it is
  perfectly acceptable to use a third-party (or built-in) library.


Solution
========

Python script (you can set it as executable and place it to your PATH).

Tested on linux, python version 3.12.4

::

    usage: sync_periodical.py [-h] [--debug] [--dry] [--follow-symlinks] [-b] [-i INTERVAL] [-f LOG_FILE] src dst

    Mirroring one directory to another directory.

    Script compares two directories (src and dst) and synchronizes them periodically.

    Warning: multiple nested directories can cause crash this script
             due to recursion limit (maximum depth of stack) in Python interpreter.
             If this happens, you can try to increase this limit (default 1000):
             sys.setrecursionlimit(limit)

    positional arguments:
      src                   path to existing source directory
      dst                   path to existing destination directory

    options:
      -h, --help            show this help message and exit
      --debug               logging debug messages
      --dry                 only compare directories, do not copy or delete files
      --follow-symlinks     follow symlinks to source when copy, if not set, default symlinks copy as link
      -b, --by-content      compare files by binary content
      -i INTERVAL, --interval INTERVAL
                            interval for periodical sync in seconds, default 0 (no periodical sync, run only once)
      -f LOG_FILE, --log-file LOG_FILE
                            path to log file, default empty (no log file)

    Press <Ctrl-C> to stop.

