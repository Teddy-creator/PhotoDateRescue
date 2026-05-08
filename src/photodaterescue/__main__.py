"""Module entrypoint for python -m photodaterescue."""

from .cli import main


if __name__ == "__main__":
    raise SystemExit(main())
