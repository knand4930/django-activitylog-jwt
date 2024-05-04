import logging
from activitylog.models import CRUDEvent, LoginEvent, RequestEvent, CorsEvent

logger = logging.getLogger(__name__)


class ModelBackend:
    def request(self, request_info):
        return RequestEvent.objects.create(**request_info)

    def cors(self, cors_info):
        return CorsEvent.objects.create(**cors_info)

    def crud(self, crud_info):
        return CRUDEvent.objects.create(**crud_info)

    def login(self, login_info):
        return LoginEvent.objects.create(**login_info)
