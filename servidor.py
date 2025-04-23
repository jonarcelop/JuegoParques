import socket
import threading

# Configuración del servidor
HOST = '0.0.0.0'  # Acepta conexiones desde cualquier IP
PORT = 5000

clientes = []
nombres = []
max_jugadores = 4

def manejar_cliente(conn, addr):
    print(f"[+] Nueva conexión desde {addr}")

    nombre = conn.recv(1024).decode()
    nombres.append(nombre)
    clientes.append(conn)

    enviar_a_todos(f"{nombre} se ha unido a la partida.")

    while True:
        try:
            mensaje = conn.recv(1024).decode()
            if not mensaje:
                break
            enviar_a_todos(f"{nombre}: {mensaje}")
        except:
            break

    conn.close()
    clientes.remove(conn)
    nombres.remove(nombre)
    enviar_a_todos(f"{nombre} ha salido del juego.")
    print(f"[-] Conexión finalizada: {addr}")

def enviar_a_todos(mensaje):
    for cliente in clientes:
        try:
            cliente.send(mensaje.encode())
        except:
            continue

def iniciar_servidor():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((HOST, PORT))
    server.listen()
    print(f"[Servidor iniciado en {HOST}:{PORT}] Esperando jugadores...")

    while len(clientes) < max_jugadores:
        conn, addr = server.accept()
        hilo = threading.Thread(target=manejar_cliente, args=(conn, addr))
        hilo.start()

    print("[!] Límite de jugadores alcanzado. No se permiten más conexiones.")

if __name__ == "__main__":
    iniciar_servidor()
    print("[!] Servidor cerrado.")
    for cliente in clientes:
        cliente.close()
    print("Conexiones cerradas.")
    print("Servidor finalizado.")
