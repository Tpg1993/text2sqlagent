"""
SSE Manager for streaming agent progress to frontend.
"""
import asyncio
from typing import Dict, AsyncGenerator
import json

class SSEManager:
    def __init__(self):
        self.queues: Dict[str, asyncio.Queue] = {}
    
    def create_session(self, session_id: str) -> asyncio.Queue:
        """Create a new SSE session queue."""
        queue = asyncio.Queue()
        self.queues[session_id] = queue
        return queue
    
    async def send_event(self, session_id: str, event_type: str, data: dict):
        """Send an event to a specific session."""
        if session_id in self.queues:
            await self.queues[session_id].put({
                "event": event_type,
                "data": data
            })
    
    async def stream_events(self, session_id: str) -> AsyncGenerator[str, None]:
        """Stream events for a session."""
        queue = self.queues.get(session_id)
        if not queue:
            return
        
        try:
            while True:
                event = await queue.get()
                if event is None:  # Sentinel to close stream
                    break
                yield f"data: {json.dumps(event)}\n\n"
        finally:
            # Cleanup
            if session_id in self.queues:
                del self.queues[session_id]
    
    def close_session(self, session_id: str):
        """Close an SSE session."""
        if session_id in self.queues:
            self.queues[session_id].put_nowait(None)

# Global instance
sse_manager = SSEManager()
