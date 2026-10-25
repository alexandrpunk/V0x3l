import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from v0x3l.steps.final import DesktopStep


class _UI:
    def __init__(self, result=True):
        self.result = result
        self.calls = []

    def run_cmd(self, desc, *args, **kwargs):
        self.calls.append((desc, args, kwargs))
        return self.result


class _Runner:
    def __init__(self, result=True):
        self.ui = _UI(result)
        self.shell = None


class LazyVimTests(unittest.TestCase):
    def make_step(self, result=True):
        step = DesktopStep.__new__(DesktopStep)
        step.runner = _Runner(result)
        return step

    def test_rejects_missing_target_user_without_commands(self):
        step = self.make_step()
        with patch("v0x3l.steps.final.TARGET_USER", ""), patch(
            "v0x3l.steps.final.TARGET_HOME", "/root"
        ):
            self.assertFalse(step._install_zsh_lazyvim())
        self.assertEqual(step.runner.ui.calls, [])

    def test_rejects_root_home_without_commands(self):
        step = self.make_step()
        with patch("v0x3l.steps.final.TARGET_USER", "root"), patch(
            "v0x3l.steps.final.TARGET_HOME", "/root"
        ):
            self.assertFalse(step._install_zsh_lazyvim())
        self.assertEqual(step.runner.ui.calls, [])

    def test_skips_when_starter_already_installed(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            nvim = home / ".config" / "nvim"
            nvim.mkdir(parents=True)
            (nvim / "lua").mkdir()
            (nvim / "init.lua").write_text("installed")
            step = self.make_step()
            with patch("v0x3l.steps.final.TARGET_USER", "alice"), patch(
                "v0x3l.steps.final.TARGET_HOME", str(home)
            ):
                self.assertTrue(step._install_zsh_lazyvim())

            self.assertEqual(step.runner.ui.calls, [])
            self.assertTrue((nvim / "init.lua").exists())

    def test_backups_use_timestamp_and_preserve_previous_backup(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            nvim = home / ".config" / "nvim"
            nvim.mkdir(parents=True)
            (nvim / "init.lua").write_text("old")
            old_backup = home / ".config" / "nvim.bak"
            old_backup.mkdir()
            (old_backup / "keep").write_text("yes")

            step = self.make_step()
            with patch("v0x3l.steps.final.TARGET_USER", "alice"), patch(
                "v0x3l.steps.final.TARGET_HOME", str(home)
            ):
                self.assertTrue(step._install_zsh_lazyvim())

            self.assertTrue(old_backup.exists())
            backups = list((home / ".config").glob("nvim.bak.*"))
            self.assertEqual(len(backups), 1)
            self.assertTrue((backups[0] / "init.lua").exists())

    def test_backups_data_state_and_cache_directories(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            (home / ".config" / "nvim").mkdir(parents=True)
            (home / ".config" / "nvim" / "init.lua").write_text("old")
            for sub in ("share", "state"):
                d = home / ".local" / sub / "nvim"
                d.mkdir(parents=True)
                (d / "marker").write_text(sub)
            cache = home / ".cache" / "nvim"
            cache.mkdir(parents=True)
            (cache / "marker").write_text("cache")

            step = self.make_step()
            with patch("v0x3l.steps.final.TARGET_USER", "alice"), patch(
                "v0x3l.steps.final.TARGET_HOME", str(home)
            ):
                self.assertTrue(step._install_zsh_lazyvim())

            self.assertTrue(list((home / ".local" / "share").glob("nvim.bak.*")))
            self.assertTrue(list((home / ".local" / "state").glob("nvim.bak.*")))
            self.assertTrue(list((home / ".cache").glob("nvim.bak.*")))

    def test_clone_failure_stops_before_chown(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            step = self.make_step(result=False)
            with patch("v0x3l.steps.final.TARGET_USER", "alice"), patch(
                "v0x3l.steps.final.TARGET_HOME", str(home)
            ):
                self.assertFalse(step._install_zsh_lazyvim())

            self.assertFalse(any("chown lazyvim" in c[0]
                                 for c in step.runner.ui.calls))
            self.assertFalse(any("install lazyvim" in c[0]
                                 for c in step.runner.ui.calls
                                 if "chown" in c[0]))


if __name__ == "__main__":
    unittest.main()
