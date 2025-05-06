import socket
import threading

HOST = 'localhost'  # O la IP del servidor
PORT = 5000

def recibir_mensajes(sock):
    while True:
        try:
            mensaje = sock.recv(1024).decode()
            if mensaje:
                print("\n" + mensaje)
            else:
                break
        except:
            print("[-] Conexión perdida.")
            break

def cliente():
    cliente_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    cliente_socket.connect((HOST, PORT))

    nombre = input("Ingresa tu nombre de jugador: ")
    cliente_socket.send(nombre.encode())

    # Hilo para recibir mensajes del servidor
    hilo_recepcion = threading.Thread(target=recibir_mensajes, args=(cliente_socket,))
    hilo_recepcion.start()

    while True:
        mensaje = input()
        if mensaje.lower() == "salir":
            cliente_socket.close()
            break
        cliente_socket.send(mensaje.encode())


    hilo_recepcion.join()
    cliente_socket.close()

    print("Conexión cerrada.")

# tablero de parques
import tkinter as tk

TAM_CASILLA = 30
FILAS = 18
COLUMNAS = 18

# pociciones de salida 

SALIDAS = [
    (4,7,"red"),
    (7,13, "blue"),
    (10,4, "green"),
    (13,10, "yellow"),
] 

# pociciones de seguros 

SEGUROS = [
    (8, 4,"red")    ,(0,8,"red"),
    (4, 9,"blue")   ,(8,17,"blue"),
    (9, 0,"green")  ,(13,8,"green"),
    (17, 9,"yellow"),(9,13,"yellow")

]

# pociciones de meta
META = [
    (7, 8,"red"),(9,7,"green"),
    (8, 10,"blue"),(10,9,"yellow")
    ]




class TableroParques:
    def __init__(self, root):
        self.canvas = tk.Canvas(root, width=COLUMNAS*TAM_CASILLA, height=FILAS*TAM_CASILLA)
        self.canvas.pack()
        self.dibujar_tablero()
        self.turno_label = tk.Label(root, text="esperando turno")
        self.turno_label.pack(pady=10)
        self.turno_label.config(text="¡Tu turno!")
        

    def lanzar_dado(self):
        self.sock.send("lanzar_dado".encode())



    def dibujar_tablero(self):
        for fila in range(FILAS):
            for col in range(COLUMNAS):
                x1 = col * TAM_CASILLA
                y1 = fila * TAM_CASILLA
                x2 = x1 + TAM_CASILLA
                y2 = y1 + TAM_CASILLA

                color = self.obtener_color(fila, col)
                self.canvas.create_rectangle(x1, y1, x2, y2, fill=color, outline="black")
        
                # Dibujar seguros
        self.marcar_salidas()
        self.marcar_seguros()
        self.marcar_meta()

    def obtener_color(self, fila, col):
        # Zonas de cárcel por jugador
        if fila < 8 and col < 7:
            return "red"
        elif fila < 7 and col > 9:
            return "blue"
        elif fila > 10 and col < 8:
            return "green"
        elif fila > 9 and col > 10:
            return "yellow"

        # Camino central (cruz)
        elif 6 <= fila <= 8 or 6 <= col <= 8:
            return "white"

        # Zona central (meta)
        if 6 <= fila <= 8 and 6 <= col <= 8:
            return "gray"

        return "#ccc"
    
    def marcar_salidas(self):
        for fila, col, color in SALIDAS:
            x1 = col * TAM_CASILLA
            y1 = fila * TAM_CASILLA
            x2 = x1 + TAM_CASILLA
            y2 = y1 + TAM_CASILLA
            self.canvas.create_rectangle(x1, y1, x2, y2, fill=color, outline="black")
            self.canvas.create_text((x1+x2)//2, (y1+y2)//2, text="Salida", fill="white")
            
    def marcar_seguros(self):
        for fila, col, color in SEGUROS:
            x1 = col * TAM_CASILLA
            y1 = fila * TAM_CASILLA
            x2 = x1 + TAM_CASILLA
            y2 = y1 + TAM_CASILLA
            self.canvas.create_rectangle(x1, y1, x2, y2, fill=color, outline="black")
            self.canvas.create_text((x1+x2)//2, (y1+y2)//2, text="Seguro", fill="white")


    def marcar_meta(self):
        for fila, col, color in META:
            x1 = col * TAM_CASILLA
            y1 = fila * TAM_CASILLA
            x2 = x1 + TAM_CASILLA
            y2 = y1 + TAM_CASILLA
            self.canvas.create_rectangle(x1, y1, x2, y2, fill=color, outline="black")
            self.canvas.create_text((x1+x2)//2, (y1+y2)//2, text="Meta", fill="white")
    
    def dibujar_ficha(self, fila, col, color):
        x1 = col * TAM_CASILLA + 5
        y1 = fila * TAM_CASILLA + 5
        x2 = x1 + TAM_CASILLA - 10
        y2 = y1 + TAM_CASILLA - 10
        self.canvas.create_oval(x1, y1, x2, y2, fill=color, outline="black")



if __name__ == "__main__":
    root = tk.Tk()
    root.title("Tablero de Parqués")
    tablero = TableroParques(root)
    root.mainloop()
