# RHL - Real High Level Audio Visualizer

**RHL** es un visualizador de audio de alto rendimiento desarrollado en Python 3.13. A diferencia de los visualizadores tradicionales, RHL abandona el pipeline fijo antiguo para utilizar **OpenGL Moderno (Core Profile 3.3)**, aprovechando la aceleración por hardware (GPU) mediante Shaders programables (GLSL) para renderizar millones de partículas, efectos de post-procesado (Bloom) y modelos 3D en tiempo real.

El sistema cuenta con un motor de audio híbrido capaz de capturar tanto el sonido del escritorio (Loopback/WASAPI) como micrófonos físicos con latencia ultra baja.

---

## 🚀 Características Principales

*   **Renderizado Moderno:** Uso de `PyOpenGL` y `Pygame` con contexto Core Profile 3.3. Todo el dibujo se realiza mediante VBOs, VAOs y Shaders personalizados.
*   **Motor de Audio Híbrido:**
    *   **SoundCard:** Para captura de audio del sistema (Loopback) de alta fidelidad.
    *   **SoundDevice:** Para entrada de micrófono con baja latencia mediante Callbacks.
*   **Efectos Visuales Reactivos:**
    *   **Túnel Espectral:** Visualización de frecuencias mapeadas en coordenadas polares.
    *   **Campos Estelares:** Partículas que reaccionan a la energía de graves y agudos independientemente.
    *   **Modelo 3D:** Carga de modelos (OBJ/GLB) con iluminación y movimiento reactivo al ritmo.
*   **Post-Procesado:** Implementación de efecto **Bloom** (resplandor) mediante Framebuffer Objects (FBO) y shaders de desenfoque gaussiano.
*   **UI Personalizada:** Interfaz de configuración renderizada en GPU, permitiendo ajustar parámetros en tiempo real sin detener la visualización.

---

## 📋 Requisitos del Sistema

*   **Sistema Operativo:** Windows 10/11 (Recomendado para soporte WASAPI).
*   **Python:** Versión **3.13** (64-bit).
*   **GPU:** Tarjeta gráfica compatible con **OpenGL 3.3** o superior.
*   **Drivers:** Controladores de GPU actualizados (NVIDIA/AMD/Intel).

### Dependencias
El proyecto depende de las siguientes librerías clave (ver `requirements.txt`):
*   `numpy`: Procesamiento matemático y FFT.
*   `pygame`: Creación de ventana y contexto GL.
*   `PyOpenGL`: Bindings para OpenGL.
*   `pyrr`: Matemáticas 3D (Matrices, Vectores, Quaterniones).
*   `SoundCard` & `sounddevice`: Captura de audio.
*   `trimesh` & `pillow`: Carga y procesamiento de modelos 3D y texturas.

---

## 🛠️ Instalación

1.  **Clonar el repositorio o descargar el código fuente.**

2.  **Crear un entorno virtual (Opcional pero recomendado):**
    ```bash
    python -m venv venv_rhl
    .\venv_rhl\Scripts\Activate.ps1  # En PowerShell
    ```

3.  **Instalar dependencias:**
    Asegúrate de estar en la carpeta raíz del proyecto donde se encuentra el archivo `requirements.txt`.
    ```bash
    python -m pip install --upgrade pip
    python -m pip install -r requirements.txt
    ```

4.  **Ejecutar la aplicación:**
    ```bash
    python main.py
    ```

## 📥 Descarga para Windows
[![Descargar RHL](https://img.shields.io/badge/Descargar-RHL_v1.0.0-blue?style=for-the-badge&logo=windows)](https://github.com/Doto256/RHL-Audio-Visualizer/releases/download/v1.0.0/RHl.exe)

> **Nota:** No requiere instalación de Python. Solo descarga y ejecuta el `.exe`.

## ⌨️ Controles y Atajos

Para sacarle el máximo provecho al RHL, utilizá los siguientes comandos:

| Tecla | Acción |
| :--- | :--- |
| **Esc** | Abre el panel de configuración (Bloom, Sensibilidad, Colores, etc.). |
| **M** | Abre el menú de selección de dispositivos de audio. |
| **Shift + Click** | (En el menú M) **Suma** un nuevo dispositivo a la mezcla actual. |
| **Click simple** | Selecciona un único dispositivo (reemplaza al anterior). |

> **Tip de experto:** Podés mezclar el audio de tu escritorio con tu micrófono manteniendo `Shift` presionado al seleccionar el segundo dispositivo en el menú `M`.
---

## 📂 Estructura del Proyecto

La arquitectura del software es modular para facilitar la escalabilidad:

*   **`main.py`**: Punto de entrada. Inicializa el contexto de Pygame, configura OpenGL y ejecuta el bucle principal (Eventos -> Update -> Render).

*   **`core/`**:
    *   Manejo del estado global (`Context`).
    *   Gestión del tiempo y delta-time (`TimeManager`).

*   **`audio/`**:
    *   **`engine.py`**: Orquesta la captura de audio, unificando los backends de `SoundCard` y `SoundDevice`.
    *   **`fft.py`**: Realiza la Transformada Rápida de Fourier, aplica ventaneo (Hanning) y suavizado logarítmico.

*   **`render/`**:
    *   **`renderer.py`**: El corazón gráfico. Gestiona la escena 3D, el túnel y las partículas.
    *   **`shaders.py`**: Cargador y compilador de programas GLSL (`.vert`, `.frag`).
    *   **`postprocess.py`**: Maneja los FBOs para el efecto Bloom.
    *   **`modelo.py`**: Carga y renderiza geometría 3D externa.

*   **`ui/`**:
    *   Sistema de interfaz de usuario propio renderizado sobre OpenGL.
    *   Permite la selección de dispositivos de audio y ajuste de parámetros (colores, sensibilidad, bloom) en tiempo real.

---

## 📄 Licencia

Este proyecto se distribuye bajo la licencia **GNU General Public License v3 (GPLv3)**.
Puedes ver el texto completo de la licencia en el archivo `LICENSE` (si aplica) o en gnu.org.

---
*Desarrollado con pasión por el código limpio y los gráficos de alto rendimiento.*