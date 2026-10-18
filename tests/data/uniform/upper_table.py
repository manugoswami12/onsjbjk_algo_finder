import string


def shout(text):
    return text.translate(str.maketrans(string.ascii_lowercase, string.ascii_uppercase))
