import pygame
from pygame.locals import *
from OpenGL.GL import *
from OpenGL.GLU import *
import math
import sys
import time

# --------------------------------------
# CONFIGURAÇÕES INICIAIS
# --------------------------------------

pygame.init()
display = (1000, 700)
pygame.display.set_mode(display, DOUBLEBUF | OPENGL)

BOTTOM_COLOR = (0.4, 0.0, 0.0)  # Vermelho escuro
MIDDLE_COLOR = (0.0, 0.4, 0.0)  # Verde escuro
TOP_COLOR    = (0.0, 0.0, 0.4)  # Azul escuro

# Cores (normalizadas 0–1 para OpenGL)
ROYAL_BLUE      = (65/255.0, 105/255.0, 225/255.0)
LIGHTER_BLUE    = (100/255.0, 149/255.0, 237/255.0)
FRAME_GRAY      = (0.8, 0.8, 0.8)
BLACK           = (0.0, 0.0, 0.0)
STEP_COLOR      = (0.55, 0.27, 0.07)
LADDER_COLOR    = (0.4, 0.2, 0.1)

# Parâmetros do quarto esférico
SPHERE_RADIUS    = 5.0
FLOOR_Y          = -3.0
MID_FLOOR_Y      = FLOOR_Y + 4.2
TOP_PASSAGE_Y    = SPHERE_RADIUS - 0.1

WINDOW_RADIUS    = 1.5
WINDOW_ANGLES    = [60, 180, 300]
WINDOW_ELEVATION = 0
HOBBIT_WINDOW_RADIUS = 2.0

# ————————————————————————————————
# PARÂMETROS DA RAMPA CURVADA (inferior→intermediário)
# ————————————————————————————————

RAMP_ANGLE_START = 0          # ângulo inicial (em graus) ao longo da circunferência interna
RAMP_ANGLE_END   = 360        # ângulo final: uma volta completa
RAMP_SEGMENTS    = 64         # quantos “pedaços” usar para suavizar a rampa
RAMP_DEPTH       = 1.0        # “espessura” da rampa, radialmente para dentro da parede

RAMP_RADIAL_OUTER = SPHERE_RADIUS - 0.01              # raio externo (colado quase na parede)
RAMP_RADIAL_INNER = RAMP_RADIAL_OUTER - RAMP_DEPTH    # raio interno

# Altura total que a rampa precisa subir
RAMP_HEIGHT = MID_FLOOR_Y - FLOOR_Y


# --------------------------------------
# RAMPAS: DESENHO E COLISÃO
# --------------------------------------

def draw_ramp():
    """
    Desenha uma rampa curvada que segue a parede esférica,
    ligando FLOOR_Y até MID_FLOOR_Y em uma volta completa.
    """
    glColor3fv(STEP_COLOR)
    altura_total = MID_FLOOR_Y - FLOOR_Y
    ang_span = RAMP_ANGLE_END - RAMP_ANGLE_START
    
    for i in range(RAMP_SEGMENTS):
        # ângulos (em graus) dos dois vértices desse “pedaço” de rampa
        a1 = RAMP_ANGLE_START + (i    / RAMP_SEGMENTS) * ang_span
        a2 = RAMP_ANGLE_START + ((i+1)/ RAMP_SEGMENTS) * ang_span
        t1 = a1 * math.pi / 180.0
        t2 = a2 * math.pi / 180.0

        # altura correspondente a cada fragmento (varia linearmente)
        h1 = FLOOR_Y + (i    / RAMP_SEGMENTS) * altura_total
        h2 = FLOOR_Y + ((i+1)/ RAMP_SEGMENTS) * altura_total

        # calcular as coordenadas externas (coladas na parede)
        x1_ext = RAMP_RADIAL_OUTER * math.sin(t1)
        z1_ext = RAMP_RADIAL_OUTER * math.cos(t1)
        x2_ext = RAMP_RADIAL_OUTER * math.sin(t2)
        z2_ext = RAMP_RADIAL_OUTER * math.cos(t2)

        # coordenadas internas (radialmente para dentro, afastado da parede)
        x1_int = RAMP_RADIAL_INNER * math.sin(t1)
        z1_int = RAMP_RADIAL_INNER * math.cos(t1)
        x2_int = RAMP_RADIAL_INNER * math.sin(t2)
        z2_int = RAMP_RADIAL_INNER * math.cos(t2)

        glBegin(GL_QUADS)
        # superfície inclinada (face superior da rampa)
        glVertex3f(x1_ext, h1, z1_ext)
        glVertex3f(x2_ext, h2, z2_ext)
        glVertex3f(x2_int, h2, z2_int)
        glVertex3f(x1_int, h1, z1_int)
        glEnd()


