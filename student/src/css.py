# src/progress.py
"""Estilo unificado de barras de progreso: el 'css' del proyecto."""

from collections.abc import Iterable
from typing import Any, ClassVar

from tqdm import tqdm


class StyledBar(tqdm):
    """Barra de progreso con el estilo único del proyecto (el 'css').

    Los valores de STYLE se aplican a todas las barras; cualquier
    argumento recibido en la llamada tiene prioridad (como un inline
    style sobre el css).

    Nota: `ascii` necesita al menos 2 caracteres. Con 1 solo, tqdm
    calcula len(charset) - 1 = 0 y muere con ZeroDivisionError.
    """

    STYLE: ClassVar[dict[str, Any]] = {
        "ncols": 150,       # ancho fijo: no ocupa toda la pantalla
        "ascii": " #",      # relleno '#', vacío con espacios (como el subject)
        "colour": "#83be83",
        "leave": True,      # la barra permanece impresa al terminar
    }

    def __init__(
        self,
        iterable: Iterable[Any] | None = None,
        **kwargs: Any,
    ) -> None:
        for key, value in self.STYLE.items():
            kwargs.setdefault(key, value)
        charset = kwargs.get("ascii")
        if charset is not None:
            self._check_ascii(charset)
        super().__init__(iterable, **kwargs)

    @staticmethod
    def _check_ascii(charset: str) -> None:
        if len(charset) < 2:
            raise ValueError(
                f"ascii necesita al menos 2 caracteres (recibido {charset!r}): "
                "tqdm hace divmod entre len(charset) - 1 y con 1 divide por cero."
            )
