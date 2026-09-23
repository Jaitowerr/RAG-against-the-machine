# src/progress.py
from collections.abc import Iterable
from typing import Any

from tqdm import tqdm


class StyledBar(tqdm):
    """Barra de progreso con el estilo único del proyecto (el 'css')."""

    STYLE: dict[str, Any] = {
        "ncols": 150,    # ancho fijo: no ocupa toda la pantalla
        "ascii": " #",  # relleno '#', vacío con espacios (como el subject)
    }

    def __init__(
        self,
        iterable: Iterable[Any] | None = None,
        **kwargs: Any,
    ) -> None:
        for key, value in self.STYLE.items():
            kwargs.setdefault(key, value)
        super().__init__(iterable, **kwargs)
