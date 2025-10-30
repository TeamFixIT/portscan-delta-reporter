import queue
from collections import defaultdict
from flask import url_for

# Import logger from centralized logging config
from app.logging_config import get_logger

logger = get_logger(__name__)


class SSEManager:
    def __init__(self):
        self.clients = []  # All clients
        self.user_clients = defaultdict(list)  # user_id -> [queues]

    def add_client(self, client_queue, user_id=None):
        """Add a client queue, optionally associated with a user."""
        self.clients.append(client_queue)
        if user_id:
            self.user_clients[user_id].append(client_queue)

    def remove_client(self, client_queue, user_id=None):
        """Remove a client queue."""
        if client_queue in self.clients:
            self.clients.remove(client_queue)
        if user_id and client_queue in self.user_clients[user_id]:
            self.user_clients[user_id].remove(client_queue)
            if not self.user_clients[user_id]:
                del self.user_clients[user_id]

    def broadcast(self, data):
        """Send to all clients."""
        for client_queue in self.clients[:]:
            try:
                client_queue.put_nowait(data)
            except queue.Full:
                pass

    def send_to_user(self, user_id, data):
        """Send event to all sessions of a specific user."""
        for client_queue in self.user_clients.get(user_id, []):
            try:
                client_queue.put_nowait(data)
            except queue.Full:
                pass

    def redirect_user(self, user_id, endpoint, **url_kwargs):
        """Redirect a specific user to a page."""

        redirect_url = url_for(endpoint, **url_kwargs)
        event_data = {"type": "redirect", "url": redirect_url, "endpoint": endpoint}
        self.send_to_user(user_id, event_data)

    def broadcast_redirect(self, endpoint, **url_kwargs):
        """Redirect all clients."""

        redirect_url = url_for(endpoint, **url_kwargs)
        event_data = {"type": "redirect", "url": redirect_url, "endpoint": endpoint}
        self.broadcast(event_data)

    def broadcast_alert(self, message, alert_type="info"):
        """Broadcast an alert message to all clients."""
        alert_data = {
            "message": message,
            "type": alert_type,  # 'info', 'warning', 'error', 'success'
        }
        self.broadcast(alert_data)


sse_manager = SSEManager()
