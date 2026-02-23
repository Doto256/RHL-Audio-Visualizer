# core/time.py
# ============================================================================
# Sistema de Tiempo
# ============================================================================
# Maneja el control de FPS y el cálculo de delta_time para la aplicación.
# ============================================================================

import pygame

class TimeManager:
    def __init__(self):
        self.clock = pygame.time.Clock()
        self.delta_time = 0.0
        self.start_time = pygame.time.get_ticks()

    def tick(self, fps):
        """
        Avanza el reloj y calcula el tiempo transcurrido desde el último frame.
        Args:
            fps (int): Frames por segundo objetivo.
        Returns:
            float: Delta time en segundos.
        """
        self.delta_time = self.clock.tick(fps) / 1000.0
        return self.delta_time

    def get_fps(self):
        """Devuelve los FPS actuales."""
        return self.clock.get_fps()
    
    def get_time(self):
        """Devuelve el tiempo total de ejecución en milisegundos."""
        return pygame.time.get_ticks()
