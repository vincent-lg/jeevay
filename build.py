import argparse
from itertools import cycle
from subprocess import Popen, PIPE
import sys
import time
import shutil

def call(
    command: list[str],
    progress_message: str,
    should_exit: bool = True,
    force_after: int = None,
    ignore_non_zero: bool = False,
    progress_bar: bool = True,
):
    """Call a process, displaying a progress message.

    The output from the process is shown only in case of error.

    Args:
        command (list of str): the command to call.
        progress_message (str): the message to display when the task is in progress.
        should_exit (bool): exit the program if the task fails.
        force_after (int, opt): if set, interact with the process (will block).
        ignore_non_zero (bool): if set, will not display errors.
        progress_bar (bool): display a progress bar.

    """
    display_bar = cycle(r"-\|/")
    stdout, stderr = (None, None)
    print(progress_message + " ", end="")
    if progress_bar:
        print(".", end="")
    sys.stdout.flush()
    begin = time.time()

    process = Popen(
        command, shell=False, stdout=PIPE, stderr=PIPE, encoding="utf-8"
    )
    while (code := process.poll()) is None:
        if progress_bar:
            print(f"\b{next(display_bar)}", end="")
            sys.stdout.flush()

        try:
            time.sleep(1)
        except KeyboardInterrupt:
            process.terminate()
            break
        else:
            if (
                force_after is not None
                and (time.time() - begin) > force_after
            ):
                break

    end = time.time()
    if code == 0:
        if progress_bar:
            print("\b", end="")
        print(f"Done in {round(end - begin, 3)}s")
    else:
        stdout, stderr = process.communicate()
        if ignore_non_zero:
            print(
                f"Done but received code {process.returncode} in {round(end - begin, 3)}s"
            )
        else:
            print(f"FAILED with code={process.returncode}")
            if stdout:
                print(stdout)
            if stderr:
                print(stderr)

            if should_exit:
                print("Exiting.")
                sys.exit(1)


parser = argparse.ArgumentParser()
parser.add_argument(
    "--no-progress-bar",
    default=False,
    action="store_true",
    help="do not display dynamic progress bars",
)
parser.add_argument(
    "--force-console",
    default=False,
    action="store_true",
    help="force to build with a console for debug",
)
args = parser.parse_args()
progress_bar = not args.no_progress_bar
command = ["uv", "sync"]
call(
    command,
    "Installing dependencies with uv...",
    force_after=30,
    ignore_non_zero=False,
    progress_bar=progress_bar,
)

command = [
    "uv",
    "run",
    "-m",
    "nuitka",
]

if not args.force_console:
    command.append("--windows-console-mode=disable")

command.extend(
    [
        "--standalone",
        "--remove-output",
        "--mingw64",
        "--lto=yes",
        "--python-flag=no_docstrings",
        "--assume-yes-for-downloads",
        "jeevay",
    ]
)

call(
    command,
    "Building with Nuitka...",
    progress_bar=progress_bar,
)

print("Copying directories... ", end="")
sys.stdout.flush()
shutil.copytree("accessible_output3", "jeevay.dist/accessible_output3")
print("Done")
