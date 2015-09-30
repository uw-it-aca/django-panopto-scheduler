from nameparser import HumanName


def display_name(first_name, surname, reverse=False):
    name = HumanName("%s %s" % (first_name, surname))
    name.capitalize()
    name.string_format = "{last}, {first}" if (
        reverse is True) else "{first} {last}"
    return unicode(name)
