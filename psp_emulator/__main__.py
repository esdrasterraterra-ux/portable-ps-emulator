from .emulator import PSPEmulator

if __name__ == "__main__":
    import sys
    from .main import main

    raise SystemExit(main(sys.argv[1:]))
