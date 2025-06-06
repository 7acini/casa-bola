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
ROYAL_BLUE      = (65 / 255.0, 105 / 255.0, 225 / 255.0)
LIGHTER_BLUE    = (100 / 255.0, 149 / 255.0, 237 / 255.0)
FRAME_GRAY      = (0.8, 0.8, 0.8)
BLACK           = (0.0, 0.0, 0.0)
STEP_COLOR      = (0.55, 0.27, 0.07)
LADDER_COLOR    = (0.4, 0.2, 0.1)

# Parâmetros do quarto esférico
SPHERE_RADIUS    = 5.0 # TIBET
FLOOR_Y          = -3.0
MID_FLOOR_Y      = FLOOR_Y + 4.2
TOP_PASSAGE_Y    = SPHERE_RADIUS - 0.1

WINDOW_RADIUS    = 1.5
WINDOW_ANGLES    = [60, 180, 300]
WINDOW_ELEVATION = 0
HOBBIT_WINDOW_RADIUS = 2.0

# Disco ball removida do centro; será substituída por semicírculos de esferas

# Parâmetros da escada em espiral (inferior->intermediário)
NUM_STEPS       = 8
TOTAL_HEIGHT    = MID_FLOOR_Y - FLOOR_Y
STEP_HEIGHT     = TOTAL_HEIGHT / NUM_STEPS
STEP_WIDTH      = 3.0
STEP_DEPTH      = 1.0
STEP_RADIAL     = SPHERE_RADIUS - 0.01
STEP_ANGLE_INC  = 360.0 / NUM_STEPS

# Parâmetros da escada em espiral (intermediário->teto)
NUM_STEPS_UP        = 2
UP_HEIGHT           = TOP_PASSAGE_Y - MID_FLOOR_Y
UP_STEP_HEIGHT      = UP_HEIGHT / NUM_STEPS_UP
UP_STEP_RADIAL      = SPHERE_RADIUS - 0.01
UP_STEP_ANGLE_INC   = 360.0 / NUM_STEPS_UP
UP_STEP_WIDTH       = 3.0
UP_STEP_DEPTH       = 1.0

# Parâmetros do alçapão no piso inferior
HATCH_RADIUS        = 1.0
LADDER_RUNG_SPACING = 0.3
LADDER_RUNG_COUNT   = int(3.0 / LADDER_RUNG_SPACING)

# Parâmetro do corte circular no piso intermediário
UPPER_HATCH_RADIUS = 2.0

# Parâmetro de salto
GRAVITY       = 9.8
JUMP_SPEED    = 5.0
camera_vel_y  = 0.0
on_ground     = False  # indica se posso pular

# Câmera
camera_pos         = [0.0, FLOOR_Y + 0.2, -2.0]
camera_rot         = [0.0, 0.0]
mouse_sensitivity  = 0.2
move_speed         = 0.1

# Configuração OpenGL
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

        # Determinar cor por faixa de altura
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


# Pré-cálculo degraus para colisão e desenho
stairs_info_lower = []
for i in range(NUM_STEPS):
    angle = i * STEP_ANGLE_INC
    height = FLOOR_Y + STEP_HEIGHT * (i + 1)
    stairs_info_lower.append((angle, height))

stairs_info_upper = []
for i in range(NUM_STEPS_UP):
    angle = i * UP_STEP_ANGLE_INC
    height = MID_FLOOR_Y + UP_STEP_HEIGHT * (i + 1)
    stairs_info_upper.append((angle, height))


def draw_spiral_stairs_lower():
    """Escada inferior: piso->segundo andar."""
    glColor3fv(STEP_COLOR)
    for angle, height in stairs_info_lower:
        theta = math.radians(angle)
        x_wall = STEP_RADIAL * math.sin(theta)
        z_wall = STEP_RADIAL * math.cos(theta)
        x_in = (STEP_RADIAL - STEP_DEPTH) * math.sin(theta)
        z_in = (STEP_RADIAL - STEP_DEPTH) * math.cos(theta)
        dx = STEP_WIDTH / 2 * math.cos(theta)
        dz = -STEP_WIDTH / 2 * math.sin(theta)
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
        # Face lateral esquerda
        glVertex3f(x_wall - dx,      height,      z_wall - dz)
        glVertex3f(x_wall - dx,      height + 0.005, z_wall - dz)
        glVertex3f(x_in   - dx,      height + 0.005, z_in   - dz)
        glVertex3f(x_in   - dx,      height,      z_in   - dz)
        # Face lateral direita
        glVertex3f(x_wall + dx,      height,      z_wall + dz)
        glVertex3f(x_wall + dx,      height + 0.005, z_wall + dz)
        glVertex3f(x_in   + dx,      height + 0.005, z_in   + dz)
        glVertex3f(x_in   + dx,      height,      z_in   + dz)
        glEnd()


