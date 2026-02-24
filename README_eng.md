# RHL - Real High Level Audio Visualizer

**RHL** is a high-performance audio visualizer developed in Python 3.13. Unlike traditional visualizers, RHL abandons the old fixed pipeline to utilize **Modern OpenGL (Core Profile 3.3)**, leveraging hardware acceleration (GPU) via programmable Shaders (GLSL) to render millions of particles, post-processing effects (Bloom), and 3D models in real-time.

The system features a hybrid audio engine capable of capturing both desktop audio (Loopback/WASAPI) and physical microphones with ultra-low latency.

---

## 🚀 Key Features

*   **Modern Rendering:** Uses `PyOpenGL` and `Pygame` with Core Profile 3.3 context. All drawing is done via VBOs, VAOs, and custom Shaders.
*   **Hybrid Audio Engine:**
    *   **SoundCard:** For high-fidelity system audio capture (Loopback).
    *   **SoundDevice:** For low-latency microphone input via Callbacks.
*   **Reactive Visual Effects:**
    *   **Spectral Tunnel:** Frequency visualization mapped to polar coordinates.
    *   **Starfields:** Particles reacting independently to bass and treble energy.
    *   **3D Model:** Model loading (OBJ/GLB) with lighting and rhythm-reactive movement.
*   **Post-Processing:** Implementation of **Bloom** effect (glow) using Framebuffer Objects (FBO) and Gaussian blur shaders.
*   **Custom UI:** Configuration interface rendered on GPU, allowing parameter adjustments in real-time without stopping the visualization.

---

## 📋 System Requirements

*   **Operating System:** Windows 10/11 (Recommended for WASAPI support).
*   **Python:** Version **3.13** (64-bit).
*   **GPU:** Graphics card compatible with **OpenGL 3.3** or higher.
*   **Drivers:** Updated GPU drivers (NVIDIA/AMD/Intel).

### Dependencies
The project depends on the following key libraries (see `requirements.txt`):
*   `numpy`: Mathematical processing and FFT.
*   `pygame`: Window creation and GL context.
*   `PyOpenGL`: OpenGL bindings.
*   `pyrr`: 3D Mathematics (Matrices, Vectors, Quaternions).
*   `SoundCard` & `sounddevice`: Audio capture.
*   `trimesh` & `pillow`: 3D model and texture loading/processing.

---

## 🛠️ Installation

1.  **Clone the repository or download the source code.**

2.  **Create a virtual environment (Optional but recommended):**
    ```bash
    python -m venv venv_rhl
    .\venv_rhl\Scripts\Activate.ps1  # In PowerShell
    ```

3.  **Install dependencies:**
    Make sure you are in the project root folder where `requirements.txt` is located.
    ```bash
    python -m pip install --upgrade pip
    python -m pip install -r requirements.txt
    ```

4.  **Run the application:**
    ```bash
    python main.py
    ```

---

## 📂 Project Structure

The software architecture is modular to facilitate scalability:

*   **`main.py`**: Entry point. Initializes the Pygame context, configures OpenGL, and runs the main loop (Events -> Update -> Render).

*   **`core/`**:
    *   Global state management (`Context`).
    *   Time and delta-time management (`TimeManager`).

*   **`audio/`**:
    *   **`engine.py`**: Orchestrates audio capture, unifying `SoundCard` and `SoundDevice` backends.
    *   **`fft.py`**: Performs Fast Fourier Transform, applies windowing (Hanning), and logarithmic smoothing.

*   **`render/`**:
    *   **`renderer.py`**: The graphics heart. Manages the 3D scene, tunnel, and particles.
    *   **`shaders.py`**: Loader and compiler for GLSL programs (`.vert`, `.frag`).
    *   **`postprocess.py`**: Handles FBOs for the Bloom effect.
    *   **`modelo.py`**: Loads and renders external 3D geometry.

*   **`ui/`**:
    *   Custom user interface system rendered over OpenGL.
    *   Allows audio device selection and parameter adjustment (colors, sensitivity, bloom) in real-time.

---

## 📄 License

This project is distributed under the **GNU General Public License v3 (GPLv3)**.
You can view the full text of the license in the `LICENSE` file (if applicable) or at gnu.org.

---
*Developed with passion for clean code and high-performance graphics.*