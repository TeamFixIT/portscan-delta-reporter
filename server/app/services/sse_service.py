import queue
import logging

logger = logging.getLogger(__name__)


class SSEManager:
    def __init__(self):
        self.clients = []

    def add_client(self, client_queue):
        """Add a new client queue"""
        self.clients.append(client_queue)
        logger.info(f"Client connected. Total clients: {len(self.clients)}")

    def remove_client(self, client_queue):
        """Remove a client queue"""
        if client_queue in self.clients:
            self.clients.remove(client_queue)
            logger.info(f"Client disconnected. Total clients: {len(self.clients)}")

    def broadcast_alert(self, message, alert_type="info"):
        """Broadcast alert to all connected clients"""
        logger.info(f"Broadcasting alert to {len(self.clients)} clients: {message}")

        alert_data = {
            "message": message,
            "type": alert_type,  # 'info', 'warning', 'error', 'success'
        }

        # Send to all clients
        disconnected = []
        for client_queue in self.clients:
            try:
                client_queue.put(alert_data, block=False)
            except queue.Full:
                logger.warning("Client queue full, marking for removal")
                disconnected.append(client_queue)

        # Clean up disconnected clients
        for client_queue in disconnected:
            self.remove_client(client_queue)

    def get_client_count(self):
        """Get number of connected clients"""
        return len(self.clients)


# Global SSE manager instance
sse_manager = SSEManager()
