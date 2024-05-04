# ModelActivityMiddleware.py
# from django.middleware import
from threading import local


_thread_locals = local()


class ModelActivityMiddleware:
    def __init__(self, get_response=None):
        self.get_response = get_response

    def __call__(self, request):
        _thread_locals.request = (
            request
        )
        if hasattr(self, "process_request"):
            response = self.process_request(request)
        response = response or self.get_response(request)
        if hasattr(self, "process_response"):
            response = self.process_response(request, response)
        return response
