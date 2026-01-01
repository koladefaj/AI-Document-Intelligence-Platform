import asyncio
import json
import logging
import redis.asyncio as aioredis
from fastapi import WebSocket, WebSocketDisconnect
from app.infrastructure.config import settings
from typing import Dict

# Initialize logger for real-time events
logger = logging.getLogger(__name__)

class ConnectionManager:
    def __init__(self):
        # Maps task_id to the active WebSocket connection
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, task_id: str, websocket: WebSocket):
        """Accepts the connection and initiates the Redis subscription loop."""
        await websocket.accept()
        self.active_connections[task_id] = websocket
        logger.info(f"WS: Client connected to track task {task_id}")
        
        try:
            # Start the listener loop
            await self.listen_to_redis(task_id, websocket)
        except WebSocketDisconnect:
            logger.info(f"WS: Client disconnected from task {task_id}")
        except Exception as e:
            logger.error(f"WS: Unexpected error for task {task_id}: {e}")
        finally:
            self.disconnect(task_id)

    def disconnect(self, task_id: str):
        """Removes the connection from the active tracking map."""
        if task_id in self.active_connections:
            del self.active_connections[task_id]
            logger.debug(f"WS: Cleaned up connection for task: {task_id}")

    async def listen_to_redis(self, task_id: str, websocket: WebSocket):
        """
        Subscribes to a Redis channel specific to a task.
        Streams messages from the Worker directly to the User's browser.
        """
        # Connect to Redis using the same URL as Celery
        redis = aioredis.from_url(settings.redis_url, decode_responses=True)
        pubsub = redis.pubsub()
        channel_name = f"notifications_{task_id}"
        
        await pubsub.subscribe(channel_name)

        try:
            # The async iterator handles message retrieval non-blockingly
            async for message in pubsub.listen():
                if message["type"] == "message":
                    data = json.loads(message["data"])
                    
                    # Push data to the UI (e.g., partial summaries or status updates)
                    await websocket.send_json(data)
                    
                    # Self-terminate the connection once the task hits a terminal state
                    if data.get("status") in ["COMPLETED", "FAILED", "SUCCESS"]:
                        logger.info(f"WS: Terminal state reached for {task_id}. Closing.")
                        break
        finally:
            # --- CRITICAL CLEANUP ---
            # Unsubscribing ensures we don't leak memory in the Redis server
            await pubsub.unsubscribe(channel_name)
            await redis.close()
            logger.debug(f"WS: Redis pubsub closed for {task_id}")

# Global instance to be used in the WebSocket router
manager = ConnectionManager()