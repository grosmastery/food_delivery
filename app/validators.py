import re

NAME_RE = re.compile(r"^[^\W\d_]+(?:[-'’ʼ ][^\W\d_]+)*$")
PHONE_NUMBER_RE = re.compile(r"[0-9]{10}")


def is_valid_name(name):
    return bool(name) and NAME_RE.match(name) is not None


def is_valid_phone_number(phone_number):
    return bool(phone_number) and PHONE_NUMBER_RE.fullmatch(phone_number) is not None
