import socket
import json
import subprocess
import platform
import psutil
import threading
from enum import Enum
from typing import Any, Dict

class MessageType(Enum):
    COMMAND = "command"
    MESSAGE = "message"
    RESPONSE = "response"
    ERROR = "error"
    STATUS = "status"

class TerminalClient:
    def __init__(self, host='localhost', port=5000):
        self.host = host
        self.port = port
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.running = True

    def format_message(self, msg_type: MessageType, data: Any, metadata: Dict = None) -> dict:
        return {
            "type": msg_type.value,
            "data": data,
            "metadata": metadata or {}
        }

    def connect(self):
        try:
            self.socket.connect((self.host, self.port))
            print(f"Connected to server at {self.host}:{self.port}")
            self.process_messages()
        except Exception as e:
            print(f"Failed to connect: {e}")
            self.running = False

    def process_messages(self):
        try:
            while self.running:
                message = self.receive_message()
                if not message:
                    break

                self.handle_message(message)
        except Exception as e:
            print(f"Error processing messages: {e}")
        finally:
            self.socket.close()

    def handle_message(self, message):
        msg_type = message.get('type')
        data = message.get('data')

        if msg_type == MessageType.COMMAND.value:
            # Execute command and send response
            output = self.execute_command(data)
            self.send_message(self.format_message(MessageType.RESPONSE, output))
        
        elif msg_type == MessageType.MESSAGE.value:
            # Echo message and send response
            print(f"Server message: {data}")
            self.send_message(self.format_message(
                MessageType.RESPONSE,
                f"Message received: {data}"
            ))
        
        elif msg_type == MessageType.STATUS.value:
            # Send system status
            status = self.get_system_status()
            self.send_message(self.format_message(MessageType.STATUS, status))

    def execute_command(self, command):
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.returncode == 0:
                return result.stdout
            else:
                return f"Error (code {result.returncode}): {result.stderr}"
        except subprocess.TimeoutExpired:
            return "Command timed out after 30 seconds"
        except Exception as e:
            return f"Error executing command: {e}"

    def get_system_status(self):
        status = {
            "platform": platform.platform(),
            "python_version": platform.python_version(),
            "cpu_percent": psutil.cpu_percent(),
            "memory_percent": psutil.virtual_memory().percent,
            "disk_usage": psutil.disk_usage('/').percent
        }
        return status

    # ... existing send_message and receive_message methods ...
def send_message(self, message):
    try:
        serialized = json.dumps(message).encode('utf-8')
        message_length = len(serialized).to_bytes(4, byteorder='big')
        self.socket.send(message_length + serialized)
    except Exception as e:
        raise Exception(f"Failed to send message: {e}")

def receive_message(self):
    try:
        # Read message length (4 bytes)
        message_length_bytes = self.socket.recv(4)
        if not message_length_bytes:
            return None
            
        message_length = int.from_bytes(message_length_bytes, byteorder='big')
        
        # Read the actual message
        chunks = []
        bytes_received = 0
        while bytes_received < message_length:
            chunk = self.socket.recv(min(message_length - bytes_received, 4096))
            if not chunk:
                return None
            chunks.append(chunk)
            bytes_received += len(chunk)
            
        serialized = b''.join(chunks)
        return json.loads(serialized.decode('utf-8'))
    except Exception as e:
        raise Exception(f"Failed to receive message: {e}")

if __name__ == "__main__":
    client = TerminalClient()
    client.connect()