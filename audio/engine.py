# audio/engine.py
# ============================================================================
# Motor de Audio Híbrido (SoundDevice + SoundCard)
# ============================================================================
# Gestiona la captura de audio unificando dos backends:
# 1. SoundDevice (PortAudio): Para micrófonos físicos (baja latencia).
# 2. SoundCard (WASAPI/CoreAudio): Para Loopback/Desktop Audio.
#
# Mantiene la arquitectura de hilo único y buffer circular.
# ============================================================================

import threading
import time
import warnings
import queue
import numpy as np
import sounddevice as sd
import soundcard as sc
from .fft import FFTProcessor

# Ignoramos las advertencias de Soundcard para mantener la consola limpia
# y poder leer las métricas del Profiler sin interferencias.
warnings.filterwarnings("ignore", category=sc.SoundcardRuntimeWarning)

class AudioDeviceWrapper:
    """
    Clase contenedora para unificar la interfaz de dispositivos
    entre sounddevice y soundcard para la UI.
    """
    def __init__(self, name, is_loopback, backend, ref, sd_index=None):
        self.name = name
        self.isloopback = is_loopback
        self.backend = backend  # 'sd' (SoundDevice) o 'sc' (SoundCard)
        self.ref = ref          # Objeto original (SoundCard) o Info Dict (SoundDevice)
        self.sd_index = sd_index # Índice numérico para SoundDevice

    def __repr__(self):
        return f"<AudioDeviceWrapper: {self.name} ({self.backend})>"

class SDMicrophoneStream:
    """
    Sistema de captura dedicado para micrófonos usando Callbacks (estilo Visualizador.py).
    Aísla la captura del hilo principal para evitar 'glitches' y ruidos por latencia.
    """
    def __init__(self, device_index, samplerate, blocksize, noise_gate_threshold=0.015):
        self.device_index = device_index
        self.samplerate = samplerate
        self.blocksize = blocksize
        self.noise_gate_threshold = noise_gate_threshold
        self.q = queue.Queue()
        self.stream = sd.InputStream(
            device=device_index,
            channels=1,
            samplerate=samplerate,
            blocksize=blocksize,
            callback=self._callback
        )

    def _callback(self, indata, frames, time, status):
        # El callback corre en un hilo de audio de alta prioridad.
        # Copiamos los datos y los pasamos a la cola inmediatamente.
        if status:
            pass # Ignoramos errores menores de buffer para evitar spam
        
        data = indata.copy()
        
        # Noise Gate: Si la señal es muy débil (ruido de fondo), la silenciamos completamente.
        if np.max(np.abs(data)) < self.noise_gate_threshold:
            data[:] = 0.0
            
        self.q.put(data)

    def start(self):
        self.stream.start()

    def stop(self):
        self.stream.stop()
        self.stream.close()

    def read(self):
        # Gestión de latencia: si se acumulan demasiados paquetes, descartamos los viejos
        if self.q.qsize() > 4:
            while self.q.qsize() > 1:
                self.q.get_nowait()
        
        try:
            return self.q.get(timeout=0.05)
        except queue.Empty:
            return np.zeros((self.blocksize, 1), dtype=np.float32)

