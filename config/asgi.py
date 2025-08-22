"""
ASGI config for mate project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/dev/howto/deployment/asgi/

"""

import os
import sys
from pathlib import Path

from django.core.asgi import get_asgi_application
from whitenoise import WhiteNoise

# This allows easy placement of apps within the interior
# mate directory.
BASE_DIR = Path(__file__).resolve(strict=True).parent.parent
sys.path.append(str(BASE_DIR / "mate"))

# If DJANGO_SETTINGS_MODULE is unset, default to the local settings
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")

# This application object is used by any ASGI server configured to use this file.
django_asgi_app = get_asgi_application()

# Wrap with WhiteNoise for static file serving
django_application = WhiteNoise(
    django_asgi_app,
    root=str(BASE_DIR / "staticfiles"),
)

# Import websocket application here, so apps from django_application are loaded first
from config.websocket import websocket_application  # noqa: E402


async def application(scope, receive, send):
    if scope["type"] == "http":
        await django_application(scope, receive, send)
    elif scope["type"] == "websocket":
        await websocket_application(scope, receive, send)
    else:
        msg = f"Unknown scope type {scope['type']}"
        raise NotImplementedError(msg)
