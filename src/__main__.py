import fire
import sys

from .cli import CLI


if __name__ == "__main__":
    try:
        fire.Fire(CLI)

    except Exception as e:
        print("FALLO:")
        print('    -->  ', e)
        sys.exit(1)
