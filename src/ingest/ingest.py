"""Backward-compatible full rebuild alias for `embed-all`."""

from src.ingest.embed import main_embed_all as main


if __name__ == "__main__":
    main()
