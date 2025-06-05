import socket
import threading
import json
import random
import time
from datetime import datetime

class ParquesServer:
    def __init__(self, host='localhost', port=5000):
        self.host = host
        self.port = port
        self.clients = {}  # {client_socket: player_info}
        self.game_state = {
            'players': {},  # {player_id: player_data}
            'current_turn': 0,
            'game_started': False,
            'board': self.initialize_board(),
            'turn_order': [],
            'dice_rolls': [],
            'game_winner': None
        }
        self.colors = ['red', 'blue', 'green', 'yellow']
        self.available_colors = self.colors.copy()
        self.lock = threading.Lock()
        
    def initialize_board(self):
        """Inicializa el tablero con 96 casillas"""
        board = {
            'squares': [None] * 96,  # None = vacío, player_id = ocupado
            'safe_squares': [8, 16, 24, 32, 40, 48, 56, 64, 72, 80, 88, 0],  # Casillas de seguro
            'exit_squares': [1, 25, 49, 73],  # Casillas de salida para cada color
            'home_squares': {  # Casillas finales por color
                'red': list(range(89, 96)),
                'blue': list(range(89, 96)),
                'green': list(range(89, 96)),
                'yellow': list(range(89, 96))
            }
        }
        return board
    
    def start_server(self):
        """Inicia el servidor"""
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind((self.host, self.port))
        server_socket.listen(4)
        
        print(f"Servidor de Parqués iniciado en {self.host}:{self.port}")
        print("Esperando jugadores...")
        
        while len(self.clients) < 4:
            try:
                client_socket, address = server_socket.accept()
                print(f"Nueva conexión desde {address}")
                
                # Crear hilo para manejar cliente
                client_thread = threading.Thread(
                    target=self.handle_client,
                    args=(client_socket, address)
                )
                client_thread.daemon = True
                client_thread.start()
                
            except Exception as e:
                print(f"Error aceptando conexión: {e}")
    
    def handle_client(self, client_socket, address):
        """Maneja la comunicación con un cliente"""
        try:
            while True:
                data = client_socket.recv(1024).decode('utf-8')
                if not data:
                    break
                
                message = json.loads(data)
                self.process_message(client_socket, message)
                
        except Exception as e:
            print(f"Error con cliente {address}: {e}")
        finally:
            self.disconnect_client(client_socket)
    
    def process_message(self, client_socket, message):
        """Procesa mensajes del cliente"""
        msg_type = message.get('type')
        
        if msg_type == 'join_game':
            self.handle_join_game(client_socket, message)
        elif msg_type == 'roll_dice':
            self.handle_roll_dice(client_socket, message)
        elif msg_type == 'move_piece':
            self.handle_move_piece(client_socket, message)
        elif msg_type == 'get_game_state':
            self.send_game_state(client_socket)
    
    def handle_join_game(self, client_socket, message):
        """Maneja la entrada de un jugador al juego"""
        with self.lock:
            if len(self.clients) >= 4:
                self.send_message(client_socket, {
                    'type': 'error',
                    'message': 'Juego lleno'
                })
                return
            
            if self.game_state['game_started']:
                self.send_message(client_socket, {
                    'type': 'error',
                    'message': 'Juego ya iniciado'
                })
                return
            
            username = message.get('username')
            color = message.get('color')
            
            # Verificar color disponible
            if color not in self.available_colors:
                self.send_message(client_socket, {
                    'type': 'error',
                    'message': 'Color no disponible'
                })
                return
            
            # Crear jugador
            player_id = len(self.clients)
            player_data = {
                'id': player_id,
                'username': username,
                'color': color,
                'pieces': [{'position': -1, 'in_jail': True} for _ in range(4)],  # -1 = en cárcel
                'socket': client_socket
            }
            
            self.clients[client_socket] = player_data
            self.game_state['players'][player_id] = player_data
            self.available_colors.remove(color)
            
            # Enviar confirmación
            self.send_message(client_socket, {
                'type': 'join_success',
                'player_id': player_id,
                'color': color
            })
            
            # Broadcast a todos los jugadores
            self.broadcast_message({
                'type': 'player_joined',
                'player': {
                    'id': player_id,
                    'username': username,
                    'color': color
                },
                'total_players': len(self.clients)
            })
            
            # Iniciar juego si hay al menos 2 jugadores
            if len(self.clients) >= 2:
                self.start_game()
    
    def start_game(self):
        """Inicia el juego"""
        if self.game_state['game_started']:
            return
            
        self.game_state['game_started'] = True
        self.game_state['turn_order'] = list(self.game_state['players'].keys())
        
        # Determinar primer jugador por dados
        self.determine_first_player()
        
        # Sincronizar clientes (algoritmo Berkeley simulado)
        self.synchronize_clients()
        
        self.broadcast_message({
            'type': 'game_started',
            'turn_order': self.game_state['turn_order'],
            'current_turn': self.game_state['current_turn']
        })
        
        print("¡Juego iniciado!")
    
    def determine_first_player(self):
        """Determina el primer jugador tirando dados"""
        dice_results = {}
        
        for player_id in self.game_state['players']:
            dice1 = random.randint(1, 6)
            dice2 = random.randint(1, 6)
            total = dice1 + dice2
            dice_results[player_id] = {'dice1': dice1, 'dice2': dice2, 'total': total}
        
        # Encontrar el máximo
        max_total = max(dice_results.values(), key=lambda x: x['total'])['total']
        winners = [pid for pid, result in dice_results.items() if result['total'] == max_total]
        
        # Si hay empate, elegir aleatoriamente
        first_player = random.choice(winners)
        self.game_state['current_turn'] = first_player
        
        self.broadcast_message({
            'type': 'first_player_determined',
            'dice_results': dice_results,
            'first_player': first_player
        })
    
    def synchronize_clients(self):
        """Sincroniza los relojes de los clientes (algoritmo Berkeley simulado)"""
        server_time = time.time()
        
        for client_socket in self.clients:
            self.send_message(client_socket, {
                'type': 'sync_time',
                'server_time': server_time
            })
    
    def handle_roll_dice(self, client_socket, message):
        """Maneja el lanzamiento de dados"""
        player_data = self.clients.get(client_socket)
        if not player_data:
            return
        
        player_id = player_data['id']
        
        # Verificar que sea el turno del jugador
        if self.game_state['current_turn'] != player_id:
            self.send_message(client_socket, {
                'type': 'error',
                'message': 'No es tu turno'
            })
            return
        
        # Lanzar dados
        dice1 = random.randint(1, 6)
        dice2 = random.randint(1, 6)
        is_double = dice1 == dice2

        print(f"[DEBUG] Jugador {player_id} lanzó los dados: {dice1}, {dice2} (doble: {is_double})")
        
        dice_result = {
            'dice1': dice1,
            'dice2': dice2,
            'is_double': is_double,
            'player_id': player_id
        }
        
        # Broadcast resultado de dados
        self.broadcast_message({
            'type': 'dice_rolled',
            **dice_result
        })
        
        # Si es doble, puede sacar ficha de la cárcel
        if is_double:
            self.handle_jail_release(player_id)
        
        # Enviar posibles movimientos
        possible_moves = self.get_possible_moves(player_id, dice1, dice2)
        self.send_message(client_socket, {
            'type': 'possible_moves',
            'moves': possible_moves
        })
    
    def handle_jail_release(self, player_id):
        """Maneja la liberación de fichas de la cárcel"""
        player = self.game_state['players'][player_id]
        
        # Buscar ficha en cárcel
        for i, piece in enumerate(player['pieces']):
            if piece['in_jail']:
                piece['in_jail'] = False
                piece['position'] = self.get_start_position(player['color'])
                
                self.broadcast_message({
                    'type': 'piece_released',
                    'player_id': player_id,
                    'piece_index': i,
                    'new_position': piece['position']
                })
                break
    
    def get_start_position(self, color):
        """Obtiene la posición de inicio según el color"""
        start_positions = {
            'red': 1,
            'blue': 25,
            'green': 49,
            'yellow': 73
        }
        return start_positions.get(color, 1)
    
    def get_possible_moves(self, player_id, dice1, dice2):
        """Calcula los movimientos posibles para un jugador"""
        player = self.game_state['players'][player_id]
        possible_moves = []
        
        for i, piece in enumerate(player['pieces']):
            if not piece['in_jail']:
                # Movimiento con dado 1
                new_pos1 = (piece['position'] + dice1) % 96
                if self.is_valid_move(player_id, i, new_pos1):
                    possible_moves.append({
                        'piece_index': i,
                        'new_position': new_pos1,
                        'dice_used': dice1
                    })
                
                # Movimiento con dado 2
                new_pos2 = (piece['position'] + dice2) % 96
                if self.is_valid_move(player_id, i, new_pos2):
                    possible_moves.append({
                        'piece_index': i,
                        'new_position': new_pos2,
                        'dice_used': dice2
                    })
                
                # Movimiento con suma de dados
                new_pos_sum = (piece['position'] + dice1 + dice2) % 96
                if self.is_valid_move(player_id, i, new_pos_sum):
                    possible_moves.append({
                        'piece_index': i,
                        'new_position': new_pos_sum,
                        'dice_used': dice1 + dice2
                    })
        
        return possible_moves
    
    def is_valid_move(self, player_id, piece_index, new_position):
        """Verifica si un movimiento es válido"""
        # Verificar límites del tablero
        if new_position < 0 or new_position >= 96:
            return False
        
        # Verificar si la casilla está ocupada por otra ficha del mismo jugador
        player = self.game_state['players'][player_id]
        for i, piece in enumerate(player['pieces']):
            if i != piece_index and piece['position'] == new_position:
                return False
        
        return True
    
    def handle_move_piece(self, client_socket, message):
        """Maneja el movimiento de una ficha"""
        player_data = self.clients.get(client_socket)
        if not player_data:
            return
        
        player_id = player_data['id']
        piece_index = message.get('piece_index')
        new_position = message.get('new_position')
        
        # Verificar que sea el turno del jugador
        if self.game_state['current_turn'] != player_id:
            return
        
        # Mover la ficha
        player = self.game_state['players'][player_id]
        old_position = player['pieces'][piece_index]['position']
        player['pieces'][piece_index]['position'] = new_position
        
        # Verificar capturas
        self.check_captures(player_id, new_position)
        
        # Verificar victoria
        if self.check_victory(player_id):
            self.game_state['game_winner'] = player_id
            self.broadcast_message({
                'type': 'game_won',
                'winner': player_id,
                'winner_name': player['username']
            })
            return
        
        # Broadcast movimiento
        self.broadcast_message({
            'type': 'piece_moved',
            'player_id': player_id,
            'piece_index': piece_index,
            'old_position': old_position,
            'new_position': new_position
        })
        
        # Pasar turno
        self.next_turn()
    
    def check_captures(self, player_id, position):
        """Verifica si se captura alguna ficha enemiga"""
        # Verificar si la posición es un seguro
        if position in self.game_state['board']['safe_squares']:
            return
        
        captured_pieces = []
        
        for other_player_id, other_player in self.game_state['players'].items():
            if other_player_id == player_id:
                continue
            
            for i, piece in enumerate(other_player['pieces']):
                if piece['position'] == position and not piece['in_jail']:
                    # Enviar a la cárcel
                    piece['position'] = -1
                    piece['in_jail'] = True
                    captured_pieces.append({
                        'player_id': other_player_id,
                        'piece_index': i
                    })
        
        if captured_pieces:
            self.broadcast_message({
                'type': 'pieces_captured',
                'captured_by': player_id,
                'captured_pieces': captured_pieces
            })
    
    def check_victory(self, player_id):
        """Verifica si un jugador ha ganado"""
        player = self.game_state['players'][player_id]
        home_squares = self.game_state['board']['home_squares'][player['color']]
        
        pieces_home = 0
        for piece in player['pieces']:
            if piece['position'] in home_squares:
                pieces_home += 1
        
        return pieces_home == 4
    
    def next_turn(self):
        """Pasa al siguiente turno"""
        current_index = self.game_state['turn_order'].index(self.game_state['current_turn'])
        next_index = (current_index + 1) % len(self.game_state['turn_order'])
        self.game_state['current_turn'] = self.game_state['turn_order'][next_index]
        
        self.broadcast_message({
            'type': 'turn_changed',
            'current_turn': self.game_state['current_turn']
        })
    
    def send_game_state(self, client_socket):
        """Envía el estado completo del juego"""
        self.send_message(client_socket, {
            'type': 'game_state',
            'state': self.game_state
        })
    
    def send_message(self, client_socket, message):
        """Envía un mensaje a un cliente específico"""
        try:
            message_str = json.dumps(message)
            client_socket.send(message_str.encode('utf-8'))
        except Exception as e:
            print(f"Error enviando mensaje: {e}")
    
    def broadcast_message(self, message):
        """Envía un mensaje a todos los clientes"""
        for client_socket in list(self.clients.keys()):
            self.send_message(client_socket, message)
    
    def disconnect_client(self, client_socket):
        """Desconecta un cliente"""
        if client_socket in self.clients:
            player_data = self.clients[client_socket]
            player_id = player_data['id']
            color = player_data['color']
            
            # Remover cliente
            del self.clients[client_socket]
            del self.game_state['players'][player_id]
            
            # Hacer color disponible de nuevo
            if color not in self.available_colors:
                self.available_colors.append(color)
            
            # Notificar a otros jugadores
            self.broadcast_message({
                'type': 'player_disconnected',
                'player_id': player_id
            })
            
            print(f"Jugador {player_id} desconectado")
        
        try:
            client_socket.close()
        except:
            pass

if __name__ == "__main__":
    server = ParquesServer()
    server.start_server()