# eduplatform_config/asgi.py
import os
from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application
import activity.routing   # هنستدعي منه المسارات الخاصة بالـ websocket

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "eduplatform_config.settings")

django_asgi_app = get_asgi_application()

application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": AuthMiddlewareStack(
        URLRouter(
            activity.routing.websocket_urlpatterns
        )
    ),
})
