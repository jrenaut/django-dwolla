# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required


class LoginRequiredMixin(object):
    """
    View mixin which requires that the user is authenticated.
    """
    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super(LoginRequiredMixin, self).dispatch(*args, **kwargs)
