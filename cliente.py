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

TAM_CASILLA = 40
FILAS = 15
COLUMNAS = 15

class TableroParques:
    def __init__(self, root):
        self.canvas = tk.Canvas(root, width=COLUMNAS*TAM_CASILLA, height=FILAS*TAM_CASILLA)
        self.canvas.pack()
        self.dibujar_tablero()

    def dibujar_tablero(self):
        for fila in range(FILAS):
            for col in range(COLUMNAS):
                x1 = col * TAM_CASILLA
                y1 = fila * TAM_CASILLA
                x2 = x1 + TAM_CASILLA
                y2 = y1 + TAM_CASILLA

                color = self.obtener_color(fila, col)
                self.canvas.create_rectangle(x1, y1, x2, y2, fill=color, outline="black")

    def obtener_color(self, fila, col):
        # Zonas de cárcel por jugador
        if fila < 6 and col < 6:
            return "red"
        elif fila < 6 and col > 8:
            return "blue"
        elif fila > 8 and col < 6:
            return "green"
        elif fila > 8 and col > 8:
            return "yellow"

        # Camino central (cruz)
        elif 6 <= fila <= 8 or 6 <= col <= 8:
            return "white"

        # Zona central (meta)
        if 6 <= fila <= 8 and 6 <= col <= 8:
            return "gray"

        return "#ccc"

if __name__ == "__main__":
    root = tk.Tk()
    root.title("Tablero de Parqués")
    tablero = TableroParques(root)
    root.mainloop()
