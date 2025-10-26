"""
WebSocket service for bidirectional communication
"""

from flask_socketio import emit
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class WebSocketService:
    def __init__(self, socketio=None):
        self.socketio = socketio
        self.connected_users = {}

    def init_app(self, socketio):
        """initialise with SocketIO instance"""
        self.socketio = socketio
        logger.info("WebSocket service initialised")

    def register_connection(self, user_id, session_id):
        """Register a new WebSocket connection"""
        if user_id not in self.connected_users:
            self.connected_users[user_id] = []

        # Check if session already exists
        for session in self.connected_users[user_id]:
            if session["sid"] == session_id:
                session["last_heartbeat"] = datetime.utcnow()
                return

        # Add new session
        self.connected_users[user_id].append(
            {
                "sid": session_id,
                "last_heartbeat": datetime.utcnow(),
                "connected_at": datetime.utcnow(),
            }
        )
        logger.info(f"User {user_id} connected via WebSocket (session: {session_id})")

    def unregister_connection(self, user_id, session_id):
        """Unregister a WebSocket connection"""
        if user_id in self.connected_users:
            self.connected_users[user_id] = [
                session
                for session in self.connected_users[user_id]
                if session["sid"] != session_id
            ]

            # Remove user if no more sessions
            if not self.connected_users[user_id]:
                del self.connected_users[user_id]

            logger.info(
                f"User {user_id} disconnected from WebSocket (session: {session_id})"
            )

    def update_heartbeat(self, user_id, session_id=None):
        """Update last heartbeat timestamp for a user/session"""
        if user_id in self.connected_users:
            if session_id:
                # Update specific session
                for session in self.connected_users[user_id]:
                    if session["sid"] == session_id:
                        session["last_heartbeat"] = datetime.utcnow()
                        break
            else:
                # Update all sessions for user
                for session in self.connected_users[user_id]:
                    session["last_heartbeat"] = datetime.utcnow()

    def send_alert(self, user_id, message, category="info", room=None):
        """
        Send a alert to a specific user or room
        """
        alert_data = {
            "message": message,
            "category": category,
            "timestamp": datetime.utcnow().isoformat(),
        }

        if room:
            self.socketio.emit("alert", alert_data, room=room)
            logger.info(f"Alert sent to room {room}: {message}")
        elif user_id and user_id in self.connected_users:
            # Send to all sessions of the user
            for session in self.connected_users[user_id]:
                self.socketio.emit("alert", alert_data, room=session["sid"])
            logger.info(f"Alert sent to user {user_id}: {message}")
        else:
            logger.warning(f"Failed to send alert - user {user_id} not connected")

    def broadcast_alert(self, message, category="info"):
        """Broadcast alert to all connected users"""
        alert_data = {
            "message": message,
            "category": category,
            "timestamp": datetime.utcnow().isoformat(),
        }

        # Use the socketio instance to broadcast
        self.socketio.emit("alert", alert_data)
        logger.info(f"Broadcast alert: {message}")

    def get_connection_health(self, user_id=None):
        """
        Get connection health status
        """
        if user_id:
            if user_id in self.connected_users:
                sessions_health = []
                for session in self.connected_users[user_id]:
                    last_heartbeat = session.get("last_heartbeat")
                    if last_heartbeat:
                        seconds_since = (
                            datetime.utcnow() - last_heartbeat
                        ).total_seconds()
                        status = "healthy" if seconds_since < 30 else "degraded"
                    else:
                        status = "unknown"

                    sessions_health.append(
                        {
                            "session_id": session["sid"],
                            "status": status,
                            "last_heartbeat": (
                                last_heartbeat.isoformat() if last_heartbeat else None
                            ),
                            "connected_at": session["connected_at"].isoformat(),
                        }
                    )

                return {
                    "connected": True,
                    "user_id": user_id,
                    "sessions": sessions_health,
                    "total_sessions": len(sessions_health),
                }
            return {"connected": False, "user_id": user_id, "status": "disconnected"}
        else:
            # Return overall health
            total_users = len(self.connected_users)
            total_sessions = sum(
                len(sessions) for sessions in self.connected_users.values()
            )

            healthy_sessions = 0
            for user_sessions in self.connected_users.values():
                for session in user_sessions:
                    if (
                        session.get("last_heartbeat")
                        and (
                            datetime.utcnow() - session["last_heartbeat"]
                        ).total_seconds()
                        < 30
                    ):
                        healthy_sessions += 1

            return {
                "total_users": total_users,
                "total_sessions": total_sessions,
                "healthy_sessions": healthy_sessions,
                "status": (
                    "healthy" if healthy_sessions == total_sessions else "degraded"
                ),
            }

    def get_connected_users_count(self):
        """Get count of currently connected users"""
        return len(self.connected_users)

    def get_active_sessions_count(self):
        """Get count of all active sessions"""
        return sum(len(sessions) for sessions in self.connected_users.values())


# Global instance
websocket_service = WebSocketService()
