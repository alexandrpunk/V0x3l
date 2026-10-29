# Paso 5: Entorno — dotfiles + Oh My Zsh + LazyVim + harness omp
# (Noctalia/Umbriel/ly se instalan en Step 2: packages.py;
# dotfiles/zsh/lazyvim/omp al final para evitar conflictos con instaladores
# que tocan ~/.config y ~/.local)

import os
import shutil
import tempfile
import subprocess
from v0x3l.steps.base import BaseStep
from v0x3l.config import (TARGET_USER, TARGET_HOME,
                          DOTFILES_DIR, DOTFILES_MAP, OMP_HARNESS_REPO)
from v0x3l.shell import log

OMP_HARNESS_KEEP = ("config.yml", "models.yml", ".env")

# Plugin Noctalia: Optimus GPU Manager (Luau)
OPTIMUS_PLUGIN_FILES = {
    "plugin.toml": '''plugin_api = 37
name = "Optimus GPU Manager"
author = "v0x3l"
version = "1.0.0"
description = "Gestión NVIDIA Optimus desde Noctalia (Intel iGPU / NVIDIA dGPU)"

[settings]
startup_mode = { type = "enum", options = ["intel", "nvidia", "auto"], default = "intel" }
show_vram_usage = { type = "bool", default = true }
show_gpu_temp = { type = "bool", default = true }
notify_on_switch = { type = "bool", default = true }

[[entry]]
name = "bar"
file = "entries/bar.lua"
type = "bar_widget"

[[entry]]
name = "panel"
file = "entries/panel.lua"
type = "panel"

[[entry]]
name = "service"
file = "entries/service.lua"
type = "service"
''',
    "entries/bar.lua": '''-- Widget barra: GPU actual + VRAM/Temp (NVIDIA)
local widget = require("widget")
local ui = require("ui")

local current_gpu = "intel"
local vram_used, vram_total, gpu_temp = 0, 0, 0
local last_update = 0
local driver_version = "desconocido"

local function parse_optimus_status()
    noctalia.runAsync({ "optimus-manager", "--status" }, function(result)
        if result.exitCode == 0 and result.stdout then
            if result.stdout:match("nvidia") then
                current_gpu = "nvidia"
            elseif result.stdout:match("intel") then
                current_gpu = "intel"
            end
        end
    end)
end

local function parse_nvidia_smi()
    if current_gpu ~= "nvidia" then return end
    noctalia.runAsync({ "nvidia-smi", "--query-gpu=memory.used,memory.total,temperature.gpu,driver_version", "--format=csv,noheader,nounits" }, function(result)
        if result.exitCode == 0 and result.stdout then
            local u, t, tmp, drv = result.stdout:match("(%d+)%s*,%s*(%d+)%s*,%s*(%d+)%s*,%s*([%d.]+)")
            if u then
                vram_used, vram_total, gpu_temp, driver_version = tonumber(u), tonumber(t), tonumber(tmp), drv
            end
        end
    end)
end

noctalia.setUpdateInterval(1000)

function update()
    local now = noctalia.nowMs()
    if now - last_update > 5000 then
        last_update = now
        parse_optimus_status()
        parse_nvidia_smi()
    end
end

function build()
    local show_vram = noctalia.getConfig("show_vram_usage")
    local show_temp = noctalia.getConfig("show_gpu_temp")

    local icon = current_gpu == "nvidia" and "🟢" or "🔵"
    local label = current_gpu == "nvidia" and "NVIDIA" or "Intel"

    local parts = { widget.text(icon .. " " .. label) }

    if current_gpu == "nvidia" then
        if show_vram and vram_total > 0 then
            local pct = math.floor(vram_used / vram_total * 100)
            table.insert(parts, widget.text(string.format(" VRAM:%d%%", pct)))
        end
        if show_temp and gpu_temp > 0 then
            table.insert(parts, widget.text(string.format(" %d°C", gpu_temp)))
        end
    end

    return widget.hbox(parts)
end

function onClick(button)
    if button == 1 then
        noctalia.togglePanel("v0x3l/optimus-manager:panel")
    elseif button == 3 then
        switch_gpu()
    end
end

function switch_gpu()
    local target = current_gpu == "nvidia" and "intel" or "nvidia"
    current_gpu = "switching"
    noctalia.notify("GPU Switch", "Cambiando a " .. target .. "...")
    noctalia.runAsync({ "optimus-manager", "--switch", target, "--no-confirm" }, function(result)
        if result.exitCode == 0 then
            current_gpu = target
            if noctalia.getConfig("notify_on_switch") then
                noctalia.notify("GPU Switch", "Ahora en " .. target .. " (requiere relogin)")
            end
        else
            current_gpu = target == "nvidia" and "intel" or "nvidia"
            noctalia.notifyError("GPU Switch", "Falló: " .. (result.stderr or "desconocido"))
        end
    end)
end

return { build = build, update = update, onClick = onClick }
''',
    "entries/panel.lua": '''-- Panel expandible: controles completos Optimus
local widget = require("widget")
local ui = require("ui")

local current_mode = "intel"
local is_switching = false
local vram_used, vram_total, gpu_temp = 0, 0, 0
local driver_version = "desconocido"

local function refresh_mode()
    noctalia.runAsync({ "optimus-manager", "--status" }, function(result)
        if result.exitCode == 0 and result.stdout then
            current_mode = result.stdout:match("nvidia") and "nvidia" or "intel"
        end
    end)
end

refresh_mode()

function onOpen()
    refresh_mode()
    if current_mode == "nvidia" then
        noctalia.runAsync({ "nvidia-smi", "--query-gpu=memory.used,memory.total,temperature.gpu,driver_version", "--format=csv,noheader,nounits" }, function(r)
            if r.exitCode == 0 and r.stdout then
                local u, t, tmp, drv = r.stdout:match("(%d+)%s*,%s*(%d+)%s*,%s*(%d+)%s*,%s*([%d.]+)")
                if u then vram_used, vram_total, gpu_temp, driver_version = tonumber(u), tonumber(t), tonumber(tmp), drv end
            end
        end)
    end
end

function build()
    local info = current_mode == "nvidia"
        and { name = "NVIDIA RTX 4050", icon = "🟢", desc = "Máximo rendimiento, ComfyUI/Steam" }
        or { name = "Intel UHD Graphics", icon = "🔵", desc = "Ahorro energía, escritorio/video" }

    return widget.vbox({
        widget.hbox({
            widget.text(info.icon .. "  " .. info.name, { style = "heading" }),
            widget.spacer(),
            widget.button(is_switching and "Cambiando..." or "Switch GPU", {
                onClick = function()
                    if is_switching then return end
                    local target = current_mode == "nvidia" and "intel" or "nvidia"
                    is_switching = true
                    noctalia.notify("GPU", "Cambiando a " .. target .. "...")
                    noctalia.runAsync({ "optimus-manager", "--switch", target }, function(r)
                        is_switching = false
                        if r.exitCode == 0 then
                            current_mode = target
                            noctalia.notify("GPU", "Cambiado a " .. target .. " — relogin requerido")
                        else
                            noctalia.notifyError("GPU", "Error: " .. (r.stderr or "desconocido"))
                        end
                    end)
                end,
                enabled = not is_switching
            })
        }),
        widget.separator(),
        widget.text("Modo actual: " .. current_mode),
        widget.text("Descripción: " .. info.desc),
        widget.separator(),
        current_mode == "nvidia" and widget.vbox({
            widget.text("📊 NVIDIA Stats:", { style = "subheading" }),
            widget.text("VRAM: " .. vram_used .. " / " .. vram_total .. " MB"),
            widget.text("Temp: " .. gpu_temp .. "°C"),
            widget.text("Driver: " .. driver_version),
        }) or widget.text("Usa NVIDIA on-demand: prime-run <app>"),
        widget.separator(),
        widget.text("⚡ Acciones rápidas:", { style = "subheading" }),
        widget.hbox({
            widget.button("prime-run comfyui", {
                onClick = function() noctalia.runAsync("prime-run comfyui") end
            }),
            widget.button("prime-run steam", {
                onClick = function() noctalia.runAsync("prime-run steam") end
            }),
            widget.button("nvidia-smi (live)", {
                onClick = function()
                    noctalia.runInTerminal("nvidia-smi -l 1")
                end
            }),
        }),
        widget.separator(),
        widget.button("⚙️ Configuración del plugin", {
            onClick = function() noctalia.openSettings() end
        }),
    })
end

return { build = build, onOpen = onOpen }
''',
    "entries/service.lua": '''-- Servicio background: polling + alertas
noctalia.setUpdateInterval(10000)

local notify_on_switch = noctalia.getConfig("notify_on_switch")
local last_mode = nil

function update()
    noctalia.runAsync({ "optimus-manager", "--status" }, function(result)
        if result.exitCode ~= 0 or not result.stdout then return end
        local new_mode = result.stdout:match("nvidia") and "nvidia" or "intel"
        if last_mode and new_mode ~= last_mode and notify_on_switch then
            noctalia.notify("GPU Changed", "Ahora usando: " .. new_mode)
        end
        last_mode = new_mode
    end)

    -- Alerta temperatura crítica NVIDIA
    if last_mode == "nvidia" then
        noctalia.runAsync({ "nvidia-smi", "--query-gpu=temperature.gpu", "--format=csv,noheader,nounits" }, function(r)
            if r.exitCode == 0 then
                local temp = tonumber(r.stdout:match("(%d+)"))
                if temp and temp > 85 then
                    noctalia.notifyError("GPU Temp", "Temperatura crítica: " .. temp .. "°C")
                end
            end
        end)
    end
end

return { update = update }
'''
}
class DesktopStep(BaseStep):
    number = 5
    title = "Entorno"
    category = "final"

    def run(self) -> bool:
        ok = True

        # ---- Helpers ----
        def run_critical(desc: str, *args, **kwargs) -> bool:
            try:
                result = self.runner.ui.run_cmd(desc, *args, **kwargs)
                if not result:
                    log(f"ERROR {desc}: comando fallo (critico)")
                return result
            except Exception as e:
                log(f"ERROR {desc}: excepcion {type(e).__name__}: {e}")
                return False

        def run_nonfatal(desc: str, *args, **kwargs) -> bool:
            try:
                result = self.runner.ui.run_cmd(desc, *args, **kwargs)
                if not result:
                    log(f"WARN {desc}: comando fallo (no fatal)")
                return result
            except Exception as e:
                log(f"WARN {desc}: excepcion {type(e).__name__}: {e}")
                return False

        def ensure_user_ownership(path: str) -> bool:
            if user and os.geteuid() == 0 and os.path.exists(path):
                try:
                    subprocess.run(
                        ["chown", "-R", f"{user}:", path],
                        capture_output=True, check=False
                    )
                    return True
                except Exception:
                    pass
            return True

        # ---- Dotfiles (assets/dotfiles → ~/.config del usuario) ----
        for src_name, dest_rel in DOTFILES_MAP.items():
            src = os.path.join(str(DOTFILES_DIR), src_name)
            dest = os.path.join(home, dest_rel)
            if not os.path.exists(src):
                log(f"WARN dotfile fuente faltante: {src}")
                continue
            if os.path.exists(dest) and src_name != "kitty":
                log(f"INFO dotfile existente preservado: {dest}")
                continue
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            if src_name == "kitty" and os.path.isdir(dest):
                copied = self.runner.ui.run_cmd(f"deploy dotfile {src_name}",
                    "cp", "-r", f"{src}/.", dest, sudo=True)
            else:
                copied = self.runner.ui.run_cmd(f"deploy dotfile {src_name}",
                    "cp", "-r", src, dest, sudo=True)
            if not copied:
                log(f"ERROR dotfile: fallo al desplegar {src_name}")
                ok = False
                continue
            if os.geteuid() == 0:
                chowned = self.runner.ui.run_cmd(
                    f"chown dotfile {src_name}", "chown", "-R",
                    f"{user}:", dest, sudo=True)
                ok &= chowned
        return ok and self._install_zsh_lazyvim() and self._install_omp_harness() and self._install_optimus_plugin()

    def _install_zsh_lazyvim(self) -> bool:
        """Instala el starter oficial de LazyVim de forma idempotente.

        Sigue https://www.lazyvim.org/installation: respalda config, data,
        state y cache de Neovim; clona el starter y elimina su .git.
        """
        user = TARGET_USER
        home = TARGET_HOME
        if not user or user == "root" or not home or home == "/root":
            log("ERROR lazyvim: TARGET_USER/TARGET_HOME invalido")
            return False

        config_dir = os.path.join(home, ".config")
        nvim_dir = os.path.join(config_dir, "nvim")
        # El starter valido trae init.lua y lua/ (config y plugins). Un
        # init.lua suelto es una config ajena: se respalda y se reinstala.
        if (os.path.exists(os.path.join(nvim_dir, "init.lua"))
                and os.path.isdir(os.path.join(nvim_dir, "lua"))):
            return True

        os.makedirs(config_dir, exist_ok=True)
        if os.geteuid() == 0:
            if not self.runner.ui.run_cmd("chown nvim parent",
                    "chown", "-R", f"{user}:", config_dir, sudo=True):
                return False
            if not self.runner.ui.run_cmd("chmod nvim parent",
                    "chmod", "755", config_dir, sudo=True):
                return False

        # LazyVim documenta estos cuatro paths. No borres backups anteriores:
        # cada instalacion recibe un sufijo timestamped.
        from datetime import datetime
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        backup_paths = (
            nvim_dir,
            os.path.join(home, ".local", "share", "nvim"),
            os.path.join(home, ".local", "state", "nvim"),
            os.path.join(home, ".cache", "nvim"),
        )
        for path in backup_paths:
            if not os.path.exists(path):
                continue
            backup = f"{path}.bak.{stamp}"
            try:
                shutil.move(path, backup)
            except OSError as exc:
                log(f"ERROR lazyvim: no se pudo respaldar {path}: {exc}")
                return False

        clone_ok = self.runner.ui.run_cmd("install lazyvim",
            "runuser", "-u", user, "--", "env",
            f"HOME={home}", f"USER={user}",
            "git", "clone", "--depth", "1",
            "https://github.com/LazyVim/starter", nvim_dir,
            sudo=False)
        if not clone_ok:
            log("ERROR lazyvim: git clone fallo; revisar red y permisos")
            return False

        git_dir = os.path.join(nvim_dir, ".git")
        if os.path.isdir(git_dir):
            shutil.rmtree(git_dir)
        if os.geteuid() == 0 and not self.runner.ui.run_cmd(
                "chown lazyvim", "chown", "-R", f"{user}:", nvim_dir,
                sudo=True):
            return False
        return True

    @staticmethod
    def _omp_binary(home: str) -> str:
        """Ruta del binario omp instalado, o '' si no existe.

        El instalador oficial deja omp en ~/.local/bin (binario) o en
        ~/.bun/bin (instalacion via bun).
        """
        if not home:
            return ""
        for rel in (".local/bin/omp", ".bun/bin/omp"):
            path = os.path.join(home, rel)
            if os.path.isfile(path) and os.access(path, os.X_OK):
                return path
        return ""

    def _install_omp_harness(self) -> bool:
        """Instala omp y despliega el harness personal desde el repo.

        Docs: https://omp.sh/docs/quickstart
        El binario oficial vive en ~/.local/bin/omp. La configuracion se
        copia a ~/.omp/agent preservando config.yml, models.yml y .env: el
        endpoint y la API key se fijan despues de forma manual con
        scripts/setup.sh (genera la key e introduce la URL del proveedor).
        """
        user = TARGET_USER
        home = TARGET_HOME
        if not user or user == "root" or not home or home == "/root":
            log("ERROR omp: TARGET_USER/TARGET_HOME invalido")
            return False

        agent_dir = os.path.join(home, ".omp", "agent")

        # 1) Binario omp (instalador oficial, como usuario destino).
        # El instalador usa ~/.bun/bin si hay bun compatible y ~/.local/bin
        # si no; se resuelve el binario en vez de asumir una ruta.
        omp_bin = self._omp_binary(home)
        ok = True
        if not omp_bin:
            ok = self.runner.ui.run_cmd("install omp",
                "runuser", "-u", user, "--", "env", f"HOME={home}",
                "bash", "-c",
                "curl -fsSL https://omp.sh/install | sh",
                "omp-install", sudo=False)
            omp_bin = self._omp_binary(home)
        if not ok or not omp_bin:
            log("ERROR omp: fallo la instalacion del binario")
            return False

        # Enlace global: la sesion grafica y otros shells pueden no incluir
        # ~/.local/bin ni ~/.bun/bin en PATH.
        if os.geteuid() == 0:
            ok &= self.runner.ui.run_cmd("link omp in system PATH",
                "ln", "-sf", omp_bin, "/usr/local/bin/omp", sudo=True)

        # 2) Configuracion personal desde el repo.
        staging = tempfile.mkdtemp(prefix="v0x3l-omp-")
        try:
            if os.geteuid() == 0:
                shutil.chown(staging, user=user)
            clone = os.path.join(staging, "repo")
            if not self.runner.ui.run_cmd("clone omp-harness",
                    "runuser", "-u", user, "--", "env", f"HOME={home}",
                    "git", "clone", "--depth", "1", OMP_HARNESS_REPO, clone,
                    sudo=False):
                log("ERROR omp: no se pudo clonar el harness")
                return False
            if not self._deploy_omp_harness(clone, agent_dir):
                return False
        finally:
            shutil.rmtree(staging, ignore_errors=True)

        if os.geteuid() == 0:
            ok &= self.runner.ui.run_cmd("chown omp agent dir",
                "chown", "-R", f"{user}:", os.path.join(home, ".omp"),
                sudo=True)


        log("omp instalado. Configura endpoint y API key manualmente con: "
            f"sh {agent_dir}/scripts/setup.sh")
        return ok

    def _deploy_omp_harness(self, src: str, agent_dir: str) -> bool:
        """Copia el harness respetando los archivos locales del usuario."""
        if not os.path.isdir(src):
            log(f"ERROR omp: harness origen inexistente: {src}")
            return False
        keep = {}
        for name in OMP_HARNESS_KEEP:
            path = os.path.join(agent_dir, name)
            if os.path.isfile(path):
                with open(path, "rb") as f:
                    keep[name] = f.read()

        os.makedirs(agent_dir, exist_ok=True)
        for entry in os.listdir(src):
            if entry in (".git", ".gitignore"):
                continue
            source = os.path.join(src, entry)
            target = os.path.join(agent_dir, entry)
            if os.path.isdir(source):
                shutil.copytree(source, target, dirs_exist_ok=True)
            else:
                shutil.copy2(source, target)

        for name, content in keep.items():
            path = os.path.join(agent_dir, name)
            with open(path, "wb") as f:
                f.write(content)
            log(f"omp harness: se conservo {name} existente")
        return True

    def _install_optimus_plugin(self) -> bool:
        """Instala plugin Noctalia para gestión de NVIDIA Optimus."""
        user = TARGET_USER
        home = TARGET_HOME
        if not user or user == "root" or not home or home == "/root":
            log("WARN optimus-plugin: usuario invalido, omitiendo")
            return False

        plugin_dir = os.path.join(home, ".config", "noctalia", "plugins", "optimus-manager")
        entries_dir = os.path.join(plugin_dir, "entries")
        os.makedirs(entries_dir, exist_ok=True)

        ok = True
        for rel_path, content in OPTIMUS_PLUGIN_FILES.items():
            dest = os.path.join(plugin_dir, rel_path)
            try:
                with open(dest, "w") as f:
                    f.write(content)
                log(f"INFO optimus-plugin: escrito {rel_path}")
            except Exception as e:
                log(f"ERROR optimus-plugin: {rel_path}: {type(e).__name__}: {e}")
                ok = False

        if os.geteuid() == 0:
            subprocess.run(
                ["chown", "-R", f"{user}:", plugin_dir],
                capture_output=True, check=False
            )

        if ok:
            log("INFO optimus-plugin instalado en ~/.config/noctalia/plugins/optimus-manager")
        return ok
