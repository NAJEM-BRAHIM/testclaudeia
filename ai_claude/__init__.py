# -*- encoding: utf-8 -*-

from . import models
from . import utils


def post_init_hook(cr, registry):
    """Post-installation hook to ensure proper module initialization."""
    # This hook can be used for any post-installation setup if needed
    pass

