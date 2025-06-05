import socket
import threading
import json
import random
import time

# Server Configuration
HOST = '0.0.0.0'  # Accept connections from any IP
PORT = 5000

jugadores = []
colores_disponibles = ["red", "blue", "green", "yellow"]
turno_actual_idx = 0 # Index in the players list
bloqueo_turnos = threading.Lock() # Para controlar el acceso a variables compartidas (jugadores, turno_actual_idx, juego_iniciado)
max_jugadores = 4
min_jugadores_para_iniciar = 2
juego_iniciado = False
dados_lanzados = False # Flag to ensure dice is rolled before moving piece
ultimo_dado_resultado = 0 # Store the last dice roll for the current player
ultimo_dado_dobles = False # Flag if last roll was doubles

# Definiciones de caminos y casillas especiales
# CAMINO_GLOBAL: Lista de tuplas (fila, columna) que representan el camino principal del tablero.
CAMINO_GLOBAL = [
    (7,0),(7,1),(7,2),(7,3),(7,4),(7,5),(7,6),(7,7), # Camino horizontal rojo/verde
    (6,7),(5,7),(4,7),(3,7),(2,7),(1,7),(0,7), # Camino vertical rojo/azul
    (0,8),(0,9),(0,10), # Esquinas superiores
    (1,10),(2,10),(3,10),(4,10),(5,10),(6,10),(7,10), # Camino vertical azul/amarillo
    (7,11),(7,12),(7,13),(7,14),(7,15),(7,16),(7,17), # Camino horizontal azul/amarillo
    (8,17),(9,17),(10,17), # Esquinas derechas
    (10,16),(10,15),(10,14),(10,13),(10,12),(10,11),(10,10), # Camino horizontal verde/amarillo
    (11,10),(12,10),(13,10),(14,10),(15,10),(16,10),(17,10), # Camino vertical verde/amarillo
    (17,9),(17,8),(17,7), # Esquinas inferiores
    (16,7),(15,7),(14,7),(13,7),(12,7),(11,7),(10,7), # Camino vertical verde/rojo
    (10,6),(10,5),(10,4),(10,3),(10,2),(10,1),(10,0), # Camino horizontal verde/rojo
    (9,0),(8,0) # Esquinas izquierdas
]

# Puntos de entrada al camino global desde las cárceles (índices en CAMINO_GLOBAL)
ENTRADAS_GLOBAL = {
    "red":    CAMINO_GLOBAL.index((7,0)),
    "blue":   CAMINO_GLOBAL.index((0,10)),
    "green":  CAMINO_GLOBAL.index((10,17)),
    "yellow": CAMINO_GLOBAL.index((17,7))
}

# Caminos de meta (casa) para cada color. La última posición es el centro (8,8)
CAMINOS_META = {
    "red":    [(8,1), (8,2), (8,3), (8,4), (8,5), (8,6), (8,7), (8,8)],
    "blue":   [(1,8), (2,8), (3,8), (4,8), (5,8), (6,8), (7,8), (8,8)],
    "green":  [(9,16), (9,15), (9,14), (9,13), (9,12), (9,11), (9,10), (8,8)],
    "yellow": [(16,9), (15,9), (14,9), (13,9), (12,9), (11,9), (10,9), (8,8)]
}

# Casillas seguras donde las fichas no pueden ser "comidas"
CASILLAS_SEGURAS = [
    (7,0), (0,7), (0,8), (0,9), (0,10), (7,10), (7,17), (8,17), (9,17), (10,17),
    (10,10), (10,0), (9,0), (8,0), (17,7), (17,8), (17,9), (17,10),
    # Las salidas también son seguras
    (4,7), (7,13), (10,4), (13,10)
]

# Coordenadas de las cárceles (solo para referencia visual en el cliente)
CARCELES_COORDS = {
    "red":    [(1, 1), (1, 2), (2, 1), (2, 2)],
    "blue":   [(1, 15), (1, 16), (2, 15), (2, 16)],
    "green":  [(15, 1), (15, 2), (16, 1), (16, 2)],
    "yellow": [(15, 15), (15, 16), (16, 15), (16, 16)]
}

class Jugador:
    def __init__(self, conn, addr, nombre, color):
        self.conn = conn
        self.addr = addr
        self.nombre = nombre
        self.color = color
        # ficha_estado: 0=en cárcel, 1=en camino global, 2=en camino meta, 3=llegó a meta final
        self.ficha_estado = [0] * 4 
        # ficha_pos: -1=en cárcel, índice en CAMINO_GLOBAL para global, índice en CAMINOS_META para meta
        self.ficha_pos = [-1] * 4 
        self.ultimo_dado = 0
        self.pares_consecutivos = 0 # Para la regla de 3 pares
        self.fichas_en_meta_final = [False] * 4 # True if piece reached the very center (8,8)

def enviar_mensaje(jugador_o_conn, mensaje_dict):
    try:
        mensaje_str = json.dumps(mensaje_dict)
        if isinstance(jugador_o_conn, Jugador):
            jugador_o_conn.conn.send(mensaje_str.encode())
        else: # Assuming it's a raw socket connection
            jugador_o_conn.send(mensaje_str.encode())
    except Exception as e:
        print(f"[-] Error al enviar mensaje a {jugador_o_conn.nombre if isinstance(jugador_o_conn, Jugador) else 'cliente'}: {e}")
        # Aquí se podría manejar la desconexión del cliente si el error es de conexión

def enviar_a_todos(mensaje_dict, except_jugador=None):
    for jugador in jugadores:
        if jugador != except_jugador:
            enviar_mensaje(jugador, mensaje_dict)

def iniciar_partida():
    global juego_iniciado, turno_actual_idx, dados_lanzados
    print("[DEBUG] ¡entrando a iniciar partida!")
    enviar_turno()
    
    with bloqueo_turnos:
        if not juego_iniciado and len(jugadores) >= min_jugadores_para_iniciar:
            # Inicializar estado del juego
            juego_iniciado = True
            turno_actual_idx = 0
            dados_lanzados = False
            
            # Mostrar información de inicio
            print("[!] Iniciando partida con los siguientes jugadores:")
            for i, j in enumerate(jugadores):
                print(f"  {i+1}. {j.nombre} ({j.color})")
                # Resetear estado del jugador
                j.ultimo_dado = 0
                j.pares_consecutivos = 0
                j.ficha_estado = [0] * 4
                j.ficha_pos = [-1] * 4
            
            # Notificar inicio del juego a todos
            enviar_a_todos({
                "tipo": "info", 
                "mensaje": "El juego ha iniciado! Preparando el primer turno..."
            })
            time.sleep(1)  # Dar tiempo a los clientes para actualizar
            
            # Enviar mensaje de turno inicial al primer jugador
            primer_jugador = jugadores[0]
            enviar_mensaje(primer_jugador, {
                "tipo": "turno",
                "mensaje": f"Es tu turno, {primer_jugador.nombre}. Lanza el dado.",
                "es_tu_turno": True
            })
            
            # Notificar a los demás jugadores
            for j in jugadores[1:]:
                enviar_mensaje(j, {
                    "tipo": "turno",
                    "mensaje": f"Turno de {primer_jugador.nombre}",
                    "es_tu_turno": False
                })
            
            print(f"[+] Turno inicial asignado a {primer_jugador.nombre} ({primer_jugador.color})")
            print("[!] La partida está en curso.")
            return True
        else:
            print(f"[!] No hay suficientes jugadores para iniciar. Mínimo {min_jugadores_para_iniciar} requeridos.")
            return False
def enviar_turno():
    global turno_actual_idx
    with bloqueo_turnos:
        if not jugadores:
            print("[!] No hay jugadores para enviar turno.")
            return

        print(f"[+] Turno asignado a {jugadores[turno_actual_idx].nombre} ({jugadores[turno_actual_idx].color})")

        for i, jugador in enumerate(jugadores):
            es_tu_turno = (i == turno_actual_idx)
            mensaje ={ "tipo": "turno",
                      "mensaje": f"Es tu turno, {jugador.nombre}." if es_tu_turno else f"Turno de {jugadores[turno_actual_idx].nombre}.",
                      "es_tu_turno": es_tu_turno}
            try:
                enviar_mensaje(jugador, mensaje)
                print(f"[+] Enviado turno a {jugador.nombre} ({jugador.color}) - Es tu turno: {es_tu_turno}")
            except Exception as e:
                print(f"[-] Error enviando turno a {jugador.nombre}: {e}")
            

        # Resetear estado de los dados y movimientos solo si el juego sigue en curso
        if juego_iniciado:
            dados_lanzados = False
            jugadores[turno_actual_idx].ultimo_dado = 0
            jugadores[turno_actual_idx].pares_consecutivos = 0

def obtener_posibles_movimientos(jugador, dado_total):
    movible_fichas = []
    
    # Regla: Con pares, puedes sacar una ficha de la cárcel O mover una ficha.
    # Si tiene fichas en cárcel Y sacó pares, puede sacar una.
    if ultimo_dado_dobles:
        for i in range(4):
            if jugador.ficha_estado[i] == 0: # Si está en cárcel
                movible_fichas.append(i) # Puede sacar esta ficha
        if movible_fichas: # Si hay fichas en cárcel y sacó pares, solo puede sacar una
            return movible_fichas # Devuelve solo las fichas en cárcel para esta opción

    # Si no tiene pares, o ya sacó su ficha de cárcel o no tiene más en cárcel
    for i in range(4):
        if jugador.ficha_estado[i] == 1: # En camino global
            actual_pos_idx = jugador.ficha_pos[i]
            nueva_pos_idx = actual_pos_idx + dado_total
            
            # Check if moving into meta path
            if nueva_pos_idx >= len(CAMINO_GLOBAL):
                # Calcular cuántos pasos le quedan para entrar y moverse en la meta
                pasos_en_meta = nueva_pos_idx - len(CAMINO_GLOBAL) 
                if pasos_en_meta < len(CAMINOS_META[jugador.color]): # No se pasa de la meta
                    movible_fichas.append(i)
                elif pasos_en_meta == len(CAMINOS_META[jugador.color]) - 1: # Cae exactamente en la casilla final
                     movible_fichas.append(i)
            else: # Sigue en el camino global
                movible_fichas.append(i)
        elif jugador.ficha_estado[i] == 2: # En camino meta
            actual_meta_idx = jugador.ficha_pos[i]
            nueva_meta_idx = actual_meta_idx + dado_total
            if nueva_meta_idx < len(CAMINOS_META[jugador.color]):
                movible_fichas.append(i)
            elif nueva_meta_idx == len(CAMINOS_META[jugador.color]) -1: # Cae exactamente en la casilla final
                 movible_fichas.append(i)
    
    return movible_fichas


def manejar_lanzamiento_dado(jugador):
    global turno_actual_idx, dados_lanzados, ultimo_dado_resultado, ultimo_dado_dobles, juego_iniciado
    
    with bloqueo_turnos:
        if not juego_iniciado:
            enviar_mensaje(jugador, {
                "tipo": "info", "mensaje": "El juego aún no ha iniciado."
                })
            return
        if jugadores[turno_actual_idx] != jugador:
            enviar_mensaje(jugador, {
                "tipo": "info",
                "mensaje": "No es tu turno."
                })
            return
        if dados_lanzados:
            enviar_mensaje(jugador, {
                "tipo": "error",
                "mensaje": "Ya lanzaste los dados en este turno. Ahora mueve una ficha."
                })
            return

        dado1 = random.randint(1, 6)
        dado2 = random.randint(1, 6)
        jugador.ultimo_dado = dado1 + dado2
        print(f"[+] {jugador.nombre} lanzó {dado1} y {dado2} (Total: {jugador.ultimo_dado})")

        dados_lanzados = True

        if dado1 == dado2:
            jugador.pares_consecutivos += 1
            ultimo_dado_dobles = True
            enviar_mensaje(jugador, {
                "tipo": "info", 
                "mensaje": f"Sacaste pares ({dado1} y {dado2}), puedes lanzar de nuevo o sacar una ficha de la cárcel."
                })
        else:
            jugador.pares_consecutivos = 0 # Reset consecutive doubles
            ultimo_dado_dobles = False
            
        # Check for three consecutive doubles (regla especial)
        if jugador.pares_consecutivos >= 3:
            print(f"[!] {jugador.nombre} ha sacado 3 pares consecutivos. Enviando ficha a la cárcel.")
            enviar_mensaje(jugador, {
                "tipo": "info", 
                "mensaje": f"¡Sacaste 3 pares consecutivos! Una de tus fichas irá a la cárcel (si tienes alguna en juego). Pasando turno."
                })
            # Lógica para enviar una ficha a la cárcel (ej. la primera en juego)
            for i in range(4):
                if jugador.ficha_estado[i] == 1 or jugador.ficha_estado[i] == 2: # Si está en juego o en meta
                    old_coords = CAMINO_GLOBAL[jugador.ficha_pos[i]] if jugador.ficha_estado[i] == 1 else CAMINOS_META[jugador.color][jugador.ficha_pos[i]]

                    if jugador.ficha_estado[i] == 1: old_coords = CAMINO_GLOBAL[jugador.ficha_pos[i]]
                    elif jugador.ficha_estado[i] == 2: old_coords = CAMINOS_META[jugador.color][jugador.ficha_pos[i]]

                    jugador.ficha_estado[i] = 0 # A la cárcel
                    jugador.ficha_pos[i] = -1
                    enviar_a_todos({
                        "tipo": "movimiento",
                        "color": jugador.color,
                        "ficha_idx": i,
                        "desde": old_coords,
                        "hasta": "carcel"
                    })
                    break # Solo una ficha va a la cárcel
            
            jugador.pares_consecutivos = 0 # Reset para la próxima vez
            turno_actual_idx = (turno_actual_idx + 1) % len(jugadores)
            enviar_turno()
            return

        # Enviar resultado de dados y posibles movimientos
        movible_fichas = obtener_posibles_movimientos(jugador, jugador.ultimo_dado)
        
        if not movible_fichas:
            mensaje_no_mov = "No tienes movimientos posibles con este dado. Pasando turno."
            enviar_mensaje(jugador, {
                "tipo": "info",
                "mensaje": mensaje_no_mov})
            
            # Pasar turno si no hay movimientos
            if not ultimo_dado_dobles: # Solo si no sacó pares (si sacó pares y no tiene movimientos, pierde el bonus de re-lanzar)
                turno_actual_idx = (turno_actual_idx + 1) % len(jugadores)
            enviar_turno()
            dados_lanzados = False # Reset for next player/turn
        else:
            # Enviamos los dados y las fichas movibles
            print(f"[+] Dados lanzados: {dado1} y {dado2} (Total: {jugador.ultimo_dado})")
            enviar_mensaje(jugador, {
                "tipo": "dados",
                "dado1": dado1,
                "dado2": dado2,
                "total": dado1 + dado2,
                "movible_fichas": movible_fichas
                })
            # Si sacó pares, el cliente automáticamente habilitará el botón de dado para re-lanzar si no ha movido ficha.
            # No se pasa el turno aquí.

def manejar_mover_ficha(jugador, ficha_idx):
    global turno_actual_idx, dados_lanzados, ultimo_dado_dobles, juego_iniciado

    with bloqueo_turnos:
        if not juego_iniciado or jugadores[turno_actual_idx] != jugador:
            enviar_mensaje(jugador, {"tipo": "info", "mensaje": "No es tu turno o el juego no ha iniciado."})
            return
        if not dados_lanzados:
            enviar_mensaje(jugador, {"tipo": "error", "mensaje": "Primero debes lanzar el dado."})
            return
        if ficha_idx < 0 or ficha_idx >= 4:
            enviar_mensaje(jugador, {"tipo": "error", "mensaje": "Índice de ficha inválido."})
            return
        
        # Validar si el movimiento es posible con el dado actual
        posibles_movimientos = obtener_posibles_movimientos(jugador, jugador.ultimo_dado)
        if ficha_idx not in posibles_movimientos:
            enviar_mensaje(jugador, {
                "tipo": "error", 
                "mensaje": "Movimiento de ficha no válido para el dado actual.",
                "reintentar_turno": True, # Indicar al cliente que puede reintentar
                "movible_fichas_reintentar": posibles_movimientos
            })
            return

        dado_total = jugador.ultimo_dado
        old_coords = None # Coordenadas antiguas para el borrado visual en el cliente
        
        # Lógica para sacar ficha de la cárcel
        if jugador.ficha_estado[ficha_idx] == 0: # Si la ficha está en la cárcel
            if not ultimo_dado_dobles: # Solo se puede sacar con pares
                enviar_mensaje(jugador, {
                    "tipo": "error", 
                    "mensaje": "Solo puedes sacar fichas de la cárcel con pares.",
                    "reintentar_turno": True,
                    "movible_fichas_reintentar": posibles_movimientos
                })
                return
            
            old_coords = "carcel" # La posición de la cárcel
            jugador.ficha_estado[ficha_idx] = 1 # Ahora está en el camino global
            jugador.ficha_pos[ficha_idx] = ENTRADAS_GLOBAL[jugador.color] # Posición de salida
            new_coords = CAMINO_GLOBAL[jugador.ficha_pos[ficha_idx]]

            enviar_a_todos({
                "tipo": "movimiento",
                "color": jugador.color,
                "ficha_idx": ficha_idx,
                "desde": old_coords,
                "hasta": {"fila": new_coords[0], "col": new_coords[1]}
            })
            enviar_a_todos({"tipo": "info", "mensaje": f"¡{jugador.nombre} sacó la ficha {ficha_idx+1} de la cárcel!"})
            
            dados_lanzados = False # Se resetea el flag para la próxima acción (re-lanzar o pasar turno)
            if not ultimo_dado_dobles: # Si no sacó pares, pasa el turno
                turno_actual_idx = (turno_actual_idx + 1) % len(jugadores)
            enviar_turno() # Enviar el siguiente turno o permitir re-lanzar
            return
        
        # Lógica para mover fichas que ya están en juego (global o meta)
        elif jugador.ficha_estado[ficha_idx] == 1: # En camino global
            actual_pos_idx = jugador.ficha_pos[ficha_idx]
            nueva_pos_idx = actual_pos_idx + dado_total
            
            old_coords = CAMINO_GLOBAL[actual_pos_idx] # Coordenadas actuales
            new_coords = None

            # Entrando a la meta
            if nueva_pos_idx >= len(CAMINO_GLOBAL):
                pasos_en_meta = nueva_pos_idx - len(CAMINO_GLOBAL)
                
                if pasos_en_meta < len(CAMINOS_META[jugador.color]):
                    new_coords = CAMINOS_META[jugador.color][pasos_en_meta]
                    jugador.ficha_estado[ficha_idx] = 2 # Estado: en meta
                    jugador.ficha_pos[ficha_idx] = pasos_en_meta
                elif pasos_en_meta == len(CAMINOS_META[jugador.color]) -1: # Llega exactamente al centro (meta final)
                    new_coords = CAMINOS_META[jugador.color][pasos_en_meta]
                    jugador.ficha_estado[ficha_idx] = 3 # Estado: llegó a meta final
                    jugador.fichas_en_meta_final[ficha_idx] = True
                    enviar_a_todos({"tipo": "info", "mensaje": f"¡{jugador.nombre} ha llevado la ficha {ficha_idx+1} a la meta!"})
                else: # Se pasó de la meta
                    enviar_mensaje(jugador, {
                        "tipo": "error", 
                        "mensaje": "No puedes mover esa ficha. Excedes la meta.",
                        "reintentar_turno": True,
                        "movible_fichas_reintentar": posibles_movimientos
                    })
                    return
            else: # Sigue en el camino global
                new_coords = CAMINO_GLOBAL[nueva_pos_idx]
                jugador.ficha_pos[ficha_idx] = nueva_pos_idx
            
            # Verificar si come ficha de otro jugador (solo si no es casilla segura)
            if new_coords not in CASILLAS_SEGURAS:
                for otro_jugador in jugadores:
                    if otro_jugador == jugador:
                        continue
                    for i_otro_ficha in range(4):
                        # Solo si la ficha del otro jugador está en el camino global y en la misma posición
                        if otro_jugador.ficha_estado[i_otro_ficha] == 1 and \
                           CAMINO_GLOBAL[otro_jugador.ficha_pos[i_otro_ficha]] == new_coords:
                            
                            # Enviar la ficha comida a la cárcel
                            otro_jugador.ficha_estado[i_otro_ficha] = 0
                            otro_jugador.ficha_pos[i_otro_ficha] = -1
                            enviar_a_todos({
                                "tipo": "movimiento",
                                "color": otro_jugador.color,
                                "ficha_idx": i_otro_ficha,
                                "desde": {"fila": new_coords[0], "col": new_coords[1]},
                                "hasta": "carcel"
                            })
                            enviar_a_todos({"tipo": "info", "mensaje": f"¡{jugador.nombre} ha comido la ficha {i_otro_ficha+1} de {otro_jugador.nombre}!"})
                            break # Solo una ficha puede ser comida por casilla
            
            # Enviar actualización de movimiento a todos los clientes
            enviar_a_todos({
                "tipo": "movimiento",
                "color": jugador.color,
                "ficha_idx": ficha_idx,
                "desde": {"fila": old_coords[0], "col": old_coords[1]} if isinstance(old_coords, tuple) else old_coords, # Asegurar formato
                "hasta": {"fila": new_coords[0], "col": new_coords[1]}
            })

        elif jugador.ficha_estado[ficha_idx] == 2: # En camino meta
            actual_meta_idx = jugador.ficha_pos[ficha_idx]
            nueva_meta_idx = actual_meta_idx + dado_total
            
            old_coords = CAMINOS_META[jugador.color][actual_meta_idx]
            new_coords = None

            if nueva_meta_idx < len(CAMINOS_META[jugador.color]):
                new_coords = CAMINOS_META[jugador.color][nueva_meta_idx]
                jugador.ficha_pos[ficha_idx] = nueva_meta_idx
            elif nueva_meta_idx == len(CAMINOS_META[jugador.color]) -1: # Llega exactamente al centro (meta final)
                new_coords = CAMINOS_META[jugador.color][nueva_meta_idx]
                jugador.ficha_estado[ficha_idx] = 3 # Estado: llegó a meta final
                jugador.fichas_en_meta_final[ficha_idx] = True
                enviar_a_todos({"tipo": "info", "mensaje": f"¡{jugador.nombre} ha llevado la ficha {ficha_idx+1} a la meta!"})
            else: # Se pasó de la meta
                enviar_mensaje(jugador, {
                    "tipo": "error", 
                    "mensaje": "No puedes mover esa ficha. Excedes la meta.",
                    "reintentar_turno": True,
                    "movible_fichas_reintentar": posibles_movimientos
                })
                return
            
            enviar_a_todos({
                "tipo": "movimiento",
                "color": jugador.color,
                "ficha_idx": ficha_idx,
                "desde": {"fila": old_coords[0], "col": old_coords[1]},
                "hasta": {"fila": new_coords[0], "col": new_coords[1]}
            })

        # Comprobar condición de victoria después de cada movimiento
        if all(jugador.fichas_en_meta_final):
            enviar_a_todos({"tipo": "info", "mensaje": f"🎉 ¡{jugador.nombre} ({jugador.color}) ha ganado la partida! 🎉"})
            print(f"[*] ¡{jugador.nombre} ha ganado el juego!")
            # Aquí podrías añadir lógica para reiniciar el juego o cerrar el servidor
            for j in jugadores: # Cerrar conexiones de todos los jugadores
                try:
                    j.conn.close()
                except:
                    pass
            jugadores.clear() # Limpiar la lista de jugadores
            
            juego_iniciado = False
            return # Terminar la función

        dados_lanzados = False # Reiniciar el flag para el próximo turno

        # Avanzar turno (solo si no se sacaron pares en el lanzamiento que llevó a este movimiento)
        if not ultimo_dado_dobles:
            turno_actual_idx = (turno_actual_idx + 1) % len(jugadores)
        
        enviar_turno()


def manejar_cliente(conn, addr):
    global juego_iniciado
    print(f"[+] Nueva conexión desde {addr}")

    try:
        nombre = conn.recv(1024).decode().strip()
        if not nombre:
            print(f"[-] Cliente {addr} no envió nombre. Desconectando.")
            conn.close()
            return
    except Exception as e:
        print(f"[-] Error al recibir nombre de {addr}: {e}")
        conn.close()
        return

    with bloqueo_turnos: # Protege la lista de jugadores y colores_disponibles
        if not colores_disponibles:
            enviar_mensaje(conn, {"tipo": "error", "mensaje": "No hay cupos disponibles. Conexión rechazada."})
            conn.close()
            print(f"[-] Conexión rechazada para {nombre} desde {addr}: No hay colores disponibles.")
            return
        
        if juego_iniciado:
            enviar_mensaje(conn, {"tipo": "error", "mensaje": "El juego ya ha iniciado. No se permiten nuevas conexiones."})
            conn.close()
            print(f"[-] Conexión rechazada para {nombre} desde {addr}: Juego en curso.")
            return

        # Asignar color y crear jugador
        color = colores_disponibles.pop(0)
        jugador = Jugador(conn, addr, nombre, color)
        jugadores.append(jugador)
        print(f"[+] {nombre} se ha unido con color {color}. Total de jugadores: {len(jugadores)}")

        # Enviar color al nuevo jugador
        enviar_mensaje(jugador, {"tipo": "color", "color": jugador.color})
        print(f"[+] Color asignado a {jugador.nombre}: {jugador.color}")

        # Notificar a los demás jugadores
        enviar_a_todos({
            "tipo": "info", 
            "mensaje": f"{nombre} se ha unido a la partida con color {color}. ({len(jugadores)}/{max_jugadores})"
        }, except_jugador=jugador)

        # Verificar si podemos iniciar el juego
        if len(jugadores) >= min_jugadores_para_iniciar and not juego_iniciado:
            print("[!] Suficientes jugadores para iniciar. Iniciando partida...")
            print(f"[DEBUG] Estado actual: {len(jugadores)} jugadores de {min_jugadores_para_iniciar} mínimo")
            
            # No llamar a iniciar_partida() aquí, en su lugar inicializar el juego directamente
            juego_iniciado = True
            turno_actual_idx = 0
            dados_lanzados = False
            
            # Notificar inicio del juego
            enviar_a_todos({
                "tipo": "info",
                "mensaje": "¡El juego ha iniciado! Preparando el primer turno..."
            })
            time.sleep(1)  # Dar tiempo a los clientes
            
            # Asignar primer turno
            primer_jugador = jugadores[0]
            enviar_mensaje(primer_jugador, {
                "tipo": "turno",
                "mensaje": f"Es tu turno, {primer_jugador.nombre}. Lanza el dado.",
                "es_tu_turno": True
            })
            
            # Notificar a los demás
            for j in jugadores[1:]:
                enviar_mensaje(j, {
                    "tipo": "turno",
                    "mensaje": f"Turno de {primer_jugador.nombre}",
                    "es_tu_turno": False
                })
            
            print(f"[+] Juego iniciado. Primer turno: {primer_jugador.nombre}")

    while True:
        try:
            mensaje_raw = conn.recv(1048).decode() # Aumentado el buffer
            if not mensaje_raw:
                print(f"[-] {jugador.nombre} ({addr}) se ha desconectado (recv vacío).")
                break # Exit the loop to clean up
            
            try:
                data = json.loads(mensaje_raw)
                tipo = data.get("tipo")
                print(f"DEBUG SERVIDOR: Mensaje de {jugador.nombre}: {data}") # DEBUG

                if tipo == "lanzar_dado":
                    print  (f"[+] {jugador.nombre} ha lanzado el dado.")
                    manejar_lanzamiento_dado(jugador)
                elif tipo == "mover_ficha":
                    ficha_idx = data.get("ficha_idx")
                    manejar_mover_ficha(jugador, ficha_idx)
                elif tipo == "desconectar":
                    print(f"[-] {jugador.nombre} ({addr}) ha enviado mensaje de desconexión.")
                    break # Exit the loop to clean up
                else:
                    print(f"[-] Mensaje de tipo desconocido recibido de {jugador.nombre}: {mensaje_raw}")

            except json.JSONDecodeError:
                print(f"[-] Error al decodificar JSON de {jugador.nombre}: {mensaje_raw}")
            except Exception as e:
                print(f"[-] Error al procesar mensaje de {jugador.nombre}: {e}")
                # Optionally send an error message back to the client

        except ConnectionResetError:
            print(f"[-] Conexión perdida con {jugador.nombre} ({addr}).")
            break
        except Exception as e:
            print(f"[-] Error general en manejo de cliente {jugador.nombre}: {e}")
            break

    # Clean up after client disconnects
    with bloqueo_turnos:
        if jugador in jugadores:
            jugadores.remove(jugador)
            colores_disponibles.append(jugador.color) # Return color to available pool
            colores_disponibles.sort() # Keep it sorted
            enviar_a_todos({"tipo": "info", "mensaje": f"{jugador.nombre} ha salido del juego. ({len(jugadores)}/{max_jugadores})"})
            print(f"[-] Conexión finalizada: {addr} ({jugador.nombre})")
            
            if juego_iniciado and len(jugadores) < min_jugadores_para_iniciar:
                juego_iniciado = False
                enviar_a_todos({"tipo": "info", "mensaje": "No hay suficientes jugadores para continuar. El juego se ha detenido."})
                print("[!] Juego detenido por falta de jugadores.")
            elif juego_iniciado and jugadores: # If game is still ongoing and it was their turn
                # Adjust turn index if the current player left and it was their turn or a player before them left
                if turno_actual_idx >= len(jugadores):
                    turno_actual_idx = 0
                elif jugador == jugadores[turno_actual_idx]:
                    turno_actual_idx = (turno_actual_idx + 1) % len(jugadores) #avance al siguiente jugador
                enviar_turno() # Advance turn to the next player

    conn.close()


def iniciar_servidor():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1) # Permite reusar la dirección rápidamente
    try:
        server.bind((HOST, PORT))
        server.listen(4)
        print(f"[Servidor iniciado en {HOST}:{PORT}] Esperando jugadores...")
        
        while True: # Keep accepting connections
            try:
                conn, addr = server.accept()
                print(f"[+] Conexión aceptada de {addr}")
                hilo = threading.Thread(target=manejar_cliente, args=(conn, addr))
                hilo.daemon = True # Allows main program to exit even if threads are running
                hilo.start()
            except Exception as e:
                print(f"[-] Error al aceptar conexión: {e}")
    except KeyboardInterrupt:
        print("\n[!] Servidor detenido por el usuario.")
        server.close()
        for jugador in jugadores:
            try:
                jugador.conn.close()
            except:
                pass
        print("[!] Todas las conexiones han sido cerradas. Saliendo del servidor.")

def iniciar_sincronizacion_automatica():
    while True:
        time.sleep(30)  # cada 30 segundos
        sincronizar_relojes()

threading.Thread(target=iniciar_sincronizacion_automatica, daemon=True).start()




def sincronizar_relojes():
    print("[🕒] Iniciando sincronización de relojes con clientes...")
    tiempos = {}

    for jugador in jugadores:
        try:
            jugador.conn.send(json.dumps({"tipo": "sync_request"}).encode())
            respuesta = jugador.conn.recv(1024).decode()
            tiempos[jugador.nombre] = float(respuesta)
        except Exception as e:
            print(f"[!] Falló la hora de {jugador.nombre}: {e}")

    hora_servidor = time.time()
    total = hora_servidor + sum(tiempos.values())
    promedio = total / (len(tiempos) + 1)

    for jugador in jugadores:
        desfase = promedio - tiempos[jugador.nombre]
        try:
            jugador.conn.send(json.dumps({
                "tipo": "sync_adjust",
                "ajuste": desfase
            }).encode())
        except:
            print(f"[X] No se pudo enviar ajuste a {jugador.nombre}")

    print("[✅] Sincronización de relojes completada.")

if __name__ == "__main__":
    iniciar_servidor()