class AudioEngine:
    def __init__(self, ctx):
        self.ctx = ctx
        self.window_size = 1024
        self.hop_size = 512 # Solapamiento del 50% (1024 / 2)
        self.fft = FFTProcessor(window_size=self.window_size)
        self.thread = None
        self.selected_mics = [] # Lista de micrófonos seleccionados
        
        # Buffer circular para overlap
        self.audio_buffer = np.zeros(self.window_size, dtype=np.float32)
        
        # Configuración de audio global
        self.samplerate = 48000

    def get_devices(self):
        """
        Devuelve una lista unificada de dispositivos disponibles.
        Filtra Micrófonos físicos vía SoundDevice y Loopbacks vía SoundCard.
        """
        devices = []
        
        # --- 1. SoundDevice (Micrófonos) ---
        # Intentamos filtrar por WASAPI en Windows para reducir duplicados y latencia
        preferred_api_index = -1
        try:
            hostapis = sd.query_hostapis()
            for i, api in enumerate(hostapis):
                if 'WASAPI' in api['name']:
                    preferred_api_index = i
                    break
        except: pass

        try:
            sd_devs = sd.query_devices()
            for i, dev in enumerate(sd_devs):
                # Filtramos inputs que tengan canales de entrada
                if dev['max_input_channels'] > 0:
                    # Si detectamos WASAPI, ignoramos dispositivos de otras APIs (MME, DS)
                    if preferred_api_index != -1 and dev['hostapi'] != preferred_api_index:
                        continue

                    devices.append(AudioDeviceWrapper(
                        name=f"[Mic] {dev['name']}",
                        is_loopback=False,
                        backend='sd',
                        ref=dev,
                        sd_index=i
                    ))
        except Exception as e:
            print(f"⚠️ Error inicializando SoundDevice: {e}")

        # --- 2. SoundCard (Loopback / Parlantes) ---
        try:
            sc_devs = sc.all_microphones(include_loopback=True)
            for dev in sc_devs:
                if dev.isloopback:
                    devices.append(AudioDeviceWrapper(
                        name=f"[PC] {dev.name}",
                        is_loopback=True,
                        backend='sc',
                        ref=dev
                    ))
        except Exception as e:
            print(f"⚠️ Error inicializando SoundCard: {e}")
            
        return devices

    def set_devices(self, devices):
        """Establece los dispositivos activos para captura."""
        self.selected_mics = devices

    def start(self):
        """Inicia el hilo de captura de audio."""
        if self.thread is None or not self.thread.is_alive():
            self.thread = threading.Thread(target=self._loop, daemon=True)
            self.thread.start()

    def _loop(self):
        """Loop principal de captura de audio (corre en hilo secundario)."""
        while self.ctx.running:
            # Si no hay visualizador activo o no hay micros, esperar
            if not self.ctx.activo or not self.selected_mics:
                time.sleep(0.1)
                continue

            # Listas para gestionar los streams activos
            active_sd_streams = []
            active_sc_recorders = []
            
            # --- FASE DE INICIALIZACIÓN DE STREAMS ---
            for mic in self.selected_mics:
                try:
                    if mic.backend == 'sd':
                        # Usamos el nuevo sistema de captura con callback
                        stream = SDMicrophoneStream(
                            device_index=mic.sd_index,
                            samplerate=self.samplerate,
                            blocksize=self.hop_size
                        )
                        stream.start()
                        active_sd_streams.append(stream)
                        
                    elif mic.backend == 'sc':
                        # Inicializar SoundCard Recorder
                        # SoundCard usa context managers
                        rec = mic.ref.recorder(
                            samplerate=self.samplerate, 
                            channels=1, 
                            blocksize=self.hop_size
                        )
                        rec.__enter__()
                        active_sc_recorders.append(rec)
                        
                except Exception as e:
                    print(f"⚠️ Error al abrir dispositivo {mic.name}: {e}")

            if not active_sd_streams and not active_sc_recorders:
                time.sleep(0.5)
                continue

            try:
                # --- BUCLE DE LECTURA EN TIEMPO REAL ---
                while self.ctx.running and self.ctx.activo:
                    audios = []
                    
                    # 1. Leer de SoundDevice (Queue/Callback)
                    for stream in active_sd_streams:
                        # read() ahora gestiona la cola y devuelve (blocksize, 1)
                        data = stream.read()
                        audios.append(data.flatten())
                    
                    # 2. Leer de SoundCard (Bloqueante)
                    # Si SD ya esperó, el buffer de SC debería estar lleno y retornar rápido.
                    for rec in active_sc_recorders:
                        try:
                            data = rec.record(numframes=self.hop_size)
                            # data shape: (hop_size, 1)
                            audios.append(data.flatten())
                        except Exception:
                            break

                    if audios:
                        # Mezclar y procesar
                        # Promediamos todas las fuentes activas
                        audio_combined = np.mean(audios, axis=0)
                        
                        # Actualizar Buffer Circular (Overlap)
                        self.audio_buffer = np.roll(self.audio_buffer, -self.hop_size)
                        self.audio_buffer[-self.hop_size:] = audio_combined
                        
                        self._actualizar_espectro(self.audio_buffer)
                    
                    # No usamos sleep aquí porque las lecturas de audio ya bloquean 
                    # el tiempo exacto necesario (hop_size / samplerate).
            finally:
                # --- LIMPIEZA DE RECURSOS ---
                for stream in active_sd_streams:
                    try:
                        stream.stop()
                        stream.close()
                    except: pass
                
                for rec in active_sc_recorders:
                    try:
                        rec.__exit__(None, None, None)
                    except: pass

    def _actualizar_espectro(self, mono_buffer):
        """Procesa FFT y actualiza el estado en el contexto."""
        with self.ctx.profiler.region("audio_fft"):
            # Acceso a configuración a través de UI (si existe) o valores por defecto
            gain_min = 0.3
            gain_max = 2.0
            if self.ctx.ui:
                gain_min = self.ctx.ui.config["gain_min"]
                gain_max = self.ctx.ui.config["gain_max"]

            # Usamos un tamaño fijo para el espectro. Esto evita que al redimensionar la ventana
            # (VIDEORESIZE) se resetee el array de audio a ceros, lo que hacía desaparecer el túnel.
            SPECTRUM_SIZE = 1024

            # Procesamiento FFT (Ventana, FFT, Ganancia, Interpolación Logarítmica)
            # Delegamos la matemática pesada al módulo FFT
            log_spectrum = self.fft.process(mono_buffer, SPECTRUM_SIZE, gain_min, gain_max)
            
            # Compresión de rango dinámico (Logaritmo de amplitud)
            np.log1p(log_spectrum, out=log_spectrum)
            
            # Normalización
            # Noise Gate: Si el pico máximo es muy bajo (silencio/ruido de fondo), forzamos a cero.
            max_val = np.max(log_spectrum)
            if max_val < 0.1:
                norm = np.zeros_like(log_spectrum)
            else:
                norm = log_spectrum / (max_val + 1e-6)
            
            # --- Cálculo de Energía de Graves ---
            # Tomamos el promedio de las primeras 4 bandas (frecuencias más bajas)
            # y aplicamos un suavizado (lerp) para evitar parpadeos bruscos.
            bass_instant = 0.0
            if len(norm) > 4:
                val = np.mean(norm[:4])
                if not np.isnan(val):
                    bass_instant = val
            
            # Suavizado Asimétrico: Ataque rápido (brusco), Decaimiento lento (suave)
            if bass_instant > self.ctx.bass_energy:
                self.ctx.bass_energy = self.ctx.bass_energy * 0.4 + bass_instant * 0.6
            else:
                self.ctx.bass_energy = self.ctx.bass_energy * 0.95 + bass_instant * 0.05
            
            # --- Cálculo de Energía de Agudos (Platos/S) ---
            # Tomamos el promedio de las bandas altas (último 25% del espectro)
            high_instant = 0.0
            if len(norm) > 0:
                start_idx = int(len(norm) * 0.75)
                val_h = np.mean(norm[start_idx:])
                if not np.isnan(val_h):
                    high_instant = val_h
            
            if high_instant > self.ctx.high_energy:
                self.ctx.high_energy = self.ctx.high_energy * 0.4 + high_instant * 0.6
            else:
                self.ctx.high_energy = self.ctx.high_energy * 0.95 + high_instant * 0.05

            # Ajuste de tamaño si cambió la ventana
            if len(self.ctx.espectro) != SPECTRUM_SIZE:
                self.ctx.espectro = np.zeros(SPECTRUM_SIZE, dtype=float)
                self.ctx.eco = np.zeros(SPECTRUM_SIZE, dtype=float)
                
            # Efecto eco y suavizado
            np.copyto(self.ctx.eco, self.ctx.espectro)
            self.ctx.espectro *= 0.85
            self.ctx.espectro += 0.15 * norm