def draw_spiral_stairs_upper():
    """Escada superior: segundo andar->teto."""
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
        # Face lateral esquerda
        glVertex3f(x_wall - dx,      height,      z_wall - dz)
        glVertex3f(x_wall - dx,      height + 0.005, z_wall - dz)
        glVertex3f(x_in   - dx,      height + 0.005, z_in   - dz)
        glVertex3f(x_in   - dx,      height,      z_in   - dz)
        # Face lateral direita
        glVertex3f(x_wall + dx,      height,      z_wall + dz)
        glVertex3f(x_wall + dx,      height + 0.005, z_wall + dz)
        glVertex3f(x_in   + dx,      height + 0.005, z_in   + dz)
        glVertex3f(x_in   + dx,      height,      z_in   + dz)
        glEnd()


def draw_hobbit_door(radius=HOBBIT_WINDOW_RADIUS, y_offset=0.0, angle_deg=0):
    """
    Desenha um círculo (porta estilo Hobbit) na parede da esfera.
    - radius: raio do círculo.
    - y_offset: altura da porta.
    - angle_deg: ângulo na esfera onde será desenhada.
    """
    glPushMatrix()
    theta = math.radians(angle_deg)
    
    # Posiciona na superfície da esfera
    x = SPHERE_RADIUS * math.sin(theta)
    z = SPHERE_RADIUS * math.cos(theta)
    y = y_offset
    
    glTranslatef(x, y, z)
    glRotatef(-angle_deg, 0, 1, 0)  # Gira o disco para "olhar para o centro"
    glRotatef(90, 1, 0, 0)  # Põe o disco na vertical
    glColor3fv(FRAME_GRAY)
    
    quad = gluNewQuadric()
    gluDisk(quad, 0.0, radius, 64, 1)
    gluDeleteQuadric(quad)
    glPopMatrix()


def draw_skylight(y_level, outer_radius, inner_radius, color):
    """
    Desenha uma claraboia circular aberta no teto da casa esférica.
    y_level: altura vertical da claraboia (ex: perto do topo da esfera)
    outer_radius: raio externo do anel
    inner_radius: raio interno do anel (buraco da claraboia)
    color: cor do anel
    """
    quad = gluNewQuadric()
    glPushMatrix()
    glTranslatef(0.0, y_level, 0.0)  # posiciona no teto
    glRotatef(-90, 1, 0, 0)          # gira para ficar horizontal (XY plane)
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
    Ajusta altura da câmera ao subir pelos degraus em espiral.
    """
    global on_ground
    cam_x, cam_y, cam_z = camera_pos
    angle = (math.degrees(math.atan2(cam_x, cam_z)) + 360) % 360
    dist_radial = math.sqrt(cam_x**2 + cam_z**2)

    on_ground = False

    # Verifica contato com degraus inferiores
    for step_angle, step_height in stairs_info_lower:
        diff = abs((angle - step_angle + 180) % 360 - 180)
        if diff < (STEP_ANGLE_INC / 2) and abs(dist_radial - (STEP_RADIAL - STEP_DEPTH / 2)) < 0.5:
            target_y = step_height + 0.2
            if cam_y <= target_y + 0.1:
                camera_pos[1] = target_y
                on_ground = True
            return

    # Verifica contato com degraus superiores
    for step_angle, step_height in stairs_info_upper:
        diff = abs((angle - step_angle + 180) % 360 - 180)
        if diff < (UP_STEP_ANGLE_INC / 2) and abs(dist_radial - (UP_STEP_RADIAL - UP_STEP_DEPTH / 2)) < 0.5:
            target_y = step_height + 0.2
            if cam_y <= target_y + 0.1:
                camera_pos[1] = target_y
                on_ground = True
            return

    # Verifica contato com piso inferior
    if abs(cam_y - (FLOOR_Y + 0.2)) < 0.1:
        on_ground = True
    # Verifica contato com piso intermediário
    if abs(cam_y - (MID_FLOOR_Y + 0.2)) < 0.1:
        on_ground = True

    # Verifica contato com piso superior
   # if abs(cam_y - (TOP_FLOOR_Y + 0.2)) < 0.1:
    #    on_ground = True


# --------------------------------------
# LOOP PRINCIPAL
# --------------------------------------

clock = pygame.time.Clock()
start_time = time.time()

running = True
while running:
    dt = clock.tick(60) / 60.0  # em segundos
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

    # ---------- COLISÕES COM ESCADAS E PISOS ----------
    handle_stair_collision()
    #handle_hatch_and_basement()

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

    # Desenha a claraboia aberta logo acima do teto
    draw_skylight(
    y_level=TOP_PASSAGE_Y + 0.01,  # pouco acima do teto para evitar z-fighting
    outer_radius=1.5,              # tamanho externo da claraboia
    inner_radius=0.5,              # buraco da claraboia (vazio)
    color=LIGHTER_BLUE             # cor da borda da claraboia
    )

    # 5) Escada em espiral inferior
    if camera_pos[1] < MID_FLOOR_Y - 0.1:
        draw_spiral_stairs_lower()

    # 6) Escada em espiral superior
    if MID_FLOOR_Y + 0.1 < camera_pos[1] < TOP_PASSAGE_Y - 0.1:
        draw_spiral_stairs_upper()

    # Aqui entra a porta hobbit
    draw_hobbit_door(radius=2.0, y_offset=MID_FLOOR_Y, angle_deg=270)


    pygame.display.flip()

pygame.quit()
sys.exit()