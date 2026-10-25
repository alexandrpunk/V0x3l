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


    def test_omp_binary_prefers_local_bin_then_bun(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            self.assertEqual(DesktopStep._omp_binary(str(home)), "")

            bun = home / ".bun" / "bin"
            bun.mkdir(parents=True)
            (bun / "omp").write_text("x")
            (bun / "omp").chmod(0o755)
            self.assertTrue(DesktopStep._omp_binary(str(home)).endswith(
                ".bun/bin/omp"))

            local = home / ".local" / "bin"
            local.mkdir(parents=True)
            (local / "omp").write_text("x")
            (local / "omp").chmod(0o755)
            self.assertTrue(DesktopStep._omp_binary(str(home)).endswith(
                ".local/bin/omp"))

    def test_omp_binary_ignores_non_executable(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            local = home / ".local" / "bin"
            local.mkdir(parents=True)
            (local / "omp").write_text("x")
            (local / "omp").chmod(0o644)
            self.assertEqual(DesktopStep._omp_binary(str(home)), "")

class OmpHarnessTests(unittest.TestCase):
    def make_step(self):
        step = DesktopStep.__new__(DesktopStep)
        step.runner = _Runner()
        return step

    def _make_repo(self, root):
        src = root / "repo"
        (src / "scripts").mkdir(parents=True)
        (src / "agents").mkdir()
        (src / "skills" / "demo").mkdir(parents=True)
        (src / ".git").mkdir()
        (src / "config.yml").write_text("model: omniroute/auto/best-coding\n")
        (src / "models.yml").write_text("baseUrl: https://api.example.com/v1\n")
        (src / "scripts" / "setup.sh").write_text("#!/bin/sh\n")
        (src / "agents" / "planner.md").write_text("planner\n")
        (src / "skills" / "demo" / "SKILL.md").write_text("skill\n")
        (src / ".git" / "HEAD").write_text("ref\n")
        return src

    def test_deploys_harness_and_skips_git_metadata(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            src = self._make_repo(root)
            agent = root / "home" / ".omp" / "agent"

            step = self.make_step()
            self.assertTrue(step._deploy_omp_harness(str(src), str(agent)))

            self.assertTrue((agent / "config.yml").exists())
            self.assertTrue((agent / "scripts" / "setup.sh").exists())
            self.assertTrue((agent / "skills" / "demo" / "SKILL.md").exists())
            self.assertFalse((agent / ".git").exists())

    def test_preserves_existing_local_config_and_env(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            src = self._make_repo(root)
            agent = root / "agent"
            agent.mkdir()
            (agent / "models.yml").write_text("baseUrl: https://mine/v1\n")
            (agent / ".env").write_text("OMNIROUTE_API_KEY=secret\n")

            step = self.make_step()
            self.assertTrue(step._deploy_omp_harness(str(src), str(agent)))

            self.assertEqual((agent / "models.yml").read_text(),
                             "baseUrl: https://mine/v1\n")
            self.assertEqual((agent / ".env").read_text(),
                             "OMNIROUTE_API_KEY=secret\n")
            self.assertEqual((agent / "config.yml").read_text(),
                             "model: omniroute/auto/best-coding\n")

    def test_refreshes_repo_managed_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            src = self._make_repo(root)
            agent = root / "agent"
            (agent / "agents").mkdir(parents=True)
            (agent / "agents" / "planner.md").write_text("stale\n")

            step = self.make_step()
            self.assertTrue(step._deploy_omp_harness(str(src), str(agent)))
            self.assertEqual((agent / "agents" / "planner.md").read_text(),
                             "planner\n")

    def test_missing_source_is_reported(self):
        step = self.make_step()
        self.assertFalse(step._deploy_omp_harness("/nonexistent/omp", "/tmp/x"))


if __name__ == "__main__":
    unittest.main()
