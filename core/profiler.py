# core/profiler.py
# ============================================================================
# Sistema de Medición de Rendimiento
# ============================================================================
# Proporciona una forma sencilla de medir el tiempo de ejecución de bloques
# de código usando un gestor de contexto.
# ============================================================================

import time

class Profiler:
    def __init__(self):
        self.records = {}

    def region(self, name):
        return ProfileRegion(self, name)

    def get_results(self):
        return self.records

class ProfileRegion:
    def __init__(self, profiler, name):
        self.profiler = profiler
        self.name = name

    def __enter__(self):
        self.start_time = time.perf_counter()

    def __exit__(self, type, value, traceback):
        duration_ms = (time.perf_counter() - self.start_time) * 1000
        self.profiler.records[self.name] = duration_ms