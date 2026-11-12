import asyncio
import logging
import os
import signal


log = logging.getLogger("nuxiva.hardware.execution")


async def run_command(cmd, timeout=180, env=None):
    environment = dict(os.environ)
    environment.update(DEBIAN_FRONTEND="noninteractive", APT_LISTCHANGES_FRONTEND="none", LC_ALL="C")
    environment.update(env or {})
    process = None
    output = bytearray()

    async def collect():
        while chunk := await process.stdout.read(65536):
            output.extend(chunk)
            del output[:-1048576]
        return await process.wait()

    try:
        process = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT,
            env=environment, start_new_session=os.name != "nt",
        )
        code = await asyncio.wait_for(collect(), timeout)
        return code, output.decode("utf-8", "replace")
    except asyncio.CancelledError:
        raise
    except (OSError, asyncio.TimeoutError) as exc:
        log.error("Hardware command failed (%s): %s", cmd[0], exc)
        return 124 if isinstance(exc, asyncio.TimeoutError) else 1, str(exc)
    finally:
        if process is not None and process.returncode is None:
            try:
                if os.name != "nt":
                    os.killpg(process.pid, signal.SIGKILL)
                else:
                    process.kill()
            except ProcessLookupError:
                log.debug("Hardware process already stopped: %s", process.pid)
            await process.wait()
