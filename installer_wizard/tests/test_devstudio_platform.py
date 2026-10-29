import unittest
from pathlib import Path
from unittest.mock import patch

from features.devstudio import runner
from features.devstudio.workspace import DevError


class DevstudioPlatformTest(unittest.IsolatedAsyncioTestCase):
    async def test_missing_resource_refuses_execution_before_subprocess(self):
        with patch.object(runner, "resource", None), \
             patch.object(runner, "command", return_value=["python3", "-I", "app.py"]), \
             patch.object(runner.sys, "platform", "linux"), \
             patch.object(runner.shutil, "which", return_value="/usr/bin/unshare"), \
             patch.object(runner.asyncio, "create_subprocess_exec") as spawn:
            with self.assertRaisesRegex(DevError, "isolamento"):
                await runner.run("python_run", Path("."), "app.py")
            spawn.assert_not_called()
            with self.assertRaises(DevError):
                runner._limit()
