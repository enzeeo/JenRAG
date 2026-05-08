def retrieve(*args, **kwargs):
    from .retriever import retrieve as retrieve_function

    return retrieve_function(*args, **kwargs)


def generate(*args, **kwargs):
    from .generator import generate as generate_function

    return generate_function(*args, **kwargs)


def ask(*args, **kwargs):
    from .generator import ask as ask_function

    return ask_function(*args, **kwargs)
