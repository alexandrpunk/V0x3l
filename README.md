# VoidForge

Post-instalador minimalista para Ubuntu Server con optimización para hardware moderno.

## Descripción

VoidForge automatiza la configuración de Ubuntu Server para transformarlo en un sistema Wayland listo para uso, con soporte para GPU NVIDIA/Optimus, kernel optimizado (XanMod), temas personalizados y herramientas esenciales.

## Requisitos

- Ubuntu Server 24.04 LTS (o compatible)
- Acceso root (sudo)
- Conexión a internet
- Mínimo 8GB RAM recomendado (16GB para desarrollo/gaming)
- 20GB espacio libre en disco

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
| [6] | Generar README.md |
| [7] | Salir |

### Flags CLI (para automatización)

```bash
sudo bash VoidForge.sh --resume           # Reanudar desde checkpoint
sudo bash VoidForge.sh --step 5           # Ejecutar solo paso 5
sudo bash VoidForge.sh --range 5-10       # Ejecutar pasos 5-10
sudo bash VoidForge.sh --skip 3,7         # Omitir pasos 3 y 7
sudo bash VoidForge.sh --all              # Ejecutar todo (equivalente a menú [1])
```

## Pasos de instalación

| # | Descripción |
|---|-------------|
| 0 | Bootstrap: nala, git, curl, zsh, pciutils, locales |
| 1 | ButterRepo, upgrade, grupos, timezone (America/Mazatlan), locale (es_MX.UTF-8) |
| 2 | Kernel XanMod Edge |
| 3 | Detección GPU + drivers NVIDIA (version dinámica con `ubuntu-drivers`) + Optimus |
| 4 | Mega-instalación: Wayland, Nautilus, Apps, Audio, Codecs, Flatpak, TLP, Fonts |
| 5 | Regla polkit para automontaje |
| 6 | xdg-user-dirs + UFW (deny incoming) |
| 7 | Netplan (NetworkManager) + desactivación de systemd-networkd-wait-online |
| 8 | Flathub + Apps Flatpak (Papers, Resources, Showtime) |
| 9 | Habilitar servicios (NetworkManager, bluetooth, pipewire, wireplumber) + env Wayland |
| 10 | TLP (configuración personalizada) + logind (lid switch, power key) |
| 11 | Oh My Zsh + tema agnoster |
| 12 | Tema de iconos Colloid (catppuccin green) |
| 13 | Plymouth + GRUB + parámetros kernel para NVIDIA DRM/KMS |
| 14 | Limpieza: nala autoremove + clean |
| 15 | Instalador Dank Linux (ejecuta al final) |

## Hardware

### GPU NVIDIA

El script detecta automáticamente:
- GPU NVIDIA pura → instala driver propietario
- Sistema híbrido (Intel + NVIDIA) → instala NVIDIA + Optimus (prime-select on-demand)
- Sin NVIDIA → omite, usa Mesa

El driver se selecciona dinámicamente usando `ubuntu-drivers devices` para encontrar la versión más reciente compatible.

**Parámetros kernel agregados para NVIDIA (si detectado):**
```
nvidia-drm.modeset=1 nvidia-drm.fbdev=1 nvidia.NVreg_PreserveVideoMemoryAllocations=1
```

Esto habilita DRM/KMS (necesario para Wayland) y framebuffer.

**Servicios NVIDIA:**
- `nvidia-suspend`, `nvidia-resume`, `nvidia-hibernate` habilitados para laptops

### Laptops

TLP configurado con optimizaciones:
- CPU limitado a 80% en batería
- PCIe ASPM powersupersave
- USB autosuspend
- WiFi power save en batería
- Audio power save

## Personalización

### Tema Plymouth

Coloca un archivo `.zip` con el tema en el mismo directorio que el script, o descomenta y establece `PLYMOUTH_ZIP_NAME` en el script:

```bash
PLYMOUTH_ZIP_NAME="mi-tema-plymouth.zip"
```

Si no se encuentra ningún ZIP, se omite sin error.

### Tema de iconos

El script instala **Colloid** con variante **catppuccin green**. Para cambiar:

1. Edita el paso 12 en el script
2. Cambia `-s catppuccin -t green` a tu preferencia (ej: `-s dracula -t purple`)

### Zona horaria y locale

Valores por defecto:
- Zona horaria: `America/Mazatlan`
- Locale: `es_MX.UTF-8`

Edita el script en el paso 1 para cambiar.

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
3. **Conexión estable**: El script descarga varios paquetes y recursos externos, asegúrate de tener conexión estable

### Después de ejecutar

1. **Reiniciar**: Si se instaló XanMod Edge o drivers NVIDIA, reiniciar es obligatorio
2. **Verificar GPU NVIDIA**: Ejecuta `nvidia-smi` para verificar que el driver esté cargado correctamente
3. **Configurar Dank Linux**: El paso 15 ejecuta el instalador Dank Linux, completa la configuración allí

### Para sistemas con Optimus

- Usa `prime-run <app>` para aplicaciones que necesitan GPU discreta (juegos, rendering)
- Para cambiar comportamiento por defecto: `prime-select intel` (integrado) o `prime-select nvidia` (discreto)
- `prime-select query` para ver estado actual

### Para laptops

- TLP maneja automáticamente la energía en batería vs enchufado
- `tlp-stat` muestra el estado detallado de ahorro de energía
- Ajusta la configuración de TLP en `/etc/tlp.d/01-voidforge.conf` según tus necesidades

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