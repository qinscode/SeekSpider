import socketio

from plombery.config import settings

# Get the allowed origins for websocket CORS
if settings.allowed_origins == "*":
    # When allowed_origins is *, allow common development origins
    # Allow both the configured frontend_url and common dev server ports
    cors_allowed_origins = [
        "http://localhost:5173",  # Vite dev server default
        "http://localhost:3000",  # React/Next.js dev server default
        "http://localhost:8000",  # Backend/production default
        "http://127.0.0.1:8000",  # Backend with 127.0.0.1
    ]
else:
    cors_allowed_origins = [
        f"{origin.scheme}://{origin.host}{(':' + str(origin.port)) if origin.port else ''}"
        for origin in settings.allowed_origins
    ]

sio = socketio.AsyncServer(async_mode="asgi", cors_allowed_origins=cors_allowed_origins)
asgi = socketio.ASGIApp(socketio_server=sio, socketio_path="/ws")
