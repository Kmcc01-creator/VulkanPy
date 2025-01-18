import socket
import json
import threading
import datetime
from enum import Enum
from typing import Any, Dict

class MessageType(Enum):
    COMMAND = "command"
    MESSAGE = "message"
    RESPONSE = "response"
    ERROR = "error"
    STATUS = "status"

class TerminalServer:
    def __init__(self, host='localhost', port=5000):
        self.host = host
        self.port = port
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.clients = {}
        self.running = True

    def format_message(self, msg_type: MessageType, data: Any, metadata: Dict = None) -> dict:
        return {
            "type": msg_type.value,
            "data": data,
            "timestamp": datetime.datetime.now().isoformat(),
            "metadata": metadata or {}
        }

    def start(self):
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(5)
        print(f"Server listening on {self.host}:{self.port}")
        print("Available commands:")
        print("  /cmd <command> - Execute a command")
        print("  /msg <message> - Send a message")
        print("  /status - Get client status")
        print("  /quit - Exit the server")

        # Start accepting clients in a separate thread
        accept_thread = threading.Thread(target=self.accept_clients)
        accept_thread.start()

        # Handle server input
        self.handle_server_input()

    def accept_clients(self):
        while self.running:
            try:
                client_socket, address = self.server_socket.accept()
                client_handler = threading.Thread(
                    target=self.handle_client,
                    args=(client_socket, address)
                )
                client_handler.start()
            except Exception as e:
                if self.running:
                    print(f"Error accepting client: {e}")

    def handle_server_input(self):
        while self.running:
            try:
                user_input = input("Server> ").strip()
                
                if user_input.lower() == '/quit':
                    self.shutdown()
                    break

                if not self.clients:
                    print("No connected clients.")
                    continue

                if user_input.startswith('/'):
                    self.process_server_command(user_input)
                else:
                    # Treat as a message by default
                    self.broadcast_message(
                        self.format_message(MessageType.MESSAGE, user_input)
                    )
            except KeyboardInterrupt:
                self.shutdown()
                break
            except Exception as e:
                print(f"Error processing input: {e}")

    def process_server_command(self, command: str):
        parts = command.split(maxsplit=1)
        cmd_type = parts[0].lower()
        cmd_data = parts[1] if len(parts) > 1 else ""

        if cmd_type == '/cmd':
            self.broadcast_message(
                self.format_message(MessageType.COMMAND, cmd_data)
            )
        elif cmd_type == '/msg':
            self.broadcast_message(
                self.format_message(MessageType.MESSAGE, cmd_data)
            )
        elif cmd_type == '/status':
            self.broadcast_message(
                self.format_message(MessageType.STATUS, "status_request")
            )
        else:
            print(f"Unknown command: {cmd_type}")

    def broadcast_message(self, message):
        disconnected_clients = []
        
        for address, client_socket in self.clients.items():
            try:
                self.send_message(client_socket, message)
            except Exception as e:
                print(f"Error sending to client {address}: {e}")
                disconnected_clients.append(address)

        # Clean up disconnected clients
        for address in disconnected_clients:
            del self.clients[address]

    def handle_client(self, client_socket, address):
        self.clients[address] = client_socket
        print(f"New connection from {address}")
        
        # Send welcome message
        welcome_msg = self.format_message(
            MessageType.MESSAGE,
            "Connected to server",
            {"client": str(address)}
        )
        self.send_message(client_socket, welcome_msg)

        try:
            while self.running:
                response = self.receive_message(client_socket)
                if not response:
                    break

                self.handle_client_response(address, response)
        except Exception as e:
            print(f"Error handling client {address}: {e}")
        finally:
            client_socket.close()
            if address in self.clients:
                del self.clients[address]
            print(f"Client {address} disconnected")

    def handle_client_response(self, address, response):
        msg_type = response.get('type')
        data = response.get('data')
        
        if msg_type == MessageType.RESPONSE.value:
            print(f"Client {address} output:")
            print(data)
        elif msg_type == MessageType.ERROR.value:
            print(f"Client {address} error:")
            print(data)
        elif msg_type == MessageType.STATUS.value:
            print(f"Client {address} status:")
            print(data)

    # ... existing send_message and receive_message methods ...
def send_message(self, client_socket, message):
    try:
        serialized = json.dumps(message).encode('utf-8')
        message_length = len(serialized).to_bytes(4, byteorder='big')
        client_socket.send(message_length + serialized)
    except Exception as e:
        raise Exception(f"Failed to send message: {e}")

def receive_message(self, client_socket):
    try:
        # Read message length (4 bytes)
        message_length_bytes = client_socket.recv(4)
        if not message_length_bytes:
            return None
            
        message_length = int.from_bytes(message_length_bytes, byteorder='big')
        
        # Read the actual message
        chunks = []
        bytes_received = 0
        while bytes_received < message_length:
            chunk = client_socket.recv(min(message_length - bytes_received, 4096))
            if not chunk:
                return None
            chunks.append(chunk)
            bytes_received += len(chunk)
            
        serialized = b''.join(chunks)
        return json.loads(serialized.decode('utf-8'))
    except Exception as e:
        raise Exception(f"Failed to receive message: {e}")

def shutdown(self):
        print("Shutting down server...")
        self.running = False
        
        # Close all client connections
        for client_socket in self.clients.values():
            try:
                self.send_message(client_socket, 
                    self.format_message(MessageType.MESSAGE, "Server shutting down")
                )
                client_socket.close()
            except:
                pass
        
        self.clients.clear()
        self.server_socket.close()