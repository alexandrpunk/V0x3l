# VoidForge

Post-instalador minimalista para Ubuntu Server con optimización para hardware moderno.

## Descripción

VoidForge automatiza la configuración de Ubuntu Server para transformarlo en un sistema Wayland listo para uso, con soporte para GPU NVIDIA/Optimus, kernel optimizado (XanMod), temas personalizados y herramientas esenciales.

## Requisitos

- Ubuntu Server 26.04 LTS (o compatible)
- Acceso root (sudo)
- Conexión a internet
- Mínimo 4GB RAM recomendado (8GB para desarrollo/gaming)
- 20GB espacio libre en disco

## Características

- **Instalación modular**: 16 pasos independientes, cada uno es una función `step_N()` — permite ejecución granular
- **Checkpoint system**: Guarda progreso en `/tmp/voidforge-progress`, reanudable tras fallos
- **Menú interactivo**: 6 opciones: instalación completa, resume, paso específico, rango, estado, salir
- **CLI flags**: `--resume`, `--step N`, `--range N-M`, `--skip N,M,...`, `--all`
- **Detección de hardware**: `lspci` para detectar GPU NVIDIA, `ubuntu-drivers devices` para versión óptima
- **Optimización de paquetes**: De ~12 llamadas nala a 1 mega-instalación (paso 4), más rápido y menos I/O
- **Idempotencia**: Configuraciones que ya existen se omiten con `⏭️` (pasa 9 polkit, UFW, TLP, etc.)
- **NVIDIA DRM/KMS**: Habilitado automáticamente para Wayland, con parámetros kernel y módulos initramfs
- **Colores y logging**: Helpers visuales con códigos ANSI para progreso, éxito, warnings, errores

## Uso

```bash
sudo bash VoidForge.sh
```

### Modos de ejecución

| Opción | Descripción |
|--------|-------------|
| [1] | Instalación completa (todos los pasos 0-15) |
| [2] | Reanudar desde último checkpoint (si hubo fallo) |
| [3] | Ejecutar un paso específico |
| [4] | Ejecutar un rango de pasos |
| [5] | Ver estado actual de la instalación |
| [6] | Salir |

### Flags CLI (para automatización)

```bash
sudo bash VoidForge.sh --resume           # Reanudar desde último checkpoint guardado
sudo bash VoidForge.sh --step 5           # Ejecutar solo paso 5
sudo bash VoidForge.sh --range 5-10       # Ejecutar pasos 5 a 10 inclusive
sudo bash VoidForge.sh --skip 3,7         # Omitir pasos 3 y 7 (separados por coma)
sudo bash VoidForge.sh --all              # Ejecutar todo (equivalente a menú [1])
```

**Combinar flags:**
```bash
sudo bash VoidForge.sh --skip 8 --range 0-6   # Omitir Flatpak, ejecutar pasos 0-6
sudo bash VoidForge.sh --resume --skip 13    # Reanudar pero omitir Plymouth/GRUB
```

**Ejemplos de uso real:**
- Testear nuevo paso en desarrollo: `sudo bash VoidForge.sh --step 13`
- Reinstalar solo Flatpak tras fallo: `sudo bash VoidForge.sh --step 8`
- Instalar sin Dank Linux: `sudo bash VoidForge.sh --skip 15`
- Corregir Plymouth/GRUB tras problemas: `sudo bash VoidForge.sh --step 13`

## Pasos de instalación

| # | Descripción |
|---|-------------|
| 0 | Bootstrap: `apt install` (nala aún no disponible) wget, tar, unzip, file, zsh, git, curl, ca-certificates, pciutils, locales |
| 1 | ButterRepo, upgrade, grupos, timezone (America/Mazatlan), locale (es_MX.UTF-8) |
| 2 | Kernel XanMod Edge (repo oficial, versión edge más reciente) |
| 3 | Detección GPU + drivers NVIDIA (version dinámica con `ubuntu-drivers devices`) + Optimus. Si NVIDIA: habilita servicios `nvidia-suspend/resume/hibernate` |
| 4 | Mega-instalación: Wayland, Nautilus, Apps, Audio/Bluetooth, Codecs, Flatpak, TLP, fonts-powerline (13 paquetes agrupados en 1) |
| 5 | Regla polkit para automontaje |
| 6 | xdg-user-dirs + UFW (deny incoming, allow outgoing) |
| 7 | Netplan (NetworkManager) + desactivación de `systemd-networkd-wait-online.service` |
| 8 | Flathub + Apps Flatpak (Papers, Resources, Showtime) + override para Nautilus |
| 9 | Habilitar servicios (NetworkManager, udisks2, bluetooth) + servicios usuario (pipewire, wireplumber) + `environment.d/wayland.conf` |
| 10 | TLP (configuración personalizada en `/etc/tlp.d/01-voidforge.conf`) + logind (lid switch, power key) |
| 11 | Oh My Zsh (instalación vía curl, tema agnoster), cambia shell por defecto a zsh |
| 12 | Tema de iconos Colloid (catppuccin green) desde GitHub |
| 13 | Plymouth (desde ZIP local) + GRUB Vimix + parámetros kernel para NVIDIA DRM/KMS + módulos en initramfs |
| 14 | Limpieza: `nala autoremove`, `nala clean` |
| 15 | Instalador Dank Linux (ejecuta al final) |

