from contextvars import ContextVar
from typing import Optional
import socketio

_sio_instance: ContextVar[Optional[socketio.AsyncServer]] = ContextVar('sio_instance', default=None)
_session_id: ContextVar[Optional[str]] = ContextVar('session_id', default=None)

class SocketIOContext:
    @staticmethod
    def set_context(sio: socketio.AsyncServer, sid: str):
        """Set the Socket.IO context for the current task"""
        _sio_instance.set(sio)
        _session_id.set(sid)
    
    @staticmethod
    def get_context() -> tuple[Optional[socketio.AsyncServer], Optional[str]]:
        """Get the current Socket.IO context"""
        return _sio_instance.get(), _session_id.get()
    
    @staticmethod
    async def emit(event: str, data: dict, **kwargs):
        """Emit an event using the current context"""
        sio, sid = SocketIOContext.get_context()
        if sio and sid:
            await sio.emit(event, data, room=sid, **kwargs)