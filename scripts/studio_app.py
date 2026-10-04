"""Compatibility entry point for the managed Studio; safe to import."""


def main():
    from studio_runtime import main as runtime_main
    runtime_main()


if __name__ == "__main__":
    main()