## Hardware

### GPU NVIDIA

El script detecta automáticamente usando `lspci`:
- **GPU NVIDIA pura** → instala `nvidia-driver-<VERSION>` + `nvidia-settings` + habilita servicios de suspend/resume
- **Sistema híbrido (Intel + NVIDIA)** → instala `nvidia-driver-<VERSION>` + `nvidia-prime` + `nvidia-settings`, configura `prime-select on-demand`, habilita servicios suspend/resume
- **Sin NVIDIA** → omite drivers, usa Mesa (Mesa-DRI ya incluido en mega-instalación)

**Detección dinámica de versión:**
```bash
NVIDIA_VER=$(ubuntu-drivers devices 2>/dev/null | grep -oP 'nvidia-driver-\K\d+' | sort -rn | head -1)
```
Si `ubuntu-drivers` no está disponible, fallback a `nvidia-driver-535`. Esto garantiza que siempre se instale la versión compatible más reciente para tu hardware específico.

**Parámetros kernel agregados para NVIDIA (si detectado):**
```bash
nvidia-drm.modeset=1 nvidia-drm.fbdev=1 nvidia.NVreg_PreserveVideoMemoryAllocations=1
```

- `nvidia-drm.modeset=1`: Habilita DRM/KMS, **obligatorio** para Wayland
- `nvidia-drm.fbdev=1`: Activa framebuffer device para console y Plymouth
- `nvidia.NVreg_PreserveVideoMemoryAllocations=1`: Preserva VRAM en suspend/resume (importante para laptops)

**Módulos NVIDIA en initramfs (si GPU detectada):**
```
nvidia
nvidia-drm
nvidia-modeset
nvidia-uvm
```
Escritos en `/etc/initramfs-tools/modules` y regenerados con `update-initramfs -u`. Esto permite que el framebuffer esté disponible desde el boot temprano, permitiendo que Plymouth se muestre correctamente.

**Servicios NVIDIA (habilitados automáticamente si es laptop):**
- `nvidia-suspend`
- `nvidia-resume`
- `nvidia-hibernate`

### Laptops

TLP configurado con optimizaciones:
- CPU limitado a 80% en batería
- PCIe ASPM powersupersave
- USB autosuspend
- WiFi power save en batería
- Audio power save

## Personalización

### Zona horaria y locale

Valores por defecto:
- Zona horaria: `America/Mazatlan`
- Locale: `es_MX.UTF-8`

Edita las líneas 64-66 en el script para cambiar:
```bash
timedatectl set-timezone <tu-zona>
```
```bash
sed -i 's/^# *es_MX\.UTF-8 UTF-8/es_MX.UTF-8 UTF-8/' /etc/locale.gen
```

### Tema Plymouth

Coloca un archivo `.zip` con el tema en el mismo directorio que el script, o establece `PLYMOUTH_ZIP_NAME` en el script (línea 44):
```bash
PLYMOUTH_ZIP_NAME="mi-tema-plymouth.zip"
```

Si no se encuentra ningún ZIP, se omite sin error. El script busca el primer `.zip` en el directorio del script.

### Tema de iconos

El script instala **Colloid** con variante **catppuccin green**. Para cambiar:
1. Edita el paso 12 en el script (línea 310)
2. Cambia `-s catppuccin -t green` a tu preferencia:
   - `-s dracula -t purple` (Dracula, púrpura)
   - `-s nord -t blue` (Nord, azul)
   - `-s gruvbox -t orange` (Gruvbox, naranja)

### Oh My Zsh tema

Por defecto usa `agnoster`. Para cambiar, edita la línea 299:
```bash
sed -i "s/^ZSH_THEME=.*/ZSH_THEME=\"powerlevel10k\"/" "$HOME/.zshrc"
```

Para usar powerlevel10k, instálalo primero:
```bash
git clone --depth=1 https://github.com/romkatv/powerlevel10k.git ~/powerlevel10k
~/powerlevel10k/install.sh
```

## Comandos útiles