def handle_ramp_collision():
    """
    Ajusta a altura da câmera ao caminhar pela rampa curva.
    Retorna True se a câmera estiver dentro do arco da rampa e ajustar Y; senão False.
    """
    global on_ground
    cam_x, cam_y, cam_z = camera_pos

    # descobre o ângulo (em graus) da posição da câmera no plano XZ
    ang_cam = (math.degrees(math.atan2(cam_x, cam_z)) + 360) % 360

    # define faixa de ângulos válida para a rampa
    start = RAMP_ANGLE_START % 360
    end   = RAMP_ANGLE_END   % 360
    # se RAMP_ANGLE_END > 360, podemos mapear a lógica modular
    span = RAMP_ANGLE_END - RAMP_ANGLE_START

    # calcular “quanto” (fração) da rampa já foi percorrido a partir de RAMP_ANGLE_START
    frac = (ang_cam - RAMP_ANGLE_START) / span

    # normalizar frac entre 0 e 1
    if frac < 0:
        frac += math.ceil(abs(frac))
    if not (0 <= frac <= 1):
        return False

    # distância radial da câmera ao centro
    dist_radial = math.sqrt(cam_x*cam_x + cam_z*cam_z)

    # calcule também um limite permissivo de largura (entre RAMP_RADIAL_INNER−ε a RAMP_RADIAL_OUTER+ε)
    if (RAMP_RADIAL_INNER - 0.3) <= dist_radial <= (RAMP_RADIAL_OUTER + 0.3):
        # altura alvo
        target_y = FLOOR_Y + frac * RAMP_HEIGHT + 0.2
        if cam_y <= target_y + 0.1:
            camera_pos[1] = target_y
            on_ground = True
            return True

    return False

# --------------------------------------
# PARÂMETROS DA ESCADA SUPERIOR (intermediário→teto)
# --------------------------------------

NUM_STEPS_UP        = 2
UP_HEIGHT           = TOP_PASSAGE_Y - MID_FLOOR_Y
UP_STEP_HEIGHT      = UP_HEIGHT / NUM_STEPS_UP
UP_STEP_RADIAL      = SPHERE_RADIUS - 0.01
UP_STEP_ANGLE_INC   = 360.0 / NUM_STEPS_UP
UP_STEP_WIDTH       = 3.0
UP_STEP_DEPTH       = 1.0

# Pré-cálculo dos “degraus” apenas para a escada superior
stairs_info_upper = []
for i in range(NUM_STEPS_UP):
    angle = i * UP_STEP_ANGLE_INC
    height = MID_FLOOR_Y + UP_STEP_HEIGHT * (i + 1)
    stairs_info_upper.append((angle, height))

# --------------------------------------
# PARÂMETROS DO ALÇAPÃO E HATCH
# --------------------------------------

HATCH_RADIUS        = 1.0
UPPER_HATCH_RADIUS  = 2.0

# --------------------------------------
# PARÂMETROS DE MOVIMENTO
# --------------------------------------

GRAVITY       = 9.8
JUMP_SPEED    = 5.0
camera_vel_y  = 0.0
on_ground     = False  # indica se pode pular

# Câmera
camera_pos         = [0.0, FLOOR_Y + 0.2, -2.0]
camera_rot         = [0.0, 0.0]
mouse_sensitivity  = 0.2
move_speed         = 0.1

# --------------------------------------
# CONFIGURAÇÃO OPENGL
# --------------------------------------

