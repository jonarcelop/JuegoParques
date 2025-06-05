import socket
import threading
import json
import tkinter as tk
from tkinter import messagebox, simpledialog, ttk
import time
import math

class ClienteParques:
    def __init__(self):
        # Definir coordenadas del tablero (igual que el servidor)
        self.CAMINO_GLOBAL = [
            (7,0),(7,1),(7,2),(7,3),(7,4),(7,5),(7,6),
            (6,6),(5,6),(4,6),(3,6),(2,6),(1,6),(0,6),
            (0,7),(0,8),(0,9),(0,10),(0,11),
            (1,11),(2,11),(3,11),(4,11),(5,11),(6,11),
            (7,11),(7,12),(7,13),(7,14),(7,15),(7,16),(7,17),
            (8,17),(9,17),(10,17),(11,17),
            (11,16),(11,15),(11,14),(11,13),(11,12),(11,11),
            (11,10),(12,10),(13,10),(14,10),(15,10),(16,10),(17,10),
            (17,9),(17,8),(17,7),(17,6),
            (16,6),(15,6),(14,6),(13,6),(12,6),(11,6),
            (10,6),(10,5),(10,4),(10,3),(10,2),(10,1),(10,0),
            (9,0),(8,0),(7,0)
        ]
        
        self.CAMINOS_META = {
            "red": [(8,1), (8,2), (8,3), (8,4), (8,5), (8,6), (8,7), (8,8)],
            "blue": [(1,8), (2,8), (3,8), (4,8), (5,8), (6,8), (7,8), (8,8)],
            "green": [(9,16), (9,15), (9,14), (9,13), (9,12), (9,11), (9,10), (8,8)],
            "yellow": [(16,9), (15,9), (14,9), (13,9), (12,9), (11,9), (10,9), (8,8)]
        }
        
        self.CARCELES_COORDS = {
            "red": [(1, 1), (1, 2), (2, 1), (2, 2)],
            "blue": [(1, 15), (1, 16), (2, 15), (2, 16)],
            "green": [(15, 1), (15, 2), (16, 1), (16, 2)],
            "yellow": [(15, 15), (15, 16), (16, 15), (16, 16)]
        }
        
        self.CASILLAS_SEGURAS = [
            (7,0), (0,6), (0,11), (7,11), (7,17), (11,17), (11,10), (17,10),
            (17,6), (11,6), (10,0), (4,6), (7,13), (11,4), (13,10)
        ]
        self.socket = None
        self.conectado = False
        self.nombre = ""
        self.color = ""
        self.tiempo_ajuste = 0
        
        # Estado del juego
        self.es_mi_turno = False
        self.puede_lanzar = False
        self.ultimo_dado = {"dado1": 0, "dado2": 0, "total": 0}
        self.movible_fichas = []
        self.puede_relanzar = False
        
        # Estado de las fichas en el tablero
        self.fichas_tablero = {}  # {color: {ficha_idx: (x, y)}}


        # Configurar interfaz
        self.setup_gui()
        
        
        
    def setup_gui(self):
        """Configura la interfaz gráfica"""
        self.root = tk.Tk()
        self.root.title("Parqués Cliente")
        self.root.geometry("1000x800")
        self.root.configure(bg="#2c3e50")
        
        # Frame principal
        main_frame = tk.Frame(self.root, bg="#2c3e50")
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Frame de conexión
        conn_frame = tk.Frame(main_frame, bg="#34495e", relief=tk.RAISED, bd=2)
        conn_frame.pack(fill=tk.X, pady=(0, 10))
        
        tk.Label(conn_frame, text="Servidor:", bg="#34495e", fg="white", font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=5)
        self.host_entry = tk.Entry(conn_frame, width=15)
        self.host_entry.insert(0, "localhost")
        self.host_entry.pack(side=tk.LEFT, padx=5)
        
        tk.Label(conn_frame, text="Puerto:", bg="#34495e", fg="white", font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=5)
        self.port_entry = tk.Entry(conn_frame, width=8)
        self.port_entry.insert(0, "5000")
        self.port_entry.pack(side=tk.LEFT, padx=5)
        
        self.connect_btn = tk.Button(conn_frame, text="Conectar", command=self.conectar, 
                                   bg="#3498db", fg="white", font=("Arial", 10, "bold"))
        self.connect_btn.pack(side=tk.LEFT, padx=10)
        
        self.disconnect_btn = tk.Button(conn_frame, text="Desconectar", command=self.desconectar, 
                                      bg="#e74c3c", fg="white", font=("Arial", 10, "bold"), state=tk.DISABLED)
        self.disconnect_btn.pack(side=tk.LEFT, padx=5)
        
        # Frame de estado
        status_frame = tk.Frame(main_frame, bg="#34495e", relief=tk.RAISED, bd=2)
        status_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.status_label = tk.Label(status_frame, text="Desconectado", bg="#34495e", fg="#e74c3c", 
                                   font=("Arial", 12, "bold"))
        self.status_label.pack(pady=5)
        
        # Frame del juego
        game_frame = tk.Frame(main_frame, bg="#2c3e50")
        game_frame.pack(fill=tk.BOTH, expand=True)
        
        # Frame izquierdo - Tablero
        left_frame = tk.Frame(game_frame, bg="#2c3e50")
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Canvas para el tablero
        self.canvas = tk.Canvas(left_frame, width=600, height=600, bg="#ecf0f1", relief=tk.SUNKEN, bd=2)
        self.canvas.pack(pady=10)
        
        # Frame derecho - Controles
        right_frame = tk.Frame(game_frame, bg="#34495e", width=300, relief=tk.RAISED, bd=2)
        right_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=(10, 0))
        right_frame.pack_propagate(False)
        
        # Información del jugador
        info_frame = tk.LabelFrame(right_frame, text="Información", bg="#34495e", fg="white", 
                                 font=("Arial", 10, "bold"))
        info_frame.pack(fill=tk.X, padx=10, pady=10)
        
        self.player_info = tk.Label(info_frame, text="No conectado", bg="#34495e", fg="white", 
                                  font=("Arial", 10))
        self.player_info.pack(pady=5)
        
        # Frame de dados
        dice_frame = tk.LabelFrame(right_frame, text="Dados", bg="#34495e", fg="white", 
                                 font=("Arial", 10, "bold"))
        dice_frame.pack(fill=tk.X, padx=10, pady=10)
        
        self.dice_label = tk.Label(dice_frame, text="🎲 🎲", bg="#34495e", fg="white", 
                                 font=("Arial", 20))
        self.dice_label.pack(pady=5)
        
        self.dice_result = tk.Label(dice_frame, text="Total: 0", bg="#34495e", fg="white", 
                                  font=("Arial", 12))
        self.dice_result.pack(pady=2)
        
        self.launch_btn = tk.Button(dice_frame, text="Lanzar Dados", command=self.lanzar_dados, 
                                  bg="#f39c12", fg="white", font=("Arial", 10, "bold"), 
                                  state=tk.DISABLED)
        self.launch_btn.pack(pady=5)
        
        # Frame de fichas
        pieces_frame = tk.LabelFrame(right_frame, text="Fichas", bg="#34495e", fg="white", 
                                   font=("Arial", 10, "bold"))
        pieces_frame.pack(fill=tk.X, padx=10, pady=10)
        
        self.pieces_buttons = []
        for i in range(4):
            btn = tk.Button(pieces_frame, text=f"Ficha {i+1}", command=lambda idx=i: self.mover_ficha(idx),
                          bg="#95a5a6", fg="white", font=("Arial", 9), state=tk.DISABLED)
            btn.pack(fill=tk.X, pady=2)
            self.pieces_buttons.append(btn)
        
        # Frame de mensajes
        msg_frame = tk.LabelFrame(right_frame, text="Mensajes", bg="#34495e", fg="white", 
                                font=("Arial", 10, "bold"))
        msg_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        self.messages_text = tk.Text(msg_frame, height=8, bg="#2c3e50", fg="white", 
                                   font=("Arial", 9), state=tk.DISABLED)
        scrollbar = tk.Scrollbar(msg_frame, command=self.messages_text.yview)
        self.messages_text.config(yscrollcommand=scrollbar.set)
        self.messages_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Dibujar tablero inicial
        self.dibujar_tablero()
        
    def conectar(self):
        """Conecta al servidor"""
        if self.conectado:
            return
            
        try:
            host = self.host_entry.get().strip()
            port = int(self.port_entry.get().strip())
            
            # Pedir nombre del jugador
            self.nombre = simpledialog.askstring("Nombre", "Ingresa tu nombre:")
            if not self.nombre:
                return
            
            # Crear socket y conectar
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((host, port))
            
            # Enviar nombre
            self.socket.send(self.nombre.encode())
            
            # Iniciar hilo de escucha
            self.conectado = True
            self.listen_thread = threading.Thread(target=self.escuchar_servidor, daemon=True)
            self.listen_thread.start()
            
            # Actualizar interfaz
            self.connect_btn.config(state=tk.DISABLED)
            self.disconnect_btn.config(state=tk.NORMAL)
            self.status_label.config(text="Conectando...", fg="#f39c12")
            
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo conectar: {e}")
            if self.socket:
                self.socket.close()
                self.socket = None
            self.conectado = False
    
    def desconectar(self):
        """Desconecta del servidor"""
        if not self.conectado:
            return
            
        try:
            if self.socket:
                self.enviar_mensaje({"tipo": "desconectar"})
                self.socket.close()
        except:
            pass
        
        self.conectado = False
        self.socket = None
        
        # Actualizar interfaz
        self.connect_btn.config(state=tk.NORMAL)
        self.disconnect_btn.config(state=tk.DISABLED)
        self.launch_btn.config(state=tk.DISABLED)
        for btn in self.pieces_buttons:
            btn.config(state=tk.DISABLED, bg="#95a5a6")
        
        self.status_label.config(text="Desconectado", fg="#e74c3c")
        self.player_info.config(text="No conectado")
        self.agregar_mensaje("Desconectado del servidor")
        
        # Limpiar tablero
        self.fichas_tablero.clear()
        self.dibujar_tablero()
    
    def enviar_mensaje(self, mensaje_dict):
        """Envía un mensaje JSON al servidor"""
        if not self.conectado or not self.socket:
            return False
            
        try:
            mensaje_str = json.dumps(mensaje_dict)
            self.socket.send(mensaje_str.encode())
            return True
        except Exception as e:
            print(f"Error enviando mensaje: {e}")
            return False
    
    def escuchar_servidor(self):
        """Escucha mensajes del servidor"""
        while self.conectado:
            try:
                mensaje_raw = self.socket.recv(1024).decode()
                if not mensaje_raw:
                    break
                
                data = json.loads(mensaje_raw)
                self.root.after(0, self.procesar_mensaje, data)
                
            except Exception as e:
                if self.conectado:
                    print(f"Error escuchando servidor: {e}")
                break
        
        # Si sale del bucle, desconectar
        if self.conectado:
            self.root.after(0, self.desconectar)
    
    def procesar_mensaje(self, data):
        """Procesa mensajes recibidos del servidor"""
        tipo = data.get("tipo")
        
        if tipo == "color":
            self.color = data.get("color")
            mensaje = data.get("mensaje", "")
            self.status_label.config(text=f"Conectado - {self.color}", fg="#27ae60")
            self.player_info.config(text=f"Jugador: {self.nombre}\nColor: {self.color}")
            self.agregar_mensaje(mensaje)
            
        elif tipo == "error":
            mensaje = data.get("mensaje", "Error desconocido")
            messagebox.showerror("Error", mensaje)
            self.agregar_mensaje(f"ERROR: {mensaje}")
            
        elif tipo == "jugador_unido":
            nombre = data.get("nombre")
            color = data.get("color")
            total = data.get("total_jugadores")
            self.agregar_mensaje(f"{nombre} ({color}) se unió. Jugadores: {total}")
            
        elif tipo == "jugador_desconectado":
            nombre = data.get("nombre")
            total = data.get("total_jugadores")
            self.agregar_mensaje(f"{nombre} se desconectó. Jugadores: {total}")
            
        elif tipo == "inicio_juego":
            mensaje = data.get("mensaje", "")
            jugadores = data.get("jugadores", [])
            self.agregar_mensaje(mensaje)
            self.agregar_mensaje("Jugadores en partida:")
            for j in jugadores:
                self.agregar_mensaje(f"  - {j['nombre']} ({j['color']})")
            
            # Inicializar fichas en el tablero
            for j in jugadores:
                self.fichas_tablero[j['color']] = {}
                for i in range(4):
                    self.fichas_tablero[j['color']][i] = "carcel"
            self.dibujar_tablero()
            
        elif tipo == "turno":
            mensaje = data.get("mensaje", "")
            self.es_mi_turno = data.get("es_tu_turno", False)
            self.puede_lanzar = data.get("puede_lanzar", False)
            
            self.agregar_mensaje(mensaje)
            
            if self.es_mi_turno:
                self.launch_btn.config(state=tk.NORMAL if self.puede_lanzar else tk.DISABLED)
                self.status_label.config(text=f"Tu turno - {self.color}", fg="#f39c12")
            else:
                self.launch_btn.config(state=tk.DISABLED)
                self.status_label.config(text=f"Conectado - {self.color}", fg="#27ae60")
                for btn in self.pieces_buttons:
                    btn.config(state=tk.DISABLED, bg="#95a5a6")
            
        elif tipo == "dados":
            dado1 = data.get("dado1", 0)
            dado2 = data.get("dado2", 0)
            total = data.get("total", 0)
            self.movible_fichas = data.get("movible_fichas", [])
            self.puede_relanzar = data.get("puede_relanzar", False)
            
            self.ultimo_dado = {"dado1": dado1, "dado2": dado2, "total": total}
            
            # Actualizar display de dados
            self.dice_label.config(text=f"🎲{dado1} 🎲{dado2}")
            self.dice_result.config(text=f"Total: {total}")
            
            # Actualizar botones de fichas
            for i, btn in enumerate(self.pieces_buttons):
                if i in self.movible_fichas:
                    btn.config(state=tk.NORMAL, bg="#27ae60")
                else:
                    btn.config(state=tk.DISABLED, bg="#95a5a6")
            
            # Actualizar botón de lanzar
            if self.puede_relanzar:
                self.launch_btn.config(state=tk.NORMAL)
                self.agregar_mensaje("¡Sacaste pares! Puedes lanzar de nuevo")
            else:
                self.launch_btn.config(state=tk.DISABLED)
            
            self.agregar_mensaje(f"Dados: {dado1}-{dado2} = {total}")
            
        elif tipo == "movimiento":
            color = data.get("color")
            ficha_idx = data.get("ficha_idx")
            desde = data.get("desde")
            hasta = data.get("hasta")
            
            if color in self.fichas_tablero:
                self.fichas_tablero[color][ficha_idx] = hasta
                self.dibujar_tablero()
            
        elif tipo == "info":
            mensaje = data.get("mensaje", "")
            self.agregar_mensaje(mensaje)
            
        elif tipo == "victoria":
            ganador = data.get("ganador")
            color = data.get("color")
            mensaje = data.get("mensaje")
            self.agregar_mensaje(mensaje)
            messagebox.showinfo("¡Victoria!", mensaje)
            
        elif tipo == "sync_request":
            # Responder con tiempo actual
            tiempo_actual = time.time() + self.tiempo_ajuste
            self.enviar_mensaje({
                "tipo": "sync_response",
                "tiempo": tiempo_actual
            })
            
        elif tipo == "sync_adjust":
            # Ajustar tiempo local
            ajuste = data.get("ajuste", 0)
            self.tiempo_ajuste += ajuste
            self.agregar_mensaje(f"Reloj sincronizado (ajuste: {ajuste:.2f}s)")
    
    def lanzar_dados(self):
        """Lanza los dados"""
        if not self.es_mi_turno or not self.puede_lanzar:
            return
            
        self.enviar_mensaje({"tipo": "lanzar_dado"})
        self.launch_btn.config(state=tk.DISABLED)
    
    def mover_ficha(self, ficha_idx):
        """Mueve una ficha específica"""
        if not self.es_mi_turno or ficha_idx not in self.movible_fichas:
            return
            
        self.enviar_mensaje({
            "tipo": "mover_ficha",
            "ficha_idx": ficha_idx
        })
        
        # Deshabilitar botones después del movimiento
        for btn in self.pieces_buttons:
            btn.config(state=tk.DISABLED, bg="#95a5a6")
    
    def agregar_mensaje(self, mensaje):
        """Agrega un mensaje al chat"""
        self.messages_text.config(state=tk.NORMAL)
        timestamp = time.strftime("%H:%M:%S")
        self.messages_text.insert(tk.END, f"[{timestamp}] {mensaje}\n")
        self.messages_text.see(tk.END)
        self.messages_text.config(state=tk.DISABLED)
    
    def dibujar_tablero(self):
        """Dibuja el tablero de Parqués"""
        self.canvas.delete("all")
        
        # Configuración
        canvas_size = 600
        grid_size = 18
        cell_size = canvas_size // grid_size
        
        # Colores
        colores = {
            "red": "#e74c3c",
            "blue": "#3498db", 
            "green": "#27ae60",
            "yellow": "#f1c40f"
        }
        
        # Dibujar fondo
        self.canvas.create_rectangle(0, 0, canvas_size, canvas_size, fill="#ecf0f1", outline="")
        
        # Dibujar casillas del camino global
        for i, (x, y) in enumerate(self.CAMINO_GLOBAL):
            px = x * cell_size + cell_size // 2
            py = y * cell_size + cell_size // 2
            
            # Color de la casilla
            color = "#bdc3c7"
            if (x, y) in self.CASILLAS_SEGURAS:
                color = "#f39c12"  # Casillas seguras en naranja
            
            self.canvas.create_rectangle(
                px - cell_size//3, py - cell_size//3,
                px + cell_size//3, py + cell_size//3,
                fill=color, outline="#34495e", width=1
            )
        
        # Dibujar caminos de meta
        for color, camino in self.CAMINOS_META.items():
            for x, y in camino[:-1]:  # Excluir la meta final
                px = x * cell_size + cell_size // 2
                py = y * cell_size + cell_size // 2
                
                self.canvas.create_rectangle(
                    px - cell_size//4, py - cell_size//4,
                    px + cell_size//4, py + cell_size//4,
                    fill=colores[color], outline="#2c3e50", width=1
                )
        
        # Dibujar meta final (centro)
        center_x = 8 * cell_size + cell_size // 2
        center_y = 8 * cell_size + cell_size // 2
        self.canvas.create_oval(
            center_x - cell_size//2, center_y - cell_size//2,
            center_x + cell_size//2, center_y + cell_size//2,
            fill="#2c3e50", outline="#34495e", width=2
        )
        self.canvas.create_text(center_x, center_y, text="META", fill="white", font=("Arial", 10, "bold"))
        
        # Dibujar cárceles
        for color, coords in self.CARCELES_COORDS.items():
            # Dibujar el marco de la cárcel
            min_x = min(coord[0] for coord in coords) * cell_size
            max_x = (max(coord[0] for coord in coords) + 1) * cell_size
            min_y = min(coord[1] for coord in coords) * cell_size
            max_y = (max(coord[1] for coord in coords) + 1) * cell_size
            
            self.canvas.create_rectangle(
                min_x, min_y, max_x, max_y,
                fill=colores[color], outline="#2c3e50", width=3
            )
            
            # Dibujar casillas individuales de la cárcel
            for i, (x, y) in enumerate(coords):
                px = x * cell_size + cell_size // 2
                py = y * cell_size + cell_size // 2
                
                self.canvas.create_rectangle(
                    px - cell_size//3, py - cell_size//3,
                    px + cell_size//3, py + cell_size//3,
                    fill="white", outline="#2c3e50", width=1
                )
        
        # Dibujar fichas
        for color, fichas in self.fichas_tablero.items():
            for ficha_idx, posicion in fichas.items():
                if posicion == "carcel":
                    # Ficha en cárcel
                    coords = self.CARCELES_COORDS[color][ficha_idx]
                    px = coords[0] * cell_size + cell_size // 2
                    py = coords[1] * cell_size + cell_size // 2
                else:
                    # Ficha en el tablero
                    px = posicion[0] * cell_size + cell_size // 2
                    py = posicion[1] * cell_size + cell_size // 2
                
                # Dibujar la ficha
                self.canvas.create_oval(
                    px - cell_size//6, py - cell_size//6,
                    px + cell_size//6, py + cell_size//6,
                    fill=colores[color], outline="white", width=2
                )
                
                # Número de la ficha
                self.canvas.create_text(
                    px, py, text=str(ficha_idx + 1), 
                    fill="white", font=("Arial", 8, "bold")
                )
    
    def run(self):
        """Ejecuta la aplicación"""
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.root.mainloop()
    
    def on_closing(self):
        """Maneja el cierre de la aplicación"""
        if self.conectado:
            self.desconectar()
        self.root.destroy()

if __name__ == "__main__":
    cliente = ClienteParques()
    cliente.run()