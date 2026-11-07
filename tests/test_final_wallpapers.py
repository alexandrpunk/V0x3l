import tempfile
import tomllib
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from v0x3l.steps import final as F
from v0x3l.steps.final import DesktopStep


class _UI:
    def run_cmd(self, desc, *args, **kwargs):
        return True


class _Runner:
    def __init__(self):
        self.ui = _UI()
        self.shell = None


class WallpaperDeployTests(unittest.TestCase):
    """El deploy debe declarar el fondo en Noctalia, no en settings.toml.

    Regresion: la version anterior escribia ~/.config/noctalia/settings.toml
    (pisando la config del usuario), usaba `transition = "fade"` (string en vez
    de array), no dejaba fondo por defecto y delegaba la rotacion a un timer
    systemd que nunca se habilitaba.
    """

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)
        self.home = self.root / "home"
        self.home.mkdir()
        self.assets = self.root / "assets"
        self.assets.mkdir()
        # El primer nombre ordenado es el fondo por defecto.
        (self.assets / "b.png").write_bytes(b"png")
        (self.assets / "a.jpg").write_bytes(b"jpg")
        (self.assets / "notas.txt").write_text("no es imagen")

        self.wall_dest = self.home / "Pictures" / "walls"
        self.noctalia_dir = self.home / ".config" / "noctalia"
        self.cfg_path = self.noctalia_dir / "90-v0x3l.toml"

        self.run = MagicMock()
        self._patches = [
            patch.object(F, "TARGET_USER", "testuser"),
            patch.object(F, "TARGET_HOME", str(self.home)),
            patch.object(F, "WALLPAPERS_DIR", self.assets),
            patch.object(F, "WALLPAPER_DEST_DIR", "Pictures/walls"),
            patch.object(F, "NOCTALIA_WALLPAPER_CFG", "90-v0x3l.toml"),
            patch.object(F, "WALLPAPER_ROTATION_SECONDS", 600),
            patch.object(F.os, "geteuid", return_value=0),
            patch.object(F.subprocess, "run", self.run),
        ]
        for p in self._patches:
            p.start()
            self.addCleanup(p.stop)
        self.step = DesktopStep.__new__(DesktopStep)
        self.step.runner = _Runner()

    def _legacy_settings(self):
        return (
            "[wallpaper]\n"
            "enabled = true\n"
            'fill_mode = "crop"\n'
            f'directory = "{self.wall_dest}"\n'
            'transition = "fade"\n'
            "transition_duration = 1500\n"
            "transition_on_startup = false\n"
        )

    def _legacy_units(self):
        user_dir = self.home / ".config" / "systemd" / "user"
        wants = user_dir / "timers.target.wants"
        wants.mkdir(parents=True)
        timer = user_dir / "v0x3l-wallpaper.timer"
        service = user_dir / "v0x3l-wallpaper.service"
        link = wants / "v0x3l-wallpaper.timer"
        timer.write_text("[Timer]\nOnCalendar=*:0/15\n")
        service.write_text("[Service]\nExecStart=awww img\n")
        link.symlink_to(timer)
        return timer, service, link

    def test_declares_default_wallpaper_and_rotation_in_noctalia_fragment(self):
        self.assertTrue(self.step._deploy_wallpapers())

        data = tomllib.loads(self.cfg_path.read_text())
        wallpaper = data["wallpaper"]
        self.assertTrue(wallpaper["enabled"])
        self.assertEqual(wallpaper["directory"], str(self.wall_dest))
        # Noctalia espera un array de efectos, no un string.
        self.assertEqual(wallpaper["transition"], ["fade"])
        self.assertEqual(wallpaper["default"]["path"],
                         str(self.wall_dest / "a.jpg"))
        self.assertTrue((self.wall_dest / "a.jpg").exists())
        self.assertTrue((self.wall_dest / "b.png").exists())
        self.assertFalse((self.wall_dest / "notas.txt").exists())

        automation = wallpaper["automation"]
        self.assertTrue(automation["enabled"])
        self.assertEqual(automation["interval_seconds"], 600)
        self.assertEqual(automation["order"], "random")

    def test_does_not_write_settings_toml_nor_systemd_units(self):
        self.assertTrue(self.step._deploy_wallpapers())

        self.assertFalse((self.noctalia_dir / "settings.toml").exists())
        self.assertFalse((self.home / ".config" / "systemd").exists())

    def test_removes_legacy_settings_and_awww_timer(self):
        self.noctalia_dir.mkdir(parents=True)
        (self.noctalia_dir / "settings.toml").write_text(self._legacy_settings())
        timer, service, link = self._legacy_units()

        self.assertTrue(self.step._deploy_wallpapers())

        self.assertFalse((self.noctalia_dir / "settings.toml").exists(),
                         "el fragmento viejo pisaria [wallpaper] del nuevo")
        self.assertFalse(timer.exists())
        self.assertFalse(service.exists())
        self.assertFalse(link.exists())

    def test_keeps_foreign_settings_toml(self):
        self.noctalia_dir.mkdir(parents=True)
        foreign = self.noctalia_dir / "settings.toml"
        foreign.write_text("[bar]\nposition = \"bottom\"\n")

        self.assertTrue(self.step._deploy_wallpapers())

        self.assertEqual(foreign.read_text(),
                         "[bar]\nposition = \"bottom\"\n")

    def test_chowns_config_and_wallpapers_to_target_user(self):
        self.assertTrue(self.step._deploy_wallpapers())

        chowns = [c.args[0] for c in self.run.call_args_list
                  if c.args and c.args[0][:1] == ["chown"]]
        self.assertEqual(
            sorted(c[-1] for c in chowns),
            sorted([str(self.wall_dest), str(self.noctalia_dir)]))
        for call in chowns:
            self.assertEqual(call[2], "testuser:")

    def test_rejects_invalid_target_user(self):
        with patch.object(F, "TARGET_USER", "root"):
            self.assertFalse(self.step._deploy_wallpapers())
        self.assertFalse(self.cfg_path.exists())


if __name__ == "__main__":
    unittest.main()