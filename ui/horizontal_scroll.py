# ui/horizontal_scroll.py
class HorizontalScroll:
    def __init__(self, scroll_speed=30.0):
        self.offset_x = 0.0
        self.max_scroll = 0.0
        self.scroll_speed = scroll_speed

    def update_limits(self, content_width, view_width):
        """
        Recalcula los límites del scroll basado en el contenido y la vista.
        content_width: Ancho total de todas las pestañas.
        view_width: Ancho de la pantalla.
        """
        # El máximo scroll es lo que sobra del contenido
        self.max_scroll = max(0.0, content_width - view_width)
        
        # Asegurar que el offset actual no se salga de los nuevos límites (ej. al redimensionar)
        self.offset_x = max(0.0, min(self.offset_x, self.max_scroll))

    def scroll(self, delta):
        """
        Aplica el desplazamiento con la rueda del mouse.
        delta: Valor de evt.y (Positivo=Arriba, Negativo=Abajo en Pygame)
        """
        # Si movemos la rueda hacia abajo (negativo), queremos ver el contenido de la derecha.
        # Por lo tanto, el offset (cámara) debe aumentar.
        # Invertimos delta para que se sienta natural.
        self.offset_x -= delta * self.scroll_speed
        
        # Clamp (limitar) entre 0 y el máximo permitido
        self.offset_x = max(0.0, min(self.offset_x, self.max_scroll))

    def get_render_offset(self):
        """
        Retorna el valor para sumar a la coordenada X de dibujo.
        Como el offset es cuánto nos movimos a la derecha, debemos restar X para dibujar.
        """
        return -self.offset_x

    def should_show_left_arrow(self):
        """Muestra flecha izquierda si no estamos al principio."""
        return self.offset_x > 1.0

    def should_show_right_arrow(self):
        """Muestra flecha derecha si no hemos llegado al final."""
        return self.offset_x < self.max_scroll - 1.0
