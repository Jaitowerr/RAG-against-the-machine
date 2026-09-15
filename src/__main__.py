"""Program entry point."""

import fire

from .CLI import CLI


if __name__ == "__main__":
    fire.Fire(CLI)
