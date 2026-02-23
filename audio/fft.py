# audio/fft.py
# ============================================================================
# Procesamiento FFT (Fast Fourier Transform)
# ============================================================================
# Encapsula la matemática para convertir audio en espectro de frecuencias.
# Incluye ventaneo (Hann) para suavidad y mapeo logarítmico para musicalidad.
# ============================================================================

import numpy as np

class FFTProcessor:
    def __init__(self, window_size=1024):
        self.window_size = window_size
        
        # 1. Ventana de Hann
        # Se multiplica por la señal para suavizar los bordes del buffer y 
        # reducir el "spectral leakage" (ruido en la FFT).
        self.window = np.hanning(window_size)
        
        # Datos para la FFT
        self.fft_size = window_size // 2 + 1
        self.fft_indices = np.arange(self.fft_size)
        
        # Caché para interpolación
        self.last_output_size = 0
        self.log_indices = None

    def process(self, audio_buffer, output_size, gain_min, gain_max):
        """
        Realiza la FFT y devuelve el espectro en bandas logarítmicas.
        """
        # 2. Aplicar Ventana
        # Asumimos que audio_buffer ya tiene el tamaño correcto (window_size)
        windowed = audio_buffer * self.window
        
        # 3. FFT
        # Obtenemos la magnitud del espectro (solo parte real positiva)
        fft_spectrum = np.abs(np.fft.rfft(windowed))
        
        # 4. Aplicar Ganancia Lineal (Pre-interpolación)
        # Aplicamos la rampa de ganancia sobre los bins lineales de la FFT.
        gain_ramp = np.linspace(gain_min, gain_max, len(fft_spectrum))
        fft_spectrum *= gain_ramp
        
        # 5. Mapeo a Bandas Logarítmicas
        # Recalcular índices si cambió el tamaño de salida (ej. redimensionar ventana)
        if output_size != self.last_output_size:
            # geomspace genera puntos espaciados logarítmicamente (exponencialmente)
            self.log_indices = np.geomspace(1, self.fft_size - 1, output_size)
            self.last_output_size = output_size
            
        # Interpolamos el espectro lineal en las coordenadas logarítmicas
        return np.interp(self.log_indices, self.fft_indices, fft_spectrum)