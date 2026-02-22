"""
ClawChat Port Rotation Module

Implements dynamic port allocation and rotation for enhanced security.
Features:
- Random port selection (49152-65535)
- Hourly port rotation with grace period
- Port conflict detection and retry
- Port change notification system
"""

import asyncio
import json
import logging
import random
import socket
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Set, Tuple, Callable
from pathlib import Path

logger = logging.getLogger(__name__)


class PortRotationError(Exception):
    """Base exception for port rotation errors."""
    pass


class PortUnavailableError(PortRotationError):
    """Raised when no available port can be found."""
    pass


class RotationState(Enum):
    """State of port rotation."""
    STABLE = "stable"          # Using current port
    PENDING = "pending"        # New port generated, not yet active
    TRANSITION = "transition"  # Both ports active (grace period)
    ROTATING = "rotating"      # Actively switching to new port


@dataclass
class PortInfo:
    """Information about a port."""
    port: int
    start_time: float
    end_time: float
    active: bool = True
    connections: Set[str] = field(default_factory=set)  # Connection IDs using this port
    
    @property
    def remaining_time(self) -> float:
        """Time remaining until port expires."""
        return max(0, self.end_time - time.time())
    
    @property
    def is_expired(self) -> bool:
        """Check if port has expired."""
        return time.time() > self.end_time


@dataclass
class RotationSchedule:
    """Port rotation schedule configuration."""
    rotation_interval: int = 3600  # 1 hour in seconds
    grace_period: int = 300        # 5 minutes in seconds
    advance_notice: int = 120      # 2 minutes before rotation
    max_port_age: int = 3900       # 65 minutes (rotation + grace)
    
    min_port: int = 49152          # IANA ephemeral port range start
    max_port: int = 65535          # IANA ephemeral port range end
    
    max_retries: int = 10          # Max attempts to find available port
    bind_address: str = "0.0.0.0"  # Address to bind for port checking