glEnable(GL_DEPTH_TEST)
glEnable(GL_LIGHTING)
glEnable(GL_LIGHT0)
glEnable(GL_COLOR_MATERIAL)
glShadeModel(GL_SMOOTH)

glLightfv(GL_LIGHT0, GL_POSITION, (0.0, 5.0, -5.0, 1.0))
glLightfv(GL_LIGHT0, GL_DIFFUSE,  (1.0, 1.0, 1.0, 1.0))
glLightfv(GL_LIGHT0, GL_AMBIENT,  (0.2, 0.2, 0.2, 1.0))

glMatrixMode(GL_PROJECTION)
gluPerspective(60, (display[0] / display[1]), 0.1, 100.0)
glMatrixMode(GL_MODELVIEW)

pygame.event.set_grab(True)
pygame.mouse.set_visible(False)

# --------------------------------------
# FUNÇÕES DE DESENHO
# --------------------------------------

def draw_colored_inner_sphere(radius):
    """
    Esfera interna com cores diferentes por andar.
    """
    slices = 64
    stacks = 64
    quad = gluNewQuadric()
    glPushMatrix()
    glScalef(-1.0, 1.0, 1.0)
    glEnable(GL_POLYGON_OFFSET_FILL)
    glPolygonOffset(1.0, 1.0)

    for i in range(stacks):
        lat0 = math.pi * (-0.5 + float(i) / stacks)
        lat1 = math.pi * (-0.5 + float(i+1) / stacks)
        y0 = radius * math.sin(lat0)
        y1 = radius * math.sin(lat1)

        if y0 < FLOOR_Y:
            glColor3fv(BOTTOM_COLOR)
        elif y0 < MID_FLOOR_Y:
            glColor3fv(MIDDLE_COLOR)
        else:
            glColor3fv(TOP_COLOR)

        glBegin(GL_QUAD_STRIP)
        for j in range(slices+1):
            lng = 2 * math.pi * float(j) / slices
            x = math.cos(lng)
            z = math.sin(lng)
            glVertex3f(radius * x * math.cos(lat0), y0, radius * z * math.cos(lat0))
            glVertex3f(radius * x * math.cos(lat1), y1, radius * z * math.cos(lat1))
        glEnd()

    glDisable(GL_POLYGON_OFFSET_FILL)
    glPopMatrix()
    gluDeleteQuadric(quad)


def draw_floor(y_level, color, hole_radius=0.0):
    """
    Desenha um piso (disco) no nível y_level com cor.
    Se hole_radius > 0, cria abertura circular no centro.
    """
    quad = gluNewQuadric()
    glPushMatrix()
    glTranslatef(0.0, y_level, 0.0)
    glRotatef(-90, 1, 0, 0)
    glColor3fv(color)
    if hole_radius > 0.0:
        gluDisk(quad, hole_radius, SPHERE_RADIUS * 0.95, 64, 1)
    else:
        gluDisk(quad, 0.0, SPHERE_RADIUS * 0.95, 64, 1)
    glPopMatrix()
    gluDeleteQuadric(quad)


def draw_spiral_stairs_upper():
    """Escada superior: intermediário→teto."""
    glColor3fv(STEP_COLOR)
    for angle, height in stairs_info_upper:
        theta = math.radians(angle)
        x_wall = UP_STEP_RADIAL * math.sin(theta)
        z_wall = UP_STEP_RADIAL * math.cos(theta)
        x_in = (UP_STEP_RADIAL - UP_STEP_DEPTH) * math.sin(theta)
        z_in = (UP_STEP_RADIAL - UP_STEP_DEPTH) * math.cos(theta)
        dx = UP_STEP_WIDTH / 2 * math.cos(theta)
        dz = -UP_STEP_WIDTH / 2 * math.sin(theta)
        glBegin(GL_QUADS)
        # Face superior
        glVertex3f(x_wall + dx,      height + 0.005, z_wall + dz)
        glVertex3f(x_wall - dx,      height + 0.005, z_wall - dz)
        glVertex3f(x_in  - dx,       height + 0.005, z_in  - dz)
        glVertex3f(x_in  + dx,       height + 0.005, z_in  + dz)
        # Face inferior
        glVertex3f(x_wall + dx,      height, z_wall + dz)
        glVertex3f(x_wall - dx,      height, z_wall - dz)
        glVertex3f(x_in  - dx,       height, z_in  - dz)
        glVertex3f(x_in  + dx,       height, z_in  + dz)
        # Face externa
        glVertex3f(x_wall + dx,      height,      z_wall + dz)
        glVertex3f(x_wall - dx,      height,      z_wall - dz)
        glVertex3f(x_wall - dx,      height + 0.005, z_wall - dz)
        glVertex3f(x_wall + dx,      height + 0.005, z_wall + dz)
        # Face interna
        glVertex3f(x_in + dx,        height,      z_in + dz)
        glVertex3f(x_in - dx,        height,      z_in - dz)
        glVertex3f(x_in - dx,        height + 0.005, z_in - dz)
        glVertex3f(x_in + dx,        height + 0.005, z_in + dz)
        glEnd()


def draw_hobbit_door(radius=HOBBIT_WINDOW_RADIUS, y_offset=0.0, angle_deg=0):
    """
    Desenha uma porta redonda estilo Hobbit na parede da esfera.
    """
    glPushMatrix()
    theta = math.radians(angle_deg)
    x = SPHERE_RADIUS * math.sin(theta)
    z = SPHERE_RADIUS * math.cos(theta)
    y = y_offset
    glTranslatef(x, y, z)
    glRotatef(-angle_deg, 0, 1, 0)
    glRotatef(90, 1, 0, 0)
    glColor3fv(FRAME_GRAY)
    quad = gluNewQuadric()
    gluDisk(quad, 0.0, radius, 64, 1)
    gluDeleteQuadric(quad)
    glPopMatrix()


def draw_skylight(y_level, outer_radius, inner_radius, color):
    """
    Desenha uma claraboia circular aberta no teto da casa esférica.
    """
    quad = gluNewQuadric()
    glPushMatrix()
    glTranslatef(0.0, y_level, 0.0)
    glRotatef(-90, 1, 0, 0)
    glColor3fv(color)
    gluDisk(quad, inner_radius, outer_radius, 64, 1)
    glPopMatrix()
    gluDeleteQuadric(quad)


# --------------------------------------
# CÂMERA (“FLY CAM”) E COLISÃO
# --------------------------------------

def apply_camera():
    glRotatef(-camera_rot[0], 1, 0, 0)
    glRotatef(-camera_rot[1], 0, 1, 0)
    glTranslatef(-camera_pos[0], -camera_pos[1], -camera_pos[2])


def handle_stair_collision():
    """
    Ajusta altura da câmera: prioriza rampa, depois degraus superiores.
    """
    global on_ground
    cam_x, cam_y, cam_z = camera_pos
    angle = (math.degrees(math.atan2(cam_x, cam_z)) + 360) % 360
    dist_radial = math.sqrt(cam_x**2 + cam_z**2)

    on_ground = False

    # 1) Tenta colisão com a rampa inferior→intermediário
    if handle_ramp_collision():
        return

    # 2) Se não estiver na rampa, checa escada superior (intermediário→teto)
    for step_angle, step_height in stairs_info_upper:
        diff = abs((angle - step_angle + 180) % 360 - 180)
        if diff < (UP_STEP_ANGLE_INC / 2) and abs(dist_radial - (UP_STEP_RADIAL - UP_STEP_DEPTH / 2)) < 0.5:
            target_y = step_height + 0.2
            if cam_y <= target_y + 0.1:
                camera_pos[1] = target_y
                on_ground = True
            return

    # 3) Pisos fixos
    if abs(cam_y - (FLOOR_Y + 0.2)) < 0.1:
        on_ground = True
    if abs(cam_y - (MID_FLOOR_Y + 0.2)) < 0.1:
        on_ground = True


# --------------------------------------
# LOOP PRINCIPAL
# --------------------------------------

clock = pygame.time.Clock()
start_time = time.time()

running = True
while running:
    dt = clock.tick(60) / 60.0
    elapsed = time.time() - start_time

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    # ---------- MOUSE PARA ROTACIONAR VIEW ----------
    dx, dy = pygame.mouse.get_rel()
    camera_rot[1] += dx * mouse_sensitivity
    camera_rot[0] += dy * mouse_sensitivity
    camera_rot[0] = max(-90, min(90, camera_rot[0]))

    # ---------- TECLADO PARA MOVIMENTO HORIZONTAL E SALTO ----------
    keys = pygame.key.get_pressed()
    yaw_rad = math.radians(camera_rot[1])
    forward = (-math.sin(yaw_rad), 0, -math.cos(yaw_rad))
    right   = ( math.cos(yaw_rad), 0, -math.sin(yaw_rad))

    if keys[pygame.K_w] or keys[pygame.K_UP]:
        camera_pos[0] += forward[0] * move_speed
        camera_pos[2] += forward[2] * move_speed
    if keys[pygame.K_s] or keys[pygame.K_DOWN]:
        camera_pos[0] -= forward[0] * move_speed
        camera_pos[2] -= forward[2] * move_speed
    if keys[pygame.K_a] or keys[pygame.K_LEFT]:
        camera_pos[0] -= right[0] * move_speed
        camera_pos[2] -= right[2] * move_speed
    if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
        camera_pos[0] += right[0] * move_speed
        camera_pos[2] += right[2] * move_speed

    # Salto
    if (keys[pygame.K_SPACE] and on_ground):
        camera_vel_y = JUMP_SPEED
        on_ground = False

    # Aplica gravidade
    camera_vel_y -= GRAVITY * dt
    camera_pos[1] += camera_vel_y * dt

    # ---------- COLISÕES COM RAMPA, ESCADA E PISOS ----------
    handle_stair_collision()

    # Piso inferior
    if camera_pos[1] < FLOOR_Y + 0.2:
        camera_pos[1] = FLOOR_Y + 0.2
        camera_vel_y = 0.0
        on_ground = True

    # Piso intermediário
    if MID_FLOOR_Y - 0.1 < camera_pos[1] < SPHERE_RADIUS:
        if camera_pos[1] < MID_FLOOR_Y + 0.2:
            camera_pos[1] = MID_FLOOR_Y + 0.2
            camera_vel_y = 0.0
            on_ground = True

    # ---------- COLISÃO PAREDES ----------
    dist = math.sqrt(camera_pos[0]**2 + camera_pos[1]**2 + camera_pos[2]**2)
    max_dist = SPHERE_RADIUS - 0.2
    if dist > max_dist:
        factor = max_dist / dist
        camera_pos[0] *= factor
        camera_pos[1] *= factor
        camera_pos[2] *= factor

    # ---------- RENDERIZAÇÃO ----------
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    glLoadIdentity()
    apply_camera()

    # 1) Parede interna da esfera
    draw_colored_inner_sphere(SPHERE_RADIUS)

    # 2) Piso inferior com alçapão
    draw_floor(FLOOR_Y, LIGHTER_BLUE, hole_radius=0.0)

    # 3) Piso intermediário com corte circular
    draw_floor(MID_FLOOR_Y, LIGHTER_BLUE, hole_radius=UPPER_HATCH_RADIUS)

    # 4) Claraboia
    draw_skylight(
        y_level=TOP_PASSAGE_Y + 0.01,
        outer_radius=1.5,
        inner_radius=0.5,
        color=LIGHTER_BLUE
    )

    # 5) Rampa lateral (inferior→intermediário)
    if camera_pos[1] < MID_FLOOR_Y - 0.1:
        draw_ramp()

    # 6) Escada superior (intermediário→teto)
    if MID_FLOOR_Y + 0.1 < camera_pos[1] < TOP_PASSAGE_Y - 0.1:
        draw_spiral_stairs_upper()

    # 7) Porta Hobbit
    draw_hobbit_door(radius=2.0, y_offset=MID_FLOOR_Y, angle_deg=0)

    pygame.display.flip()

pygame.quit()
sys.exit()