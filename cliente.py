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

if __name__ == "__main__":
    cliente()
    print("[!] Conexión cerrada.")
    