class PortRotationManager:
    """
    Manages dynamic port allocation and rotation.
    
    Features:
    1. Random port selection with availability checking
    2. Scheduled port rotation
    3. Grace period for existing connections
    4. Port change notifications
    5. Connection tracking
    """
    
    def __init__(
        self,
        schedule: Optional[RotationSchedule] = None,
        on_port_change: Optional[Callable[[int, int], None]] = None
    ):
        """
        Initialize port rotation manager.
        
        Args:
            schedule: Rotation schedule configuration
            on_port_change: Callback when port changes (old_port, new_port)
        """
        self.schedule = schedule or RotationSchedule()
        self.on_port_change = on_port_change
        
        # Current and next ports
        self.current_port: Optional[int] = None
        self.next_port: Optional[int] = None
        
        # Port history and state
        self.port_history: List[PortInfo] = []
        self.state: RotationState = RotationState.STABLE
        
        # Connection tracking
        self.connections: Dict[str, int] = {}  # connection_id -> port
        
        # Rotation task
        self._rotation_task: Optional[asyncio.Task] = None
        self._stop_event = asyncio.Event()
        
        logger.info(f"PortRotationManager initialized with schedule: {self.schedule}")
    
    def _is_port_available(self, port: int) -> bool:
        """
        Check if a port is available for binding.
        
        Args:
            port: Port number to check
            
        Returns:
            True if port is available, False otherwise
        """
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        try:
            sock.bind((self.schedule.bind_address, port))
            sock.close()
            return True
        except (OSError, socket.error) as e:
            logger.debug(f"Port {port} unavailable: {e}")
            return False
        finally:
            try:
                sock.close()
            except:
                pass
    
    def select_random_port(self) -> int:
        """
        Select a random available port.
        
        Returns:
            Available port number
            
        Raises:
            PortUnavailableError: If no available port found after max_retries
        """
        for attempt in range(self.schedule.max_retries):
            # Generate random port in ephemeral range
            port = random.randint(self.schedule.min_port, self.schedule.max_port)
            
            # Skip if this port was recently used
            recent_ports = {p.port for p in self.port_history[-5:] if p.port}
            if port in recent_ports:
                continue
            
            # Check if port is available
            if self._is_port_available(port):
                logger.info(f"Selected port {port} (attempt {attempt + 1})")
                return port
            
            logger.debug(f"Port {port} not available, trying another...")
        
        raise PortUnavailableError(
            f"Could not find available port after {self.schedule.max_retries} attempts"
        )
    
    async def initialize(self, initial_port: Optional[int] = None) -> int:
        """
        Initialize with a port (random or specified).
        
        Args:
            initial_port: Optional specific port to use
            
        Returns:
            The port being used
        """
        if initial_port is None:
            self.current_port = self.select_random_port()
        else:
            if not self._is_port_available(initial_port):
                raise PortUnavailableError(f"Port {initial_port} is not available")
            self.current_port = initial_port
        
        # Create port info
        start_time = time.time()
        end_time = start_time + self.schedule.rotation_interval
        
        port_info = PortInfo(
            port=self.current_port,
            start_time=start_time,
            end_time=end_time,
            active=True
        )
        
        self.port_history.append(port_info)
        logger.info(f"Initialized with port {self.current_port}, "
                   f"rotation scheduled at {datetime.fromtimestamp(end_time)}")
        
        # Start rotation task
        self._rotation_task = asyncio.create_task(self._rotation_loop())
        
        return self.current_port
    
    async def _rotation_loop(self):
        """Main rotation loop that handles scheduled port changes."""
        logger.info("Port rotation loop started")
        
        try:
            while not self._stop_event.is_set():
                # Calculate time until next rotation
                current_info = self.port_history[-1]
                time_until_rotation = current_info.remaining_time
                
                if time_until_rotation <= 0:
                    # Time to rotate
                    await self._perform_rotation()
                elif time_until_rotation <= self.schedule.advance_notice:
                    # Generate next port in advance
                    await self._prepare_next_port()
                    
                    # Wait for rotation time
                    await asyncio.sleep(time_until_rotation)
                else:
                    # Wait until it's time to prepare next port
                    wait_time = time_until_rotation - self.schedule.advance_notice
                    await asyncio.sleep(min(wait_time, 60))  # Check at least every minute
        except asyncio.CancelledError:
            logger.info("Port rotation loop cancelled")
        except Exception as e:
            logger.error(f"Port rotation loop error: {e}", exc_info=True)
        finally:
            logger.info("Port rotation loop stopped")
    
    async def _prepare_next_port(self):
        """Prepare the next port before rotation."""
        if self.next_port is not None:
            return  # Already prepared
        
        try:
            self.next_port = self.select_random_port()
            self.state = RotationState.PENDING
            
            # Create port info for next port
            start_time = time.time() + self.schedule.advance_notice
            end_time = start_time + self.schedule.rotation_interval
            
            port_info = PortInfo(
                port=self.next_port,
                start_time=start_time,
                end_time=end_time,
                active=False  # Not active yet
            )
            
            self.port_history.append(port_info)
            
            logger.info(f"Prepared next port {self.next_port}, "
                       f"will activate at {datetime.fromtimestamp(start_time)}")
            
            # Notify about upcoming change
            if self.on_port_change:
                self.on_port_change(self.current_port, self.next_port)
                
        except PortUnavailableError as e:
            logger.error(f"Failed to prepare next port: {e}")
            # Try again in 30 seconds
            await asyncio.sleep(30)
            await self._prepare_next_port()
    
    async def _perform_rotation(self):
        """Perform the actual port rotation."""
        if self.next_port is None:
            logger.warning("No next port prepared, selecting one now")
            self.next_port = self.select_random_port()
        
        old_port = self.current_port
        new_port = self.next_port
        
        # Update state
        self.state = RotationState.TRANSITION
        self.current_port = new_port
        
        # Mark old port as inactive (but still in grace period)
        if self.port_history:
            old_info = self.port_history[-2] if len(self.port_history) > 1 else self.port_history[-1]
            old_info.active = False
            old_info.end_time = time.time() + self.schedule.grace_period
        
        # Mark new port as active
        new_info = self.port_history[-1]
        new_info.active = True
        new_info.start_time = time.time()
        
        logger.info(f"Rotated from port {old_port} to {new_port}")
        
        # Clear next port
        self.next_port = None
        
        # Start grace period timer
        asyncio.create_task(self._grace_period_timer(old_port))
        
        # Update state after grace period starts
        await asyncio.sleep(1)  # Brief delay
        self.state = RotationState.STABLE
    
    async def _grace_period_timer(self, old_port: int):
        """Timer for grace period after rotation."""
        await asyncio.sleep(self.schedule.grace_period)
        
        # Clean up old port connections
        self._cleanup_old_port(old_port)
        
        # Clean up old port history
        self._cleanup_port_history()
        
        logger.info(f"Grace period ended for port {old_port}")
    
    def _cleanup_old_port(self, old_port: int):
        """Clean up connections using old port."""
        connections_to_remove = [
            conn_id for conn_id, port in self.connections.items()
            if port == old_port
        ]
        
        for conn_id in connections_to_remove:
            del self.connections[conn_id]
        
        if connections_to_remove:
            logger.info(f"Cleaned up {len(connections_to_remove)} connections from old port {old_port}")
    
    def _cleanup_port_history(self):
        """Clean up old port history entries."""
        max_age = time.time() - self.schedule.max_port_age
        
        # Keep at least 2 entries (current and previous)
        while len(self.port_history) > 2 and self.port_history[0].end_time < max_age:
            removed = self.port_history.pop(0)
            logger.debug(f"Removed old port history: {removed.port}")
    
    def register_connection(self, connection_id: str, port: Optional[int] = None):
        """
        Register a connection using a specific port.
        
        Args:
            connection_id: Unique connection identifier
            port: Port being used (defaults to current port)
        """
        if port is None:
            port = self.current_port
        
        self.connections[connection_id] = port
        
        # Update port info
        for port_info in reversed(self.port_history):
            if port_info.port == port and port_info.active:
                port_info.connections.add(connection_id)
                break
    
    def unregister_connection(self, connection_id: str):
        """Unregister a connection."""
        port = self.connections.pop(connection_id, None)
        
        if port:
            # Update port info
            for port_info in self.port_history:
                if port_info.port == port:
                    port_info.connections.discard(connection_id)
                    break
    
    def get_connection_count(self, port: Optional[int] = None) -> int:
        """
        Get number of connections on a port.
        
        Args:
            port: Port to check (defaults to current port)
            
        Returns:
            Number of connections
        """
        if port is None:
            port = self.current_port
        
        count = sum(1 for p in self.connections.values() if p == port)
        return count
    
    def get_status(self) -> Dict:
        """Get current status of port rotation."""
        current_info = self.port_history[-1] if self.port_history else None
        
        return {
            "state": self.state.value,
            "current_port": self.current_port,
            "next_port": self.next_port,
            "connections": len(self.connections),
            "current_connections": self.get_connection_count(self.current_port),
            "rotation_in": current_info.remaining_time if current_info else 0,
            "port_history": [
                {
                    "port": info.port,
                    "start_time": info.start_time,
                    "end_time": info.end_time,
                    "active": info.active,
                    "connections": len(info.connections)
                }
                for info in self.port_history[-5:]  # Last 5 ports
            ]
        }
    
    async def rotate_now(self) -> Tuple[int, int]:
        """
        Force immediate port rotation.
        
        Returns:
            Tuple of (old_port, new_port)
        """
        if self.next_port is None:
            self.next_port = self.select_random_port()
        
        old_port = self.current_port
        await self._perform_rotation()
        
        return old_port, self.current_port
    
    async def stop(self):
        """Stop port rotation manager."""
        logger.info("Stopping port rotation manager")
        
        self._stop_event.set()
        
        if self._rotation_task:
            self._rotation_task.cancel()
            try:
                await self._rotation_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Port rotation manager stopped")


