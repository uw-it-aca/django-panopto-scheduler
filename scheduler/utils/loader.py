# Copyright 2022 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0

from django.conf import settings
from importlib import import_module


def load_class_from_module_setting(
        module_name_setting, class_name, *args, **kwargs):
    module_name = getattr(settings, module_name_setting)
    if module_name is None:
        raise Exception("Missing setting: {}".format(module_name_setting))

    try:
        module = import_module(module_name)
        return getattr(module, class_name)(*args, **kwargs)
    except Exception as ex:
        raise Exception(
            "Cannot load module {}: {}".format(module_name, ex))
