import subprocess


class SubprocessFailed(Exception):
    pass


def run_subprocess(*args, context=None, **kwargs):
    try:
        return subprocess.run(*args, **kwargs)
    except subprocess.CalledProcessError as e:
        cli = subprocess.list2cmdline(e.cmd)
        raise SubprocessFailed(
            f"Command '{cli}' failed with error code {e.returncode} \n\t"
            f"context: {context} \n\tstdout: {e.stdout} \n\tstderr: {e.stderr}"
        ) from e

    except OSError as e:
        cli = subprocess.list2cmdline(args[0])
        raise SubprocessFailed(
            f"Failed to execute command '{cli}' \n\tcontext: {context}\n\t"
            f"Recieved error {e.__class__.__name__}: '{e}'"
        ) from e
