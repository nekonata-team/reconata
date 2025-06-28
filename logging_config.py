def load_logging_config(level: int | None = None):
    import logging

    logging.basicConfig(
        level=level or logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
