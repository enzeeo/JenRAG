def ingest():
    from .ingest import main

    return main()


def scrape():
    from .scrape import main

    return main()


def scrape_all(*args, **kwargs):
    from .scrape import scrape_all as scrape_all_function

    return scrape_all_function(*args, **kwargs)
