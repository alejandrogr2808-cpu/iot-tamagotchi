import time
import network
import urequests
import ujson
from machine import Pin, I2C
import _thread
import framebuf
import ssd1306

# ── Credenciales ────────────────────────────────────────────────
secrets = {
    'ssid':     "INFINITUM54C7_2.4",
    'pw':       "KY4AXpC4xa",
    'botToken': '8706517317:AAE-7tHArd3L2GR8_cT0hN9tM6KBbQlvogU',
    'miUid':    '5867292574',
    'noviaUid': "1529279166",
    'steam_id64': "76561199034196805"
}

# ── Hardware ────────────────────────────────────────────────────
led_red   = Pin(14, Pin.OUT)
led_blue  = Pin(15, Pin.OUT)
led_pink  = Pin(16, Pin.OUT)
led_green = Pin(19, Pin.OUT)
buzzer    = Pin(17, Pin.OUT)

btn_salir_novia   = Pin(20, Pin.IN, Pin.PULL_UP)
btn_salir_mia     = Pin(21, Pin.IN, Pin.PULL_UP)
btn_modo_descanso = Pin(22, Pin.IN, Pin.PULL_UP)
btn_modo_juego    = Pin(18, Pin.IN, Pin.PULL_UP)
btn_salir_steam   = Pin(26, Pin.IN, Pin.PULL_UP)

i2c     = I2C(0, sda=Pin(4), scl=Pin(5), freq=400000)
display = ssd1306.SSD1306_I2C(128, 64, i2c)

# ── Buffer único — solo 1 KB de RAM para todas las animaciones ──
_buf = bytearray(1024)
_fb  = framebuf.FrameBuffer(_buf, 128, 64, framebuf.MONO_HLSB)

# ── Diccionario de animaciones (solo strings, no bytearrays) ────
ANIMACIONES = {
    'idle': {
        'frames':     ['idle_1.bin', 'idle_2.bin', 'idle_3.bin', 'idle_4.bin'],
        'timings':    [300, 600, 300, 600],
        'loop_start': 0,
    },
    'steam': {
        'frames':     ['steam_1.bin', 'steam_2.bin', 'steam_3.bin',
                       'steam_4.bin', 'steam_5.bin', 'steam_6.bin', 'steam_7.bin'],
        'timings':    [300, 300, 300, 300, 600, 300, 600],
        'loop_start': 3,
    },
    'love': {
        'frames':     ['love_1.bin', 'love_2.bin', 'love_3.bin',
                       'love_4.bin', 'love_5.bin'],
        'timings':    [300, 300, 600, 300, 600],
        'loop_start': 1,
    },
    'break': {
        'frames':     ['break_1.bin', 'break_2.bin', 'break_3.bin',
                       'break_4.bin', 'break_5.bin'],
        'timings':    [400, 400, 400, 400, 400],
        'loop_start': 1,
    },
    'message': {
        'frames':     ['msg_1.bin', 'msg_2.bin', 'msg_3.bin',
                       'msg_4.bin', 'msg_5.bin', 'msg_6.bin', 'msg_7.bin'],
        'timings':    [400, 400, 400, 300, 600, 300, 600],
        'loop_start': 3,
    },
    'game': {
        'frames':     ['game_1.bin', 'game_2.bin', 'game_3.bin', 'game_4.bin', 'game_5.bin', 'game_6.bin', 'game_7.bin', 'game_8.bin'],
        'timings':    [300, 300, 300, 300, 500, 300, 300, 300],
        'loop_start': 5,
    },
}

# ── Estado compartido ───────────────────────────────────────────
estado = {
    'notif_novia':    False,
    'notif_mia':      False,
    'modo_descanso':  False,
    'modo_juego':     False,
    'notif_steam':    False,
    'ultimo_descanso': time.time(),
    'wifi_ok':        False,
}

network_lock       = _thread.allocate_lock()
URL_TELEGRAM       = f"https://api.telegram.org/bot{secrets['botToken']}"
INTERVALO_TELEGRAM = 15

# ── Variables de animación ──────────────────────────────────────
anim_actual      = 'idle'
frame_idx        = 0
ultimo_cambio_ms = time.ticks_ms()
_archivo_actual  = ''

# ── Debounce de botones ─────────────────────────────────────────
_btn_cooldown = {'novia': 0, 'mia': 0, 'descanso': 0, 'juego': 0, 'steam': 0}
DEBOUNCE_MS   = 250
_btn_juego_ant = 1

# ════════════════════════════════════════════════════════════════
# FUNCIONES
# ════════════════════════════════════════════════════════════════

def rutina_prueba_hardware():
    print("Probando LEDs...")
    led_red.on()
    led_blue.on()
    led_pink.on()
    led_green.on()
    buzzer.value(1)
    time.sleep(1)
    led_red.off()
    led_blue.off()
    led_pink.off()
    led_green.off()
    buzzer.value(0)
    print("Prueba finalizada.")

def sonar_alarma(veces=3):
    for _ in range(veces):
        buzzer.value(1)
        time.sleep_ms(100)
        buzzer.value(0)
        time.sleep_ms(100)

def _animacion_prioritaria():
    if estado['notif_novia']:   return 'love'
    if estado['notif_mia']:     return 'message'
    if estado['modo_descanso']: return 'break'
    if estado['modo_juego']:    return 'game'
    if estado['notif_steam']:   return 'steam'
    return 'idle'

def _cargar_frame(nombre_archivo):
    global _archivo_actual
    if nombre_archivo == _archivo_actual:
        return
    try:
        with open(nombre_archivo, 'rb') as f:
            f.readinto(_buf)
        _archivo_actual = nombre_archivo
    except OSError:
        pass

def animar_tamagotchi():
    global anim_actual, frame_idx, ultimo_cambio_ms, _archivo_actual

    requerida = _animacion_prioritaria()
    if requerida != anim_actual:
        anim_actual      = requerida
        frame_idx        = 0
        ultimo_cambio_ms = time.ticks_ms()
        _archivo_actual  = ''

    cfg      = ANIMACIONES[anim_actual]
    frames   = cfg['frames']
    timings  = cfg['timings']
    loop_st  = cfg['loop_start']

    ahora = time.ticks_ms()
    if time.ticks_diff(ahora, ultimo_cambio_ms) >= timings[frame_idx]:
        frame_idx += 1
        if frame_idx >= len(frames):
            frame_idx = loop_st
        ultimo_cambio_ms = ahora

    _cargar_frame(frames[frame_idx])

    display.fill(0)
    display.blit(_fb, 0, 0)
    display.show()

def leer_botones():
    global _btn_juego_ant
    ahora = time.ticks_ms()

    if (btn_salir_novia.value() == 0
            and time.ticks_diff(ahora, _btn_cooldown['novia']) > DEBOUNCE_MS):
        estado['notif_novia'] = False
        led_pink.off()
        _btn_cooldown['novia'] = ahora

    if (btn_salir_mia.value() == 0
            and time.ticks_diff(ahora, _btn_cooldown['mia']) > DEBOUNCE_MS):
        estado['notif_mia'] = False
        led_red.off()
        _btn_cooldown['mia'] = ahora

    if (btn_modo_descanso.value() == 0
            and time.ticks_diff(ahora, _btn_cooldown['descanso']) > DEBOUNCE_MS
            and estado['modo_descanso']):
        estado['modo_descanso'] = False
        led_green.off()
        estado['ultimo_descanso'] = time.time()
        _btn_cooldown['descanso'] = ahora

    btn_juego_actual = btn_modo_juego.value()
    if (btn_juego_actual == 0 and _btn_juego_ant == 1
            and time.ticks_diff(ahora, _btn_cooldown['juego']) > DEBOUNCE_MS):
        estado['modo_juego'] = not estado['modo_juego']
        _btn_cooldown['juego'] = ahora
    _btn_juego_ant = btn_juego_actual

    if (btn_salir_steam.value() == 0
            and time.ticks_diff(ahora, _btn_cooldown['steam']) > DEBOUNCE_MS):
        estado['notif_steam'] = False
        led_blue.off()
        _btn_cooldown['steam'] = ahora

# ════════════════════════════════════════════════════════════════
# WIFI
# ════════════════════════════════════════════════════════════════

def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(False)
    time.sleep_ms(500)
    wlan.active(True)
    wlan.connect(secrets['ssid'], secrets['pw'])
    print('Conectando a WiFi', end='')
    for _ in range(15):
        if wlan.isconnected():
            break
        time.sleep(1)
        print('.', end='')
    if wlan.isconnected():
        print(f'\nConectado: {wlan.ifconfig()[0]}')
        estado['wifi_ok'] = True
        sonar_alarma(1)
    else:
        print('\nOFFLINE.')
        sonar_alarma(2)

# ════════════════════════════════════════════════════════════════
# HILO DE RED — Core 1
# ════════════════════════════════════════════════════════════════

def hilo_red():
    last_update_id    = 0
    last_check        = time.time()
    last_steam_check  = time.time() - 15   # primera revisión a los 5 seg de arrancar
    ultimo_modo_juego = False
    INTERVALO_STEAM   = 20

    def enviar_aviso_novia():
        print("Enviando aviso a novia...")
        url = (f"{URL_TELEGRAM}/sendMessage"
               f"?chat_id={secrets['noviaUid']}"
               "&text=%C2%A1Hola%21+Estoy+jugando+ahora+mismo+%F0%9F%8E%AE")
        try:
            with network_lock:
                r = urequests.get(url)
                r.close()
        except Exception as e:
            print(f'[red] aviso: {e}')

    def check_updates():
        nonlocal last_update_id
        url = (f"{URL_TELEGRAM}/getUpdates"
               f"?offset={last_update_id + 1}&timeout=1")
        try:
            with network_lock:
                r = urequests.get(url)
            if r.status_code == 200:
                for upd in r.json().get('result', []):
                    last_update_id = upd['update_id']
                    msg = upd.get('message', {})
                    cid = str(msg.get('from', {}).get('id', ''))
                    if cid == secrets['noviaUid']:
                        estado['notif_novia'] = True
                        led_pink.on()
                    elif cid == secrets['miUid']:
                        estado['notif_mia'] = True
                        led_red.on()
            r.close()
        except Exception as e:
            print(f'[red] telegram: {e}')

    def check_steam():
        print("Revisando Steam via API...")
        import gc
        gc.collect()

        # URL de tu app en Render
        API_URL = "https://steam-wishlist-api.onrender.com/steam"

        r = None
        try:
            with network_lock:
                r = urequests.get(API_URL)

            if r.status_code == 200:
                resultado = r.text.strip()
                r.close()
                print(f"[steam] API: '{resultado}'")

                if resultado == "1":
                    estado['notif_steam'] = True
                    led_blue.on()
                    print("[steam] Oferta encontrada.")
                elif resultado == "0":
                    print("[steam] Sin ofertas.")

            elif r.status_code == 503:
                print("[steam] Cookie expirada — actualiza en Render dashboard")
                r.close()
            else:
                print(f"[steam] HTTP {r.status_code}")
                r.close()

        except Exception as e:
            print(f"[steam] error: {e}")
        finally:
            if r:
                try:
                    r.close()
                except Exception:
                    pass
        gc.collect()

    # ── Loop principal del hilo ─────────────────────────────────
    while True:
        if not estado['wifi_ok']:
            time.sleep(1)
            continue

        if estado['modo_juego'] and not ultimo_modo_juego:
            enviar_aviso_novia()
        ultimo_modo_juego = estado['modo_juego']

        ahora = time.time()

        if ahora - last_check >= INTERVALO_TELEGRAM:
            check_updates()
            last_check = ahora

        if ahora - last_steam_check >= INTERVALO_STEAM:
            check_steam()
            last_steam_check = ahora

        time.sleep(0.5)
# ════════════════════════════════════════════════════════════════
# ARRANQUE
# ════════════════════════════════════════════════════════════════

rutina_prueba_hardware()
connect_wifi()
_thread.start_new_thread(hilo_red, ())

while True:
    if time.time() - estado['ultimo_descanso'] >= 7200:
        estado['modo_descanso'] = True
        led_green.on()
        sonar_alarma(3)
        estado['ultimo_descanso'] = time.time()

    leer_botones()
    animar_tamagotchi()
    time.sleep_ms(10)