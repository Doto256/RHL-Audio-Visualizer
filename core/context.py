# core/context.py
# ============================================================================
# Contexto Central
# ============================================================================
# Clase que centraliza el estado de la aplicación y permite la comunicación
# entre módulos sin importaciones circulares.
# ============================================================================

import numpy as np
from .profiler import Profiler

class Context:
    def __init__(self):
        # Dimensiones de la ventana
        self.W = 800
        self.H = 600
        
        # Estado de ejecución
        self.running = True
        self.activo = False # Si el visualizador está activo (vs menú selección)
        
        # Datos de audio (Espectro)
        # Se inicializan en ceros
        self.espectro = np.zeros(800, dtype=float)
        self.eco = np.zeros(800, dtype=float)
        
        # Energía de graves (0.0 a 1.0) para efectos visuales (ej. estrellas)
        self.bass_energy = 0.0
        self.high_energy = 0.0 # Energía de agudos (Platos, S)
        
        # Estado visual global
        self.giro = 0.0 # Rotación del túnel
        
        # Referencias a los subsistemas (se asignan en main.py)
        self.audio = None
        self.renderer = None
        self.ui = None
        self.time = None
        self.profiler = Profiler()