```bash
# Reiniciar para aplicar kernel XanMod o drivers NVIDIA
sudo reboot

# Usar GPU NVIDIA en sistemas híbridos
prime-run <aplicación>

# Estado TLP
tlp-stat

# Ver logs de instalación
# Los logs se muestran en tiempo real en terminal

# Reinstalar un paso específico
sudo bash VoidForge.sh --step <número>
```

## Idempotencia

El script es idempotente — puedes ejecutarlo varias veces sin romper configuraciones existentes:

| Configuración | ¿Se omite si existe? |
|---------------|----------------------|
| ButterRepo | ✅ Si `/etc/apt/sources.list.d/butterrepo.list` existe |
| Zona horaria | ✅ Si ya es `America/Mazatlan` |
| Locale es_MX.UTF-8 | ✅ Si ya en `locale -a` |
| Polkit rule | ✅ Si `/etc/polkit-1/rules.d/90-udisks2-automount.rules` existe |
| UFW | ✅ Si status es `active` |
| Netplan | ✅ Si `/etc/netplan/01-netcfg.yaml` ya tiene `NetworkManager` |
| Flatpak Flathub | ✅ Usa `--if-not-exists` |
| Flatpak override | ✅ Si `/etc/flatpak/overrides/global` existe |
| wayland.conf | ✅ Si `$HOME/.config/environment.d/wayland.conf` existe |
| TLP config | ✅ Si `/etc/tlp.d/01-voidforge.conf` existe |
| logind config | ✅ Usa `grep -q` solo si valor ya establecido |
| Shell zsh | ✅ Comprueba `/etc/passwd` antes de cambiar |
| Oh My Zsh | ✅ Si `~/.oh-my-zsh` existe, solo actualiza tema |
| Colloid icons | ✅ Si `/usr/share/icons/Colloid-catppuccin-green-dark` existe |
| Plymouth theme | ✅ Si ya instalado, reutiliza sin reextraer ZIP |
| GRUB theme | ✅ Si `/usr/share/grub/themes/grub-theme-vimix-very-dark-blue/theme.txt` existe |
| NVIDIA params | ✅ Usa `grep -q` solo si aún no están en línea |

Las instalaciones de paquetes (`nala install`, `apt install`, `flatpak install`) son naturalmente idempotentes — reinstallar un paquete ya instalado no hace nada.

## Logs y Debugging

El script usa `echo` con emojis para progreso. Si necesitas más información:

**Revisar configuraciones aplicadas:**
```bash
# Configuración GRUB
cat /etc/default/grub | grep GRUB_CMDLINE_LINUX

# Configuración logind
grep -E "HandleLidSwitch|PowerKeyAction" /etc/systemd/logind.conf

# Estado UFW
sudo ufw status verbose

# Estado TLP
sudo tlp-stat -s

# Flatpak remotos y apps
flatpak remotes
flatpak list

# Servicios
systemctl status NetworkManager bluetooth tlp pipewire wireplumber
```

**Logs del sistema:**
```bash
# Logs recientes
journalctl -xe

# Logs de arranque (NVIDIA, Plymouth, etc.)
journalctl -b 0 -xe

# Logs de Plymouth (si no se muestra)
dmesg | grep -i plymouth
```

**Checkpoint:**
```bash
cat /tmp/voidforge-progress
# Muestra número del último paso completado
```

**Deshacer cambios (último recurso):**
- Eliminar checkpoint: `rm /tmp/voidforge-progress`
- Deshacer instalación: ejecutar pasos relevantes manualmente (usar flags `--step N`)

## Troubleshooting

### Plymouth no se muestra

Verifica:
```bash
cat /proc/cmdline
# Debería contener: quiet splash nvidia-drm.modeset=1 (si NVIDIA)
```

```bash
ls -la /usr/share/plymouth/themes/
# Tu tema debería estar aquí
```

```bash
update-alternatives --config default.plymouth
# Verifica tu tema está seleccionado
```

### NVIDIA no funciona en Wayland

Verifica:
```bash
cat /proc/cmdline
# Debe contener nvidia-drm.modeset=1
```

```bash
lsmod | grep nvidia
# Módulos deberían estar cargados
```

```bash
prime-select query
# Debería mostrar estado de Optimus
```

### Pendiente reanudar desde checkpoint

El script guarda el último paso completado en `/tmp/voidforge-progress`. Si el script falló o fue interrumpido, ejecuta:

```bash
sudo bash VoidForge.sh --resume
```

Esto continuará desde el paso siguiente al último completado.

### Errores en el paso de Flatpak

Flathub puede fallar si el servidor está ocupado. Reintenta ejecutando solo el paso 8:

```bash
sudo bash VoidForge.sh --step 8
```

## Estructura del proyecto

```
VoidForge/
├── VoidForge.sh      # Script principal
├── AGENTS.md          # Notas para agentes de desarrollo
├── README.md          # Este archivo
└── *.zip              # Tema Plymouth (opcional)
```

## Recomendaciones

### Antes de ejecutar

1. **Backup**: Haz un backup de datos importantes antes de ejecutar el script
2. **Actualización**: Ejecuta `sudo apt update && sudo apt upgrade` primero para asegurar un sistema base estable
3. **Conexión estable**: El script descarga varios paquetes y recursos externos (~3GB), asegúrate de tener conexión estable
4. **Batería**: En laptops, conecta a AC para evitar que el sistema se suspenda durante instalación larga
5. **Espacio en disco**: Requiere ~10-15GB para paquetes + ~1GB para kernels (XanMod retiene 2 kernels)

### Después de ejecutar

1. **Reiniciar**: Si se instaló XanMod Edge o drivers NVIDIA, reiniciar es **obligatorio** para aplicar cambios
2. **Verificar kernel**: `uname -r` debería mostrar kernel XanMod (ej: `6.12.9-xanmod1-edge`)
3. **Verificar GPU NVIDIA**: `nvidia-smi` debería mostrar información de la GPU y drivers. Si falla, verifica que los módulos estén cargados: `lsmod | grep nvidia`
4. **Configurar Dank Linux**: El paso 15 ejecuta el instalador Dank Linux, completa la configuración de entorno y aplicaciones allí
5. **Verificar TLP**: `tlp-stat` debe mostrar estado de ahorro de energía (BATT/AC)
6. **Revisar logs**: Revisa `/var/log/syslog` o `journalctl -xe` si hay errores durante instalación

### Para sistemas con Optimus

- **Usar GPU discreta**: `prime-run <app>` (juegos, Blender, rendering 3D)
- **Cambiar comportamiento por defecto**:
  ```bash
  sudo prime-select intel    # Usar solo integrado (ahorra batería)
  sudo prime-select nvidia   # Usar siempre discreto (batería consume)
  sudo prime-select on-demand # Por demanda (default, NVIDIA solo con prime-run)
  ```
- **Ver estado**: `prime-select query` o `cat /etc/prime-discrete`
- **Reiniciar necesario**: Cualquier cambio en `prime-select` requiere logout y re-login

### Para laptops

- **TLP automático**: Se activa con el sistema, ajusta CPU/generadores/PCIe según AC vs batería
- **Monitoreo detallado**: `sudo tlp-stat -s` muestra estado completo (temperaturas, consumo, periféricos)
- **Personalizar**: Edita `/etc/tlp.d/01-voidforge.conf` y ejecuta `sudo tlp start`
- **Suspend/Hibernate**: Configurado automáticamente en `/etc/systemd/logind.conf` (tapar portátil = suspend)

### Para mantener kernel XanMod

XanMod Edge se actualiza con frecuencia con nuevas versiones. Para actualizar:
```bash
sudo nala update
sudo nala install --download-only linux-xanmod-edge-x64
sudo nala install linux-xanmod-edge-x64
sudo reboot
```
El script retiene automáticamente 2 kernels (actual + anterior), así puedes probar versión nueva sin riesgo.

### Solución de problemas NVIDIA

**Problema**: Wayland no funciona, NVIDIA driver no carga  
**Diagnóstico**: `cat /proc/cmdline | grep nvidia`  
**Solución**: Asegúrate de que `nvidia-drm.modeset=1` está en `/proc/cmdline`. Si no, ejecuta paso 13 de nuevo.

**Problema**: Plymouth no se muestra  
**Diagnóstico**: `update-alternatives --config default.plymouth`  
**Solución**: Verifica que `/etc/initramfs-tools/modules` tenga `drm` (o módulos NVIDIA si aplica). Ejecuta `sudo update-initramfs -u`.

**Problema**: Suspender no funciona con NVIDIA  
**Diagnóstico**: `systemctl status nvidia-suspend`  
**Solución`: Revisa `/etc/systemd/logind.conf` (HandleLidSwitch=suspend) y verifica servicios NVIDIA están habilitados.

## Contribuciones

El script es monolintario y autocontenido. Para modificar:

1. Edita `VoidForge.sh`
2. Cada paso es una función `step_N()`
3. Usa los helpers: `log_step()`, `log_ok()`, `log_skip()`, `log_warn()`, `log_error()`
4. Guarda checkpoint con `save_checkpoint <número>`

## License

MIT

---

**Tu sistema. Tus reglas. Tu forja.**