# Utility functions for standalone use

def find_available_port(
    min_port: int = 49152,
    max_port: int = 65535,
    max_attempts: int = 10,
    bind_address: str = "0.0.0.0"
) -> int:
    """
    Find an available port in the specified range.
    
    Args:
        min_port: Minimum port number
        max_port: Maximum port number
        max_attempts: Maximum attempts to find port
        bind_address: Address to bind for checking
        
    Returns:
        Available port number
        
    Raises:
        PortUnavailableError: If no available port found
    """
    manager = PortRotationManager(
        schedule=RotationSchedule(
            min_port=min_port,
            max_port=max_port,
            max_retries=max_attempts,
            bind_address=bind_address
        )
    )
    
    return manager.select_random_port()


def check_port_availability(port: int, bind_address: str = "0.0.0.0") -> bool:
    """
    Check if a specific port is available.
    
    Args:
        port: Port number to check
        bind_address: Address to bind for checking
        
    Returns:
        True if port is available, False otherwise
    """
    manager = PortRotationManager(
        schedule=RotationSchedule(bind_address=bind_address)
    )
    
    return manager._is_port_available(port)


# Async context manager for easy use

class PortRotationContext:
    """Context manager for port rotation."""
    
    def __init__(self, initial_port: Optional[int] = None):
        self.initial_port = initial_port
        self.manager: Optional[PortRotationManager] = None
    
    async def __aenter__(self) -> PortRotationManager:
        self.manager = PortRotationManager()
        await self.manager.initialize(self.initial_port)
        return self.manager
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.manager:
            await self.manager.stop()


if __name__ == "__main__":
    # Example usage
    async def example():
        print("Port Rotation Module Example")
        print("=" * 50)
        
        # Find an available port
        port = find_available_port()
        print(f"Found available port: {port}")
        
        # Check port availability
        available = check_port_availability(port)
        print(f"Port {port} available: {available}")
        
        # Use context manager
        async with PortRotationContext() as manager:
            print(f"\nInitialized with port: {manager.current_port}")
            print(f"Status: {manager.get_status()}")
            
            # Wait a bit to see rotation in action (shortened for example)
            await asyncio.sleep(5)
            
            # Force rotation
            old, new = await manager.rotate_now()
            print(f"\nForced rotation: {old} -> {new}")
            print(f"New status: {manager.get_status()}")
        
        print("\nExample completed")
    
    asyncio.run(example())