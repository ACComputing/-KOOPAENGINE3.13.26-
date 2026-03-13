"""
ULTRA MARIO FOREVER ENGINE v3.0 — SMB1 NES 8-BIT EDITION
All 32 Super Mario Bros. 1 levels (World 1-1 through 8-4)
NES Super Mario Bros. 1 graphic style & 600x400 Resolution
"""

import pygame
import json
import os
import sys
import math
import random
from enum import IntEnum

# ─────────────────────────────────────────
#  CONSTANTS
# ─────────────────────────────────────────
TILE_SIZE = 32
SCREEN_W, SCREEN_H = 600, 400
FPS = 60
# Approximate Super Mario Bros. NES timer speed (~0.4s per in-game second)
SMB_TIMER_TICKS_PER_SECOND = int(FPS * 0.4)
GRAVITY = 0.55
MAX_FALL = 12
JUMP_FORCE = -11
RUN_SPEED = 4.5
SPRINT_SPEED = 7
FRICTION = 0.85
ACCEL = 0.5
GRID_W = SCREEN_W // TILE_SIZE
GRID_H = SCREEN_H // TILE_SIZE

# ─────────────────────────────────────────
#  NES 8-BIT COLOUR PALETTE
# ─────────────────────────────────────────
# Sky / backgrounds
C_SKY          = (104, 136, 252)   # NES classic sky blue
C_UNDERGROUND  = (0,   0,   0)     # NES underground black
C_CASTLE_BG    = (0,   0,   0)     # NES castle black
C_WATER_BG     = (32,  56,  236)   # NES water blue
C_CLOUD_W      = (252, 252, 252)

# Ground / terrain  (Classic NES orange/brown)
C_GROUND_BODY  = (200,  76,  12)
C_GROUND_HI    = (252, 216, 168)
C_GROUND_DARK  = (0,    0,   0)

# Bricks
C_BRICK_FACE   = (200,  76,  12)
C_BRICK_MORT   = (0,    0,   0)
C_BRICK_HI     = (252, 216, 168)

# ? block
C_QBLK_FACE    = (252, 152,  56)
C_QBLK_DARK    = (200,  76,  12)
C_QBLK_BORDER  = (0,    0,   0)
C_QBLK_BLINK   = (252, 216, 168)

# Used block
C_USED_FACE    = (200,  76,  12)
C_USED_DARK    = (0,    0,   0)

# Stone / hard block (NES stair block)
C_STONE_FACE   = (200,  76,  12)
C_STONE_HI     = (252, 216, 168)
C_STONE_SH     = (0,    0,   0)

# Pipe
C_PIPE_BODY    = (0,   168,   0)
C_PIPE_HI      = (184, 248,  24)
C_PIPE_DARK    = (0,    0,   0)

# Coins
C_COIN_BRIGHT  = (252, 216, 168)
C_COIN_MID     = (252, 152,  56)
C_COIN_DARK    = (0,    0,   0)

# Enemies
C_GOOMBA_BODY  = (200,  76,  12)
C_GOOMBA_BELLY = (252, 216, 168)
C_GOOMBA_FEET  = (0,    0,   0)
C_KOOPA_SHELL  = (0,   168,   0)
C_KOOPA_SKIN   = (252, 152,  56)

# Mario NES palette
C_M_RED        = (248,  56,   0)
C_M_BROWN      = (136, 112,   0)
C_M_SKIN       = (252, 152,  56)

# Misc
C_WHITE  = (252, 252, 252)
C_BLACK  = (0,   0,   0)
C_GOLD   = (252, 152, 56)
C_YELLOW = (252, 216, 168)
C_GRAY   = (188, 188, 188)
C_DKGRAY = (80,  80,  80)
C_GREEN  = (0,   168, 0)
C_DKGREEN= (0,   88,  0)
C_RED    = (248, 56,  0)

# ─────────────────────────────────────────
#  ENUMS & CONFIG
# ─────────────────────────────────────────
class TileType(IntEnum):
    EMPTY=0; GROUND=1; BRICK=2; QUESTION=3; HARD_BLOCK=4
    PIPE_TL=5; PIPE_TR=6; PIPE_BL=7; PIPE_BR=8
    COIN=9; GOOMBA_SPAWN=10; KOOPA_SPAWN=11; PLAYER_SPAWN=12
    GOAL_POLE=13; CLOUD=14; BUSH=15; HILL=16; USED_BLOCK=17
    MUSHROOM_SPAWN=18; SPIKE=19
    SLOPE_R=20; SLOPE_L=21; SLOPE_R2=22; SLOPE_L2=23
    LAVA=24; BRIDGE=25; WATER_TILE=26; PLATFORM=27

TILE_NAMES = {v: k for k, v in TileType.__members__.items()}

SOLID_TILES   = {TileType.GROUND, TileType.BRICK, TileType.QUESTION,
                 TileType.HARD_BLOCK, TileType.USED_BLOCK,
                 TileType.BRIDGE, TileType.PLATFORM}
PIPE_TOP_TILES  = {TileType.PIPE_TL, TileType.PIPE_TR}
PIPE_BODY_TILES = {TileType.PIPE_BL, TileType.PIPE_BR}
ALL_PIPE_TILES  = PIPE_TOP_TILES | PIPE_BODY_TILES
ALL_SOLID_TILES = SOLID_TILES | ALL_PIPE_TILES
SLOPE_TILES     = {TileType.SLOPE_R, TileType.SLOPE_L, TileType.SLOPE_R2, TileType.SLOPE_L2}
BG_TILES        = {TileType.CLOUD, TileType.BUSH, TileType.HILL}
PIPE_BODY_INSET = 2

# ─────────────────────────────────────────
#  HELPERS
# ─────────────────────────────────────────
def slope_surface_y(tile_type, gx, gy, world_x):
    tile_px = gx * TILE_SIZE
    local_x = max(0, min(TILE_SIZE - 1, world_x - tile_px))
    t = local_x / TILE_SIZE
    if   tile_type == TileType.SLOPE_R:  height = t * TILE_SIZE
    elif tile_type == TileType.SLOPE_L:  height = (1.0 - t) * TILE_SIZE
    elif tile_type == TileType.SLOPE_R2: height = t * TILE_SIZE * 0.5
    elif tile_type == TileType.SLOPE_L2: height = (1.0 - t) * TILE_SIZE * 0.5
    else: height = 0
    return gy * TILE_SIZE + TILE_SIZE - int(height)

def get_tile_rect(tile_type, gx, gy):
    px, py = gx * TILE_SIZE, gy * TILE_SIZE
    if tile_type in PIPE_BODY_TILES:
        return pygame.Rect(px + PIPE_BODY_INSET, py, TILE_SIZE - PIPE_BODY_INSET * 2, TILE_SIZE)
    return pygame.Rect(px, py, TILE_SIZE, TILE_SIZE)

def resolve_slope_y(level, world_x, foot_y, entity_h):
    best_y = None
    for probe_y in [foot_y - 2, foot_y, foot_y + 4]:
        gx = world_x // TILE_SIZE
        gy = probe_y // TILE_SIZE
        tile = level.get(gx, gy)
        if tile in SLOPE_TILES:
            surf_y = slope_surface_y(tile, gx, gy, world_x)
            if foot_y >= surf_y - 2:
                new_y = surf_y - entity_h
                if best_y is None or new_y < best_y: best_y = new_y
    return best_y

def collide_solid_x(entity_rect, vx, level):
    rect = entity_rect.copy(); hit = False
    top_gy   = max(0, rect.top // TILE_SIZE)
    bot_gy   = min(level.height - 1, rect.bottom // TILE_SIZE)
    left_gx  = max(0, (rect.left - TILE_SIZE) // TILE_SIZE)
    right_gx = min(level.width - 1, (rect.right + TILE_SIZE) // TILE_SIZE)
    for gy in range(top_gy, bot_gy + 1):
        for gx in range(left_gx, right_gx + 1):
            tile = level.get(gx, gy)
            if tile in ALL_SOLID_TILES:
                tr = get_tile_rect(tile, gx, gy)
                if rect.colliderect(tr):
                    if vx > 0: rect.right = tr.left
                    elif vx < 0: rect.left = tr.right
                    hit = True
    return rect.x, hit

def collide_solid_y(entity_rect, vy, level):
    rect = entity_rect.copy(); on_ground = False; hit_info = None
    top_gy   = max(0, (rect.top - TILE_SIZE) // TILE_SIZE)
    bot_gy   = min(level.height - 1, (rect.bottom + TILE_SIZE) // TILE_SIZE)
    left_gx  = max(0, rect.left // TILE_SIZE)
    right_gx = min(level.width - 1, rect.right // TILE_SIZE)
    for gy in range(top_gy, bot_gy + 1):
        for gx in range(left_gx, right_gx + 1):
            tile = level.get(gx, gy)
            if tile in ALL_SOLID_TILES:
                tr = get_tile_rect(tile, gx, gy)
                if rect.colliderect(tr):
                    if vy > 0: rect.bottom = tr.top; vy = 0; on_ground = True
                    elif vy < 0: rect.top = tr.bottom; vy = 0; hit_info = (gx, gy, tile)
    return rect.y, vy, on_ground, hit_info

# ─────────────────────────────────────────
#  NES DRAWING FUNCTIONS (Blocky & Flat)
# ─────────────────────────────────────────
def draw_tile(surface, tile_type, x, y, anim_frame=0, underground=False):
    s = TILE_SIZE
    r = pygame.Rect(x, y, s, s)

    if tile_type == TileType.GROUND:
        # NES Ground: Base brown with peach highlights and black shadows
        base = C_PIPE_BODY if underground else C_GROUND_BODY
        hi   = C_PIPE_HI   if underground else C_GROUND_HI
        pygame.draw.rect(surface, base, r)
        pygame.draw.rect(surface, C_BLACK, r, 2)
        pygame.draw.line(surface, hi, (x+2, y+2), (x+s-4, y+2), 2)
        pygame.draw.line(surface, hi, (x+2, y+2), (x+2, y+s-4), 2)
        # Pixel cracks
        pygame.draw.rect(surface, C_BLACK, (x+s//2, y+4, 2, 8))
        pygame.draw.rect(surface, C_BLACK, (x+4, y+s-10, 8, 2))

    elif tile_type == TileType.BRICK:
        base = C_PIPE_BODY if underground else C_BRICK_FACE
        hi   = C_PIPE_HI   if underground else C_BRICK_HI
        pygame.draw.rect(surface, base, r)
        pygame.draw.rect(surface, C_BLACK, r, 2)
        # NES mortar
        for row in range(4):
            yy = y + row * 8
            pygame.draw.line(surface, C_BLACK, (x, yy), (x+s, yy), 2)
            offset = 0 if row % 2 == 0 else 16
            for col_x in range(offset, s, 16):
                pygame.draw.line(surface, C_BLACK, (x+col_x, yy), (x+col_x, yy+8), 2)
            # Highlights
            offset2 = 2 if row % 2 == 0 else 18
            for col_x in range(offset2, s-4, 16):
                pygame.draw.rect(surface, hi, (x+col_x, yy+2, 4, 2))

    elif tile_type == TileType.QUESTION:
        flash = anim_frame % 30 < 15
        bg = C_QBLK_FACE if not underground else C_DKGRAY
        pygame.draw.rect(surface, bg, r)
        pygame.draw.rect(surface, C_BLACK, r, 2)
        pygame.draw.rect(surface, C_QBLK_DARK, (x+s-4, y+4, 2, s-8))
        pygame.draw.rect(surface, C_QBLK_DARK, (x+4, y+s-4, s-8, 2))
        # 4 corners
        for cx, cy in [(x+4,y+4), (x+s-6,y+4), (x+4,y+s-6), (x+s-6,y+s-6)]:
            pygame.draw.rect(surface, C_BLACK, (cx, cy, 2, 2))
        # Question mark
        q_color = C_QBLK_BLINK if flash else C_BRICK_FACE
        qx, qy = x + 10, y + 6
        pygame.draw.rect(surface, q_color, (qx+2, qy, 8, 4))
        pygame.draw.rect(surface, q_color, (qx-2, qy+4, 4, 4))
        pygame.draw.rect(surface, q_color, (qx+6, qy+4, 4, 6))
        pygame.draw.rect(surface, q_color, (qx+2, qy+10, 4, 4))
        pygame.draw.rect(surface, q_color, (qx+2, qy+16, 4, 4))

    elif tile_type == TileType.USED_BLOCK:
        bg = C_USED_FACE if not underground else C_DKGRAY
        pygame.draw.rect(surface, bg, r)
        pygame.draw.rect(surface, C_BLACK, r, 2)
        # 4 corners
        for cx, cy in [(x+4,y+4), (x+s-6,y+4), (x+4,y+s-6), (x+s-6,y+s-6)]:
            pygame.draw.rect(surface, C_BLACK, (cx, cy, 2, 2))

    elif tile_type == TileType.HARD_BLOCK:
        base = C_PIPE_BODY if underground else C_STONE_FACE
        hi   = C_PIPE_HI   if underground else C_STONE_HI
        pygame.draw.rect(surface, base, r)
        pygame.draw.rect(surface, C_BLACK, r, 2)
        pygame.draw.line(surface, hi, (x+2, y+2), (x+s-4, y+2), 2)
        pygame.draw.line(surface, hi, (x+2, y+2), (x+2, y+s-4), 2)
        pygame.draw.line(surface, C_BLACK, (x+2, y+s-4), (x+s-4, y+s-4), 2)
        pygame.draw.line(surface, C_BLACK, (x+s-4, y+2), (x+s-4, y+s-4), 2)

    elif tile_type in PIPE_TOP_TILES:
        pygame.draw.rect(surface, C_PIPE_BODY, r)
        pygame.draw.rect(surface, C_BLACK, r, 2)
        pygame.draw.rect(surface, C_PIPE_HI, (x+4, y+2, 6, s-4))
        pygame.draw.rect(surface, C_DKGREEN, (x+s-8, y+2, 6, s-4))

    elif tile_type in PIPE_BODY_TILES:
        inset = PIPE_BODY_INSET
        inner = pygame.Rect(x+inset, y, s-inset*2, s)
        pygame.draw.rect(surface, C_PIPE_BODY, inner)
        pygame.draw.rect(surface, C_BLACK, (inner.x, inner.y, inner.w, inner.h), 2)
        pygame.draw.rect(surface, C_PIPE_HI, (x+inset+4, y, 6, s))
        pygame.draw.rect(surface, C_DKGREEN, (x+s-inset-8, y, 6, s))

    elif tile_type == TileType.COIN:
        cx, cy = x + s//2, y + s//2
        wobble = int(math.sin(anim_frame * 0.15) * 4)
        hw = max(2, 6 - abs(wobble))
        pygame.draw.rect(surface, C_BLACK, (cx-hw-2, cy-10, hw*2+4, 20))
        pygame.draw.rect(surface, C_COIN_MID, (cx-hw, cy-8, hw*2, 16))
        pygame.draw.rect(surface, C_COIN_BRIGHT, (cx-hw+2, cy-6, max(2,hw*2-4), 12))

    elif tile_type == TileType.BRIDGE:
        pygame.draw.rect(surface, C_M_RED, (x, y+8, s, 8))
        pygame.draw.rect(surface, C_BLACK, (x, y+8, s, 8), 2)
        pygame.draw.line(surface, C_WHITE, (x+2, y+10), (x+s-4, y+10), 2)

    elif tile_type == TileType.WATER_TILE:
        wave = int(math.sin(anim_frame * 0.1 + x * 0.02) * 2)
        pygame.draw.rect(surface, C_WATER_BG, r)
        pygame.draw.rect(surface, C_WHITE, (x, y+wave, s, 2))

    elif tile_type == TileType.LAVA:
        flash = anim_frame % 20 < 10
        top_c = C_WHITE if flash else C_RED
        pygame.draw.rect(surface, C_RED, r)
        pygame.draw.rect(surface, top_c, (x, y+4, s, 4))
        pygame.draw.rect(surface, C_BLACK, (x, y+8, s, 2))

    elif tile_type == TileType.PLATFORM:
        pygame.draw.rect(surface, C_YELLOW, (x, y, s, 8))
        pygame.draw.rect(surface, C_BLACK, (x, y, s, 8), 2)

    elif tile_type == TileType.CLOUD:
        pygame.draw.rect(surface, C_WHITE, (x, y+16, s, 16), border_radius=8)
        pygame.draw.rect(surface, C_BLACK, (x, y+16, s, 16), 2, border_radius=8)
        pygame.draw.rect(surface, C_WHITE, (x+8, y+8, s-16, 16), border_radius=8)
        pygame.draw.rect(surface, C_BLACK, (x+8, y+8, s-16, 16), 2, border_radius=8)

    elif tile_type == TileType.BUSH:
        pygame.draw.rect(surface, C_GREEN, (x, y+16, s, 16), border_radius=8)
        pygame.draw.rect(surface, C_BLACK, (x, y+16, s, 16), 2, border_radius=8)
        pygame.draw.rect(surface, C_GREEN, (x+8, y+8, s-16, 16), border_radius=8)
        pygame.draw.rect(surface, C_BLACK, (x+8, y+8, s-16, 16), 2, border_radius=8)
        
    elif tile_type == TileType.HILL:
        pts = [(x, y+s), (x+s//2, y+4), (x+s, y+s)]
        pygame.draw.polygon(surface, C_GREEN, pts)
        pygame.draw.polygon(surface, C_BLACK, pts, 2)

    elif tile_type == TileType.MUSHROOM_SPAWN:
        cx, cy = x+s//2, y+s-2
        pygame.draw.rect(surface, C_BLACK, (cx-10, cy-22, 20, 22))
        pygame.draw.rect(surface, C_M_RED, (cx-8, cy-20, 16, 10))
        pygame.draw.rect(surface, C_M_SKIN, (cx-6, cy-10, 12, 8))
        pygame.draw.rect(surface, C_WHITE, (cx-4, cy-18, 4, 4))
        pygame.draw.rect(surface, C_WHITE, (cx+2, cy-18, 4, 4))

    elif tile_type == TileType.GOOMBA_SPAWN:
        _draw_goomba(surface, x, y, 0)

    elif tile_type == TileType.KOOPA_SPAWN:
        _draw_koopa(surface, x, y, 0)

    elif tile_type == TileType.GOAL_POLE:
        # Editor / simple view: single-tile pole top
        pygame.draw.rect(surface, C_BLACK, (x+s//2-2, y, 4, s))
        pygame.draw.rect(surface, C_GREEN, (x+s//2-4, y+4, 8, 8))

    elif tile_type == TileType.SPIKE:
        pts = [(x+4, y+s), (x+s//2, y+4), (x+s-4, y+s)]
        pygame.draw.polygon(surface, C_GRAY, pts)
        pygame.draw.polygon(surface, C_BLACK, pts, 2)

    elif tile_type == TileType.SLOPE_R:
        pts = [(x, y+s), (x+s, y), (x+s, y+s)]
        pygame.draw.polygon(surface, C_GROUND_BODY, pts)
        pygame.draw.line(surface, C_BLACK, (x, y+s), (x+s, y), 2)

    elif tile_type == TileType.SLOPE_L:
        pts = [(x, y), (x+s, y+s), (x, y+s)]
        pygame.draw.polygon(surface, C_GROUND_BODY, pts)
        pygame.draw.line(surface, C_BLACK, (x, y), (x+s, y+s), 2)


def _draw_goomba(surface, x, y, anim_frame):
    s = TILE_SIZE
    cx, cy = x + s//2, y + s - 2
    walk = -2 if anim_frame % 16 < 8 else 2
    # Body/Head
    pygame.draw.rect(surface, C_BLACK, (cx-10, cy-16, 20, 16))
    pygame.draw.rect(surface, C_GOOMBA_BODY, (cx-8, cy-14, 16, 12))
    # Underbelly
    pygame.draw.rect(surface, C_GOOMBA_BELLY, (cx-6, cy-6, 12, 4))
    # Feet
    pygame.draw.rect(surface, C_GOOMBA_FEET, (cx-10+walk, cy, 8, 2))
    pygame.draw.rect(surface, C_GOOMBA_FEET, (cx+2+walk, cy, 8, 2))
    # Eyes
    pygame.draw.rect(surface, C_BLACK, (cx-6, cy-12, 4, 4))
    pygame.draw.rect(surface, C_BLACK, (cx+2, cy-12, 4, 4))

def _draw_koopa(surface, x, y, anim_frame):
    s = TILE_SIZE
    cx, cy = x + s//2, y + s - 2
    walk = -2 if anim_frame % 16 < 8 else 2
    pygame.draw.rect(surface, C_BLACK, (cx-10, cy-24, 20, 24))
    # Shell
    pygame.draw.rect(surface, C_KOOPA_SHELL, (cx-8, cy-20, 14, 16))
    # Skin/Head
    pygame.draw.rect(surface, C_KOOPA_SKIN, (cx, cy-22, 10, 8))
    # Feet
    pygame.draw.rect(surface, C_KOOPA_SHELL, (cx-10+walk, cy-2, 8, 2))
    pygame.draw.rect(surface, C_KOOPA_SHELL, (cx+2+walk, cy-2, 8, 2))
    # Eye
    pygame.draw.rect(surface, C_BLACK, (cx+4, cy-20, 2, 4))

def draw_mario(surface, sx, sy, facing, big, dead, run_frame=0):
    """NES 8-bit blocky Mario style."""
    s = TILE_SIZE
    cx = sx + s // 2

    if dead:
        pygame.draw.rect(surface, C_BLACK, (cx-8, sy+14, 16, 16))
        pygame.draw.rect(surface, C_M_SKIN, (cx-6, sy+16, 12, 12))
        pygame.draw.rect(surface, C_M_RED, (cx-8, sy+28, 16, 4))
        return

    # Flip X logic
    if facing < 0:
        dir_mod = -1
    else:
        dir_mod = 1
        
    walk = int(math.sin(run_frame*0.4)*2) if facing != 0 else 0

    if big:
        # NES Big Mario (16x32 simplified)
        # Outline
        pygame.draw.rect(surface, C_BLACK, (cx-10, sy, 20, 32))
        # Hat
        hat_r = (cx-8 if dir_mod>0 else cx-4, sy+2, 12, 4)
        pygame.draw.rect(surface, C_M_RED, hat_r)
        # Face
        face_r = (cx-8 if dir_mod>0 else cx-6, sy+6, 14, 8)
        pygame.draw.rect(surface, C_M_SKIN, face_r)
        # Eye/Moustache
        pygame.draw.rect(surface, C_BLACK, (cx+(2*dir_mod), sy+8, 2, 4))
        pygame.draw.rect(surface, C_BLACK, (cx+(4*dir_mod), sy+12, 4, 2))
        # Shirt (Brown)
        pygame.draw.rect(surface, C_M_BROWN, (cx-8, sy+14, 16, 10))
        # Overalls (Red)
        pygame.draw.rect(surface, C_M_RED, (cx-6, sy+16, 12, 12))
        pygame.draw.rect(surface, C_M_RED, (cx-4, sy+12, 8, 4)) # Suspenders
        # Boots (Brown)
        pygame.draw.rect(surface, C_M_BROWN, (cx-10+walk, sy+28, 8, 4))
        pygame.draw.rect(surface, C_M_BROWN, (cx+2-walk, sy+28, 8, 4))
    else:
        # NES Small Mario (16x16 simplified)
        # Outline
        pygame.draw.rect(surface, C_BLACK, (cx-8, sy+14, 16, 16))
        # Hat
        hat_r = (cx-7 if dir_mod>0 else cx-5, sy+16, 12, 4)
        pygame.draw.rect(surface, C_M_RED, hat_r)
        # Face
        face_r = (cx-7 if dir_mod>0 else cx-5, sy+20, 12, 4)
        pygame.draw.rect(surface, C_M_SKIN, face_r)
        pygame.draw.rect(surface, C_BLACK, (cx+(2*dir_mod), sy+20, 2, 2))
        # Shirt (Brown)
        pygame.draw.rect(surface, C_M_BROWN, (cx-7, sy+24, 14, 4))
        # Overalls (Red)
        pygame.draw.rect(surface, C_M_RED, (cx-5, sy+24, 10, 4))
        # Boots (Brown)
        pygame.draw.rect(surface, C_M_BROWN, (cx-8+walk, sy+28, 6, 2))
        pygame.draw.rect(surface, C_M_BROWN, (cx+2-walk, sy+28, 6, 2))


# ─────────────────────────────────────────
#  LEVEL CLASS
# ─────────────────────────────────────────
class Level:
    def __init__(self, width=200, height=19):
        self.width = width; self.height = height
        self.tiles = [[0]*width for _ in range(height)]
        self.bg_color = C_SKY
        self.name = "Untitled"
        self.time_limit = 400
        self.theme = "overworld"

    def get(self, gx, gy):
        if 0 <= gx < self.width and 0 <= gy < self.height: return self.tiles[gy][gx]
        return 0

    def set(self, gx, gy, val):
        if 0 <= gx < self.width and 0 <= gy < self.height: self.tiles[gy][gx] = int(val)

    def find_spawn(self):
        for gy in range(self.height):
            for gx in range(self.width):
                if self.tiles[gy][gx] == TileType.PLAYER_SPAWN:
                    return gx * TILE_SIZE, (gy + 1) * TILE_SIZE - 32
        return 3 * TILE_SIZE, 14 * TILE_SIZE

    def to_dict(self):
        return {"name":self.name,"width":self.width,"height":self.height,
                "tiles":self.tiles,"bg_color":list(self.bg_color),
                "time_limit":self.time_limit,"theme":self.theme}

    @staticmethod
    def from_dict(d):
        lv = Level(d["width"],d["height"])
        lv.tiles = d["tiles"]; lv.bg_color = tuple(d.get("bg_color",C_SKY))
        lv.name = d.get("name","Untitled"); lv.time_limit = d.get("time_limit",400)
        lv.theme = d.get("theme","overworld"); return lv

    def save(self, filepath):
        os.makedirs(os.path.dirname(filepath), exist_ok=True) if os.path.dirname(filepath) else None
        with open(filepath,'w') as f: json.dump(self.to_dict(),f)

    @staticmethod
    def load(filepath):
        with open(filepath,'r') as f: return Level.from_dict(json.load(f))


# ─────────────────────────────────────────
#  ENTITIES
# ─────────────────────────────────────────
class Player:
    def __init__(self, x, y):
        self.x, self.y = float(x), float(y)
        self.vx, self.vy = 0.0, 0.0
        self.w, self.h = 24, 30
        self.on_ground = False; self.on_slope = False
        self.facing = 1; self.alive = True; self.big = False
        self.coins = 0; self.score = 0; self.lives = 3; self.won = False
        self.anim_frame = 0; self.invincible = 0; self.run_frame = 0

    @property
    def rect(self): return pygame.Rect(int(self.x), int(self.y), self.w, self.h)

    def update(self, keys, level):
        if not self.alive:
            self.vy += GRAVITY; self.y += self.vy; return

        ax = 0
        speed = SPRINT_SPEED if (keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT]) else RUN_SPEED
        moving = False
        if keys[pygame.K_LEFT]  or keys[pygame.K_a]: ax = -ACCEL; self.facing = -1; moving=True
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]: ax =  ACCEL; self.facing =  1; moving=True
        self.vx += ax; self.vx *= FRICTION
        self.vx = max(-speed, min(speed, self.vx))
        if abs(self.vx) < 0.1: self.vx = 0
        if moving: self.run_frame += 1
        else: self.run_frame = 0

        self.x += self.vx
        new_x, hit = collide_solid_x(self.rect, self.vx, level)
        if hit: self.x = float(new_x); self.vx = 0

        if (keys[pygame.K_UP] or keys[pygame.K_w] or keys[pygame.K_SPACE]) and self.on_ground:
            self.vy = JUMP_FORCE; self.on_ground = False; self.on_slope = False

        self.vy += GRAVITY
        if self.vy > MAX_FALL: self.vy = MAX_FALL
        was_on_ground = self.on_ground
        self.y += self.vy
        new_y, new_vy, on_ground, hit_info = collide_solid_y(self.rect, self.vy, level)
        self.y = float(new_y); self.vy = new_vy; self.on_ground = on_ground; self.on_slope = False

        if hit_info:
            gx, gy, tile = hit_info
            if tile == TileType.QUESTION:
                level.set(gx, gy, TileType.USED_BLOCK); self.coins += 1; self.score += 200
            elif tile == TileType.BRICK and self.big:
                level.set(gx, gy, TileType.EMPTY); self.score += 50

        foot_y = int(self.y) + self.h
        best_slope_y = None
        for px in [int(self.x)+4, int(self.x)+self.w//2, int(self.x)+self.w-4]:
            sy = resolve_slope_y(level, px, foot_y, self.h)
            if sy is not None:
                if best_slope_y is None or sy < best_slope_y: best_slope_y = sy

        if best_slope_y is not None and self.vy >= 0:
            if best_slope_y <= self.y + 2:
                self.y = float(best_slope_y); self.vy = 0; self.on_ground = True; self.on_slope = True

        if was_on_ground and not self.on_ground and not self.on_slope and self.vy >= 0 and self.vy < 4:
            foot_y = int(self.y) + self.h
            for px in [int(self.x)+4, int(self.x)+self.w//2, int(self.x)+self.w-4]:
                for extra in range(1, 10):
                    sy = resolve_slope_y(level, px, foot_y+extra, self.h)
                    if sy is not None:
                        self.y = float(sy); self.vy = 0; self.on_ground = True; self.on_slope = True; break
                if self.on_slope: break

        if self.x < 0: self.x = 0; self.vx = 0
        if self.y > level.height * TILE_SIZE + 100: self.die()
        self.anim_frame += 1
        if self.invincible > 0: self.invincible -= 1

    def die(self):
        if self.invincible > 0: return
        if self.big: self.big = False; self.invincible = 90; self.h = 30; return
        self.alive = False; self.vy = JUMP_FORCE; self.lives -= 1

    def draw(self, surface, cam_x, cam_y):
        sx = int(self.x - cam_x); sy = int(self.y - cam_y)
        if not self.alive: draw_mario(surface, sx, sy, self.facing, False, True); return
        if self.invincible > 0 and self.anim_frame % 6 < 3: return
        draw_mario(surface, sx, sy, self.facing, self.big, False, self.run_frame)


class Enemy:
    def __init__(self, x, y, etype="goomba"):
        self.x, self.y = float(x), float(y)
        self.vx = -1.5; self.vy = 0.0
        self.w, self.h = 28, 28
        self.alive = True; self.etype = etype
        self.squish_timer = 0; self.anim_frame = 0

    @property
    def rect(self): return pygame.Rect(int(self.x), int(self.y), self.w, self.h)

    def update(self, level, cam_x):
        if not self.alive: self.squish_timer -= 1; return self.squish_timer > 0
        if self.x > cam_x + SCREEN_W + 64: return True
        self.anim_frame += 1
        self.vy += GRAVITY
        if self.vy > MAX_FALL: self.vy = MAX_FALL
        self.x += self.vx
        new_x, hit = collide_solid_x(self.rect, self.vx, level)
        if hit: self.x = float(new_x); self.vx *= -1
        self.y += self.vy
        new_y, new_vy, on_ground, _ = collide_solid_y(self.rect, self.vy, level)
        self.y = float(new_y); self.vy = new_vy
        mid_x = int(self.x)+self.w//2; foot_y = int(self.y)+self.h
        sy = resolve_slope_y(level, mid_x, foot_y, self.h)
        if sy is not None and self.vy >= 0:
            if sy <= self.y+4: self.y = float(sy); self.vy = 0
        if self.y > level.height*TILE_SIZE+100: return False
        return True

    def stomp(self): self.alive = False; self.squish_timer = 20

    def draw(self, surface, cam_x, cam_y, anim_frame):
        sx = int(self.x - cam_x); sy = int(self.y - cam_y)
        if not self.alive:
            c = C_GOOMBA_BODY if self.etype == "goomba" else C_KOOPA_SHELL
            pygame.draw.rect(surface, c, (sx, sy+self.h-8, self.w, 8))
            pygame.draw.rect(surface, C_BLACK, (sx, sy+self.h-8, self.w, 8), 2)
            return
        if self.etype == "goomba":
            _draw_goomba(surface, sx+2, sy+2, self.anim_frame)
        else:
            _draw_koopa(surface, sx+2, sy+2, self.anim_frame)


class CoinParticle:
    def __init__(self, x, y): self.x,self.y = x,y; self.vy=-10; self.timer=35; self.rx=random.randint(-2,2)
    def update(self): self.y+=self.vy; self.x+=self.rx*0.3; self.vy+=0.5; self.timer-=1; return self.timer>0
    def draw(self, surface, cam_x, cam_y):
        sx = int(self.x-cam_x); sy = int(self.y-cam_y)
        pygame.draw.rect(surface, C_BLACK, (sx-6, sy-10, 12, 20))
        pygame.draw.rect(surface, C_COIN_MID, (sx-4, sy-8, 8, 16))
        pygame.draw.rect(surface, C_COIN_BRIGHT, (sx-2, sy-6, 4, 12))


class ScoreParticle:
    def __init__(self, x, y, score):
        self.x,self.y = x,y; self.score=score; self.timer=45; self.vy=-1.2
    def update(self): self.y+=self.vy; self.timer-=1; return self.timer>0
    def draw(self, surface, cam_x, cam_y, font):
        sx=int(self.x-cam_x); sy=int(self.y-cam_y)
        txt=font.render(str(self.score),True,C_WHITE)
        surface.blit(txt,(sx-txt.get_width()//2,sy))


class GameState:
    MENU=0; PLAYING=1; EDITOR=2; GAME_OVER=3; WIN=4; GAME_COMPLETE=5


# ─────────────────────────────────────────
#  BACKGROUND DRAWING
# ─────────────────────────────────────────
def draw_overworld_bg(surface, cam_x, cam_y, anim_frame):
    surface.fill(C_SKY)

def draw_underground_bg(surface, cam_x, cam_y, anim_frame):
    surface.fill(C_UNDERGROUND)

def draw_castle_bg(surface, cam_x, cam_y, anim_frame):
    surface.fill(C_CASTLE_BG)

def draw_water_bg(surface, cam_x, cam_y, anim_frame):
    surface.fill(C_WATER_BG)


def draw_goal_pole(surface, level, gx, gy, cam_x, cam_y, anim_frame):
    """Draw a full-height flag pole from its top tile down to the ground, NES-style."""
    world_x = gx * TILE_SIZE
    world_y_top = gy * TILE_SIZE

    # Find the first solid ground tile below the pole in this column
    ground_gy = None
    for sy in range(gy + 1, level.height):
        t = level.get(gx, sy)
        if t in (TileType.GROUND, TileType.BRIDGE, TileType.HARD_BLOCK, TileType.BRICK, TileType.PLATFORM):
            ground_gy = sy
            break
    if ground_gy is None:
        ground_gy = level.height - 1

    sx = int(world_x - cam_x)
    top_y = int(world_y_top - cam_y)
    bottom_y = int(ground_gy * TILE_SIZE - cam_y)

    pole_x = sx + TILE_SIZE // 2 - 2
    pole_h = max(8, bottom_y - top_y + TILE_SIZE // 2)

    # Pole
    pygame.draw.rect(surface, C_BLACK, (pole_x, top_y, 4, pole_h))

    # Simple flapping flag at the top
    flag_w = 16
    flag_h = 14
    wave = int(math.sin(anim_frame * 0.15) * 2)
    flag_x = pole_x + 4
    flag_y = top_y + 4 + wave

    pygame.draw.rect(surface, C_GREEN, (flag_x, flag_y, flag_w, flag_h))
    pygame.draw.rect(surface, C_BLACK, (flag_x, flag_y, flag_w, flag_h), 2)

# ─────────────────────────────────────────
#  LEVEL GENERATOR — ALL 32 SMB1 LEVELS
# ─────────────────────────────────────────
def make_level(world, stage):
    """Build any of the 32 World X-Y levels with NES-accurate theming."""
    if stage == 4: theme = "castle"
    elif (world, stage) in [(1,2),(4,2),(7,2)]: theme = "underground"
    elif (world, stage) in [(2,2),(3,2),(7,2)]: theme = "water"
    elif (world, stage) in [(3,1),(3,3),(4,1),(6,3)]: theme = "bridge"
    elif stage == 3 and world in [5,6,7]: theme = "cloud"
    else: theme = "overworld"

    bg_map = {
        "overworld":   C_SKY,
        "underground": C_UNDERGROUND,
        "castle":      C_CASTLE_BG,
        "water":       C_WATER_BG,
        "bridge":      C_SKY,
        "cloud":       C_SKY,
    }

    W = 220 if (world==1 and stage==1) else 200
    H = 19
    lv = Level(W, H)
    lv.name  = f"World {world}-{stage}"
    lv.theme = theme
    lv.bg_color = bg_map[theme]
    lv.time_limit = 300 if theme in ("castle","underground") else 400

    s = lv.set
    difficulty = (world-1)*4 + stage
    random.seed(world*100+stage)

    # ── WORLD 1-1 (exact replica) ──────────────────────────────────────
    if world==1 and stage==1:
        lv.time_limit=400
        s(3,16,TileType.PLAYER_SPAWN)
        for gx in range(W):
            if not (69<=gx<=70 or 86<=gx<=88 or 153<=gx<=154):
                s(gx,17,TileType.GROUND); s(gx,18,TileType.GROUND)
        for bx in range(0,W,48):
            s(bx,16,TileType.HILL); s(bx+8,5,TileType.CLOUD); s(bx+11,16,TileType.BUSH)
            s(bx+16,16,TileType.HILL); s(bx+19,4,TileType.CLOUD); s(bx+23,16,TileType.BUSH)
            s(bx+27,5,TileType.CLOUD); s(bx+36,6,TileType.CLOUD); s(bx+41,16,TileType.BUSH)
        def pipe(x,h):
            # Globally reduced pipe height (min 1)
            h = max(1, h-1)
            ty=17-h; s(x,ty,TileType.PIPE_TL); s(x+1,ty,TileType.PIPE_TR)
            for py in range(ty+1,17): s(x,py,TileType.PIPE_BL); s(x+1,py,TileType.PIPE_BR)
        pipe(28,2); pipe(38,3); pipe(46,4); pipe(57,4); pipe(163,2); pipe(179,2)
        s(16,13,TileType.QUESTION)
        s(20,13,TileType.BRICK); s(21,13,TileType.QUESTION); s(21,12,TileType.MUSHROOM_SPAWN)
        s(22,13,TileType.BRICK); s(23,13,TileType.QUESTION); s(24,13,TileType.BRICK)
        s(22,9,TileType.QUESTION)
        s(77,13,TileType.BRICK); s(78,13,TileType.QUESTION); s(78,12,TileType.MUSHROOM_SPAWN)
        s(79,13,TileType.BRICK)
        for i in range(80,88): s(i,9,TileType.BRICK)
        for i in range(94,98): s(i,9,TileType.BRICK)
        s(100,13,TileType.BRICK); s(101,13,TileType.BRICK); s(102,13,TileType.QUESTION); s(103,13,TileType.BRICK)
        s(106,13,TileType.BRICK); s(107,13,TileType.QUESTION); s(108,13,TileType.BRICK)
        s(109,9,TileType.QUESTION)
        s(112,13,TileType.BRICK); s(113,13,TileType.BRICK)
        s(118,9,TileType.BRICK)
        for i in range(121,124): s(i,9,TileType.BRICK)
        for i in range(128,132): s(i,9,TileType.BRICK)
        s(129,13,TileType.BRICK); s(130,13,TileType.BRICK)
        s(168,13,TileType.BRICK); s(169,13,TileType.BRICK); s(170,13,TileType.QUESTION); s(171,13,TileType.BRICK)
        def stairs(x,w,d):
            for i in range(w):
                h=i+1 if d=="up" else w-i
                for yy in range(h): s(x+i,16-yy,TileType.HARD_BLOCK)
        stairs(134,4,"up"); stairs(140,4,"down"); stairs(148,5,"up"); stairs(155,4,"down"); stairs(181,8,"up")
        s(198,6,TileType.GOAL_POLE)
        for i in range(202,207):
            for yy in range(12,17): s(i,yy,TileType.HARD_BLOCK)
        s(204,16,TileType.EMPTY); s(204,15,TileType.EMPTY)
        s(202,11,TileType.HARD_BLOCK); s(204,11,TileType.HARD_BLOCK); s(206,11,TileType.HARD_BLOCK)
        for ex in [22,40,51,52,80,82,97,98,114,115,124,125,128,129,174,175]:
            s(ex,16,TileType.GOOMBA_SPAWN)
        s(107,16,TileType.KOOPA_SPAWN)
        return lv

    # Generic generation fallback
    if stage == 4:
        _build_castle_level(lv, W, H, difficulty)
    elif theme == "underground":
        _build_underground_level(lv, W, H, difficulty)
    elif theme == "water":
        _build_water_level(lv, W, H, difficulty)
    elif theme == "bridge":
        _build_bridge_level(lv, W, H, difficulty)
    elif theme == "cloud":
        _build_cloud_level(lv, W, H, difficulty)
    else:
        _build_overworld(lv, W, H, difficulty, world, stage)
    return lv

def _pipe(lv, x, h):
    # Globally reduced pipe height (min 1)
    h = max(1, h-1)
    ty = 17 - h
    lv.set(x,ty,TileType.PIPE_TL); lv.set(x+1,ty,TileType.PIPE_TR)
    for py in range(ty+1,17): lv.set(x,py,TileType.PIPE_BL); lv.set(x+1,py,TileType.PIPE_BR)

def _stair(lv, x, w, direction):
    for i in range(w):
        h = i+1 if direction=="up" else w-i
        for yy in range(h): lv.set(x+i,16-yy,TileType.HARD_BLOCK)

def _castle_block(lv, x1, y1, x2, y2):
    for gx in range(x1,x2+1):
        for gy in range(y1,y2+1): lv.set(gx,gy,TileType.HARD_BLOCK)

def _build_overworld(lv, W, H, difficulty, world, stage):
    s = lv.set
    s(3,16,TileType.PLAYER_SPAWN)
    # Less frequent, smaller pits
    pit_chance = 0.010 + difficulty*0.0015
    for bx in range(0,W,48):
        s(bx,16,TileType.HILL); s(bx+8,5,TileType.CLOUD)
        s(bx+11,16,TileType.BUSH); s(bx+19,4,TileType.CLOUD); s(bx+23,16,TileType.BUSH)
    gx=0
    while gx < W-12:
        if gx > 10 and gx < W-25 and random.random() < pit_chance:
            # Narrower gaps: 1–2 tiles wide
            pit_w = random.randint(1, 2)
            gx += pit_w; continue
        s(gx,17,TileType.GROUND); s(gx,18,TileType.GROUND)
        if gx > 8 and gx < W-20 and random.random() < 0.04:
            h = random.randint(2,3+world//3)
            _pipe(lv, gx, h); gx += 2; continue
        if gx > 6 and random.random() < 0.05:
            row_y = 13 if random.random()<0.7 else 9
            for dx in range(random.randint(1,4)):
                t = random.choice([TileType.BRICK,TileType.BRICK,TileType.QUESTION])
                s(gx+dx, row_y, t)
        if gx > 10 and random.random() < 0.04+world*0.005:
            etype = TileType.GOOMBA_SPAWN if world<5 else TileType.KOOPA_SPAWN
            s(gx,16,etype)
            if random.random()<0.3 and gx+1<W: s(gx+1,16,etype)
        gx += 1
    for gx in range(W-12,W): s(gx,17,TileType.GROUND); s(gx,18,TileType.GROUND)
    _stair(lv, W-12, 8, "up")
    s(W-2, 6, TileType.GOAL_POLE)

def _build_underground_level(lv, W, H, difficulty):
    s = lv.set
    s(2,16,TileType.PLAYER_SPAWN)
    for gx in range(W): s(gx,17,TileType.GROUND); s(gx,18,TileType.GROUND)
    for gx in range(W):
        if not (55<=gx<=60): s(gx,0,TileType.BRICK); s(gx,1,TileType.BRICK)
    for gx in range(8,45,2): s(gx,3,TileType.COIN)
    for group_x in range(10, W-20, 25):
        row_y = random.choice([9,11,13])
        for dx in range(random.randint(3,7)):
            t = random.choice([TileType.BRICK]*4+[TileType.QUESTION,TileType.COIN])
            s(group_x+dx, row_y, t)
        if random.random()<0.5 and group_x+15<W-20:
            _pipe(lv, group_x+12, random.randint(2,3))
    for ex in range(20,W-15,random.randint(8,14)):
        s(ex, 16, TileType.GOOMBA_SPAWN)
    _stair(lv, W-12, 8, "up")
    s(W-2, 6, TileType.GOAL_POLE)

def _build_castle_level(lv, W, H, difficulty):
    s = lv.set
    s(2,16,TileType.PLAYER_SPAWN)
    for gx in range(W): s(gx,17,TileType.GROUND); s(gx,18,TileType.GROUND)
    for pit_x in range(20,W-25,30):
        # Narrower lava pits so holes feel less punishing
        pit_w = random.randint(2, 3)
        for gx in range(pit_x,pit_x+pit_w):
            for gy in range(16,18): s(gx,gy,TileType.EMPTY)
            s(gx,16,TileType.LAVA); s(gx,17,TileType.LAVA)
    for wall_x in range(15,W-15,25):
        h = random.randint(2,5)
        for gy in range(17-h,17): s(wall_x,gy,TileType.HARD_BLOCK)
        s(wall_x,16,TileType.EMPTY); s(wall_x,15,TileType.EMPTY)
    for plat_x in range(12,W-20,18):
        plat_y = random.randint(9,13)
        for dx in range(random.randint(2,5)): s(plat_x+dx,plat_y,TileType.HARD_BLOCK)
    for ex in range(15,W-20,15): s(ex,16,TileType.KOOPA_SPAWN)
    s(W-5,12,TileType.GOAL_POLE)
    _castle_block(lv,W-10,10,W-3,17)
    for gy in range(13,17): s(W-7,gy,TileType.EMPTY); s(W-6,gy,TileType.EMPTY)

def _build_water_level(lv, W, H, difficulty):
    s = lv.set
    s(2,12,TileType.PLAYER_SPAWN)
    for gy in range(2,H): 
        for gx in range(W): s(gx,gy,TileType.WATER_TILE)
    for gx in range(W): s(gx,17,TileType.GROUND); s(gx,18,TileType.GROUND)
    for ob_x in range(15,W-20,20):
        # Slightly shorter water pipes
        h = max(2, random.randint(3,6+difficulty//3)-1)
        for gy in range(17-h,17): s(ob_x,gy,TileType.PIPE_BL); s(ob_x+1,gy,TileType.PIPE_BR)
        s(ob_x,17-h,TileType.PIPE_TL); s(ob_x+1,17-h,TileType.PIPE_TR)
    for ob_x in range(25,W-20,28):
        h = random.randint(2,5)
        for gy in range(2,2+h): s(ob_x,gy,TileType.HARD_BLOCK); s(ob_x+1,gy,TileType.HARD_BLOCK)
    for gx in range(5,W-5,4):
        gy = random.randint(5,13)
        s(gx,gy,TileType.COIN)
    for ex in range(10,W-15,18): s(ex,10,TileType.KOOPA_SPAWN)
    _pipe(lv, W-8, 8); s(W-2,6,TileType.GOAL_POLE)

def _build_bridge_level(lv, W, H, difficulty):
    s = lv.set
    s(2,14,TileType.PLAYER_SPAWN)
    for gx in range(W): s(gx,17,TileType.BRIDGE)
    for plat_x in range(8,W-15,14):
        plat_y = random.randint(9,13)
        for dx in range(random.randint(3,6)): s(plat_x+dx,plat_y,TileType.HARD_BLOCK)
    for qx in range(12,W-15,20): s(qx,12,TileType.QUESTION)
    for ex in range(14,W-15,12):
        s(ex,16,TileType.KOOPA_SPAWN if difficulty>8 else TileType.GOOMBA_SPAWN)
    s(W-2,6,TileType.GOAL_POLE)

def _build_cloud_level(lv, W, H, difficulty):
    s = lv.set
    s(2,14,TileType.PLAYER_SPAWN)
    cloud_ys = [10,12,14,11,13]
    for i,cx in enumerate(range(0,W,8)):
        cy = cloud_ys[i%len(cloud_ys)]
        for dx in range(6): s(cx+dx,cy,TileType.PLATFORM)
    for gx in range(4,W-4,3): s(gx,8,TileType.COIN)
    for bx in range(10,W-20,15): s(bx,10,TileType.QUESTION)
    for ex in range(10,W-10,18): s(ex,9,TileType.GOOMBA_SPAWN)
    s(W-6,6,TileType.GOAL_POLE)


# ─────────────────────────────────────────
#  MAIN APP
# ─────────────────────────────────────────
class UltraMarioForever:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption("Ultra Mario Forever — NES 8-Bit Edition")
        self.screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
        self.clock  = pygame.time.Clock()
        self.state  = GameState.MENU

        self.font      = pygame.font.SysFont("couriernew", 22, bold=True)
        self.font_sm   = pygame.font.SysFont("couriernew", 16, bold=True)
        self.font_lg   = pygame.font.SysFont("couriernew", 36, bold=True)
        self.font_title= pygame.font.SysFont("couriernew", 44, bold=True)

        self.level = None; self.player = None
        self.enemies = []; self.particles = []; self.score_pops = []
        self.cam_x = 0; self.cam_y = 0
        self.anim_frame = 0; self.game_timer = 0

        self.world=1; self.stage=1
        self.menu_sel=0
        self.menu_items=["Start Game","Level Editor","Credits","Quit"]

        # Editor
        self.ed_cam_x=0; self.ed_cam_y=0
        self.ed_selected=TileType.GROUND
        self.ed_show_grid=True; self.ed_palette_scroll=0
        self.ed_input_mode=None; self.ed_input_text=""
        self.ed_testing=False

    def run(self):
        running=True
        while running:
            self.clock.tick(FPS); self.anim_frame += 1
            events=pygame.event.get()
            for ev in events:
                if ev.type==pygame.QUIT: running=False
            if   self.state==GameState.MENU:        self._update_menu(events); self._draw_menu()
            elif self.state==GameState.PLAYING:     self._update_game(events); self._draw_game()
            elif self.state==GameState.EDITOR:      self._update_editor(events); self._draw_editor()
            elif self.state==GameState.GAME_OVER:   self._update_gameover(events); self._draw_gameover()
            elif self.state==GameState.WIN:         self._update_win(events); self._draw_win()
            elif self.state==GameState.GAME_COMPLETE: self._update_complete(events); self._draw_complete()
            pygame.display.flip()
        pygame.quit()

    # ── MENU ─────────────────────────────────────────────────────────
    def _update_menu(self, events):
        for ev in events:
            if ev.type==pygame.KEYDOWN:
                if ev.key==pygame.K_UP:   self.menu_sel=(self.menu_sel-1)%len(self.menu_items)
                elif ev.key==pygame.K_DOWN: self.menu_sel=(self.menu_sel+1)%len(self.menu_items)
                elif ev.key in (pygame.K_RETURN,pygame.K_SPACE):
                    if self.menu_sel==0:
                        self.world=1; self.stage=1; self._load_and_start()
                    elif self.menu_sel==1:
                        self.level=Level(220,19); self.state=GameState.EDITOR
                    elif self.menu_sel==2: pass
                    elif self.menu_sel==3: pygame.quit(); sys.exit()

    def _draw_menu(self):
        draw_overworld_bg(self.screen, 0, 0, self.anim_frame)
        for gx in range(GRID_W+1):
            draw_tile(self.screen, TileType.GROUND, gx*TILE_SIZE, SCREEN_H-2*TILE_SIZE)
            draw_tile(self.screen, TileType.GROUND, gx*TILE_SIZE, SCREEN_H-TILE_SIZE)

        for i,_ in enumerate(range(3)):
            cx=(i*200 + self.anim_frame//2)%(SCREEN_W+100)-50
            draw_tile(self.screen, TileType.CLOUD, cx, 40+i*20, self.anim_frame)

        draw_tile(self.screen,TileType.HILL,50,SCREEN_H-3*TILE_SIZE)
        draw_tile(self.screen,TileType.BUSH,250,SCREEN_H-3*TILE_SIZE)
        draw_tile(self.screen,TileType.HILL,450,SCREEN_H-3*TILE_SIZE)

        box_r = pygame.Rect(SCREEN_W//2-200, 30, 400, 120)
        pygame.draw.rect(self.screen, C_BLACK, box_r)
        pygame.draw.rect(self.screen, C_GOLD, box_r, 4)

        t1 = self.font_title.render("SUPER MARIO", True, C_RED)
        t2 = self.font_lg.render("FOREVER NES", True, C_YELLOW)
        self.screen.blit(t1,(SCREEN_W//2-t1.get_width()//2, 40))
        self.screen.blit(t2,(SCREEN_W//2-t2.get_width()//2, 90))

        for i,item in enumerate(self.menu_items):
            color = C_YELLOW if i==self.menu_sel else C_WHITE
            prefix = "> " if i==self.menu_sel else "  "
            txt = self.font.render(prefix+item, True, color)
            self.screen.blit(txt,(SCREEN_W//2-txt.get_width()//2, 180+i*35))

        ctrl=self.font_sm.render("Arrows:Move Shift:Sprint W:Jump", True, C_BLACK)
        self.screen.blit(ctrl,(SCREEN_W//2-ctrl.get_width()//2, SCREEN_H-20))
        draw_mario(self.screen, 100, SCREEN_H-3*TILE_SIZE-2, 1, False, False, self.anim_frame//4)

    # ── GAME ─────────────────────────────────────────────────────────
    def _load_and_start(self):
        self.level = make_level(self.world, self.stage)
        self._start_game()

    def _start_game(self):
        sx,sy = self.level.find_spawn()
        self.player = Player(sx,sy)
        self.enemies=[]; self.particles=[]; self.score_pops=[]
        self.cam_x=0; self.cam_y=0
        # Timer stored in "SMB seconds" so it counts down faster like on Famicom
        self.game_timer=self.level.time_limit*SMB_TIMER_TICKS_PER_SECOND
        for gy in range(self.level.height):
            for gx in range(self.level.width):
                t=self.level.get(gx,gy)
                if t==TileType.GOOMBA_SPAWN: self.enemies.append(Enemy(gx*TILE_SIZE+2,gy*TILE_SIZE+4,"goomba"))
                elif t==TileType.KOOPA_SPAWN: self.enemies.append(Enemy(gx*TILE_SIZE+2,gy*TILE_SIZE+2,"koopa"))
        self.state=GameState.PLAYING

    def _update_game(self, events):
        for ev in events:
            if ev.type==pygame.KEYDOWN:
                if ev.key==pygame.K_ESCAPE:
                    if self.ed_testing: self.ed_testing=False; self.state=GameState.EDITOR; return
                    self.state=GameState.MENU; return

        if not self.player.alive:
            self.player.update(pygame.key.get_pressed(),self.level)
            if self.player.y > self.cam_y + SCREEN_H + 200:
                if self.player.lives>0: self._load_and_start()
                else: self.state=GameState.GAME_OVER
            return

        keys=pygame.key.get_pressed()
        self.player.update(keys,self.level)
        
        # Camera X
        target_x = self.player.x - SCREEN_W//3
        self.cam_x += (target_x-self.cam_x)*0.12
        self.cam_x = max(0, min(self.cam_x, self.level.width*TILE_SIZE-SCREEN_W))
        
        # Camera Y (Vertical scrolling fix for 600x400 view on tall level)
        target_y = self.player.y - SCREEN_H//2 + 50
        self.cam_y += (target_y - self.cam_y) * 0.12
        self.cam_y = max(0, min(self.cam_y, self.level.height*TILE_SIZE - SCREEN_H))

        self.enemies=[e for e in self.enemies if e.update(self.level,self.cam_x)]

        pr=self.player.rect
        for e in self.enemies:
            if not e.alive: continue
            er=e.rect
            if pr.colliderect(er):
                if self.player.vy>0 and pr.bottom-10 < er.centery:
                    e.stomp(); self.player.vy=JUMP_FORCE*0.6
                    self.player.score+=100
                    self.score_pops.append(ScoreParticle(e.x+14,e.y,100))
                else: self.player.die()

        for gy in range(max(0,pr.top//TILE_SIZE), min(self.level.height,pr.bottom//TILE_SIZE+1)):
            for gx in range(max(0,pr.left//TILE_SIZE), min(self.level.width,pr.right//TILE_SIZE+1)):
                t=self.level.get(gx,gy)
                tr=pygame.Rect(gx*TILE_SIZE,gy*TILE_SIZE,TILE_SIZE,TILE_SIZE)
                if not pr.colliderect(tr): continue
                if t==TileType.COIN:
                    self.level.set(gx,gy,TileType.EMPTY); self.player.coins+=1; self.player.score+=100
                    self.particles.append(CoinParticle(gx*TILE_SIZE+16,gy*TILE_SIZE))
                elif t==TileType.MUSHROOM_SPAWN:
                    self.level.set(gx,gy,TileType.EMPTY)
                    if not self.player.big: self.player.big=True; self.player.h=50; self.player.y-=20
                    self.player.score+=1000
                elif t==TileType.SPIKE:
                    sr=pygame.Rect(gx*TILE_SIZE+4,gy*TILE_SIZE+8,TILE_SIZE-8,TILE_SIZE-8)
                    if pr.colliderect(sr): self.player.die()
                elif t==TileType.LAVA:
                    self.player.die()
                elif t==TileType.GOAL_POLE:
                    self.player.won=True; self.player.score+=5000
                    self.state=GameState.WIN

        self.particles=[p for p in self.particles if p.update()]
        self.score_pops=[p for p in self.score_pops if p.update()]
        self.game_timer-=1
        if self.game_timer<=0: self.player.die()

    def _draw_game(self):
        theme = getattr(self.level,'theme','overworld')
        if   theme=="underground": draw_underground_bg(self.screen,self.cam_x,self.cam_y,self.anim_frame)
        elif theme=="castle":      draw_castle_bg(self.screen,self.cam_x,self.cam_y,self.anim_frame)
        elif theme=="water":       draw_water_bg(self.screen,self.cam_x,self.cam_y,self.anim_frame)
        else:                      draw_overworld_bg(self.screen,self.cam_x,self.cam_y,self.anim_frame)

        start_gx=max(0,int(self.cam_x//TILE_SIZE)-1)
        end_gx=min(self.level.width,int((self.cam_x+SCREEN_W)//TILE_SIZE)+2)
        start_gy=max(0,int(self.cam_y//TILE_SIZE)-1)
        end_gy=min(self.level.height,int((self.cam_y+SCREEN_H)//TILE_SIZE)+2)
        skip={TileType.EMPTY,TileType.GOOMBA_SPAWN,TileType.KOOPA_SPAWN,TileType.PLAYER_SPAWN}

        for gy in range(start_gy, end_gy):
            for gx in range(start_gx, end_gx):
                t=self.level.get(gx,gy)
                if t in BG_TILES:
                    draw_tile(self.screen,t,gx*TILE_SIZE-int(self.cam_x),gy*TILE_SIZE-int(self.cam_y),self.anim_frame,theme=="underground")

        for gy in range(start_gy, end_gy):
            for gx in range(start_gx, end_gx):
                t=self.level.get(gx,gy)
                if t == TileType.GOAL_POLE:
                    draw_goal_pole(self.screen, self.level, gx, gy, self.cam_x, self.cam_y, self.anim_frame)
                elif t not in skip and t not in BG_TILES:
                    draw_tile(self.screen,t,gx*TILE_SIZE-int(self.cam_x),gy*TILE_SIZE-int(self.cam_y),self.anim_frame,theme=="underground")

        for e in self.enemies: e.draw(self.screen,self.cam_x,self.cam_y,self.anim_frame)
        self.player.draw(self.screen,self.cam_x,self.cam_y)
        for p in self.particles: p.draw(self.screen,self.cam_x,self.cam_y)
        for p in self.score_pops: p.draw(self.screen,self.cam_x,self.cam_y,self.font_sm)
        self._draw_hud()

    def _draw_hud(self):
        items=[
            f"W {self.world}-{self.stage}",
            f"MARIO",
            f"{self.player.score:06d}",
            f"Ox{self.player.coins:02d}",
            f"TIME",
            # Display remaining time in whole SMB-style seconds
            f"{max(0,self.game_timer//SMB_TIMER_TICKS_PER_SECOND):03d}",
        ]
        y = 10
        self.screen.blit(self.font.render(items[1],True,C_WHITE),(30,y))
        self.screen.blit(self.font.render(items[2],True,C_WHITE),(30,y+20))
        self.screen.blit(self.font.render(items[3],True,C_WHITE),(180,y+20))
        self.screen.blit(self.font.render(items[0],True,C_WHITE),(300,y))
        self.screen.blit(self.font.render(items[4],True,C_WHITE),(480,y))
        self.screen.blit(self.font.render(items[5],True,C_WHITE),(480,y+20))

    def _update_gameover(self, events):
        for ev in events:
            if ev.type==pygame.KEYDOWN: self.state=GameState.MENU

    def _draw_gameover(self):
        self.screen.fill(C_BLACK)
        txt=self.font_lg.render("GAME OVER",True,C_WHITE)
        self.screen.blit(txt,(SCREEN_W//2-txt.get_width()//2,SCREEN_H//2-30))
        info=self.font_sm.render("Press any key to return",True,C_GRAY)
        self.screen.blit(info,(SCREEN_W//2-info.get_width()//2,SCREEN_H//2+30))

    def _update_win(self, events):
        for ev in events:
            if ev.type==pygame.KEYDOWN:
                self.stage+=1
                if self.stage>4: self.stage=1; self.world+=1
                if self.world>8: self.state=GameState.GAME_COMPLETE
                else: self._load_and_start()

    def _draw_win(self):
        draw_overworld_bg(self.screen,0,0,self.anim_frame)
        disp_w,disp_s=self.world,self.stage-1
        if disp_s<1: disp_s=4; disp_w=self.world-1
        txt=self.font_lg.render(f"WORLD {disp_w}-{disp_s} CLEAR!",True,C_YELLOW)
        self.screen.blit(txt,(SCREEN_W//2-txt.get_width()//2,SCREEN_H//2-40))
        nxt=self.font_sm.render(f"Next: World {self.world}-{self.stage}  (any key)",True,C_WHITE)
        self.screen.blit(nxt,(SCREEN_W//2-nxt.get_width()//2,SCREEN_H//2+20))

    def _update_complete(self, events):
        for ev in events:
            if ev.type==pygame.KEYDOWN: self.state=GameState.MENU

    def _draw_complete(self):
        self.screen.fill(C_BLACK)
        t1=self.font_lg.render("CONGRATULATIONS!",True,C_GOLD)
        t2=self.font.render("You defeated Bowser & saved Princess Peach!",True,C_WHITE)
        self.screen.blit(t1,(SCREEN_W//2-t1.get_width()//2,SCREEN_H//2-60))
        self.screen.blit(t2,(SCREEN_W//2-t2.get_width()//2,SCREEN_H//2))

    # ── EDITOR ───────────────────────────────────────────────────────
    def _update_editor(self, events):
        if self.ed_input_mode: self._update_editor_input(events); return
        keys=pygame.key.get_pressed(); spd=8
        if keys[pygame.K_LEFT]:  self.ed_cam_x-=spd
        if keys[pygame.K_RIGHT]: self.ed_cam_x+=spd
        if keys[pygame.K_UP]:    self.ed_cam_y-=spd
        if keys[pygame.K_DOWN]:  self.ed_cam_y+=spd
        self.ed_cam_x=max(0,min(self.ed_cam_x,self.level.width*TILE_SIZE-SCREEN_W))
        self.ed_cam_y=max(0,min(self.ed_cam_y,self.level.height*TILE_SIZE-SCREEN_H+80))
        mouse=pygame.mouse.get_pressed(); mx,my=pygame.mouse.get_pos()
        in_canvas=my<SCREEN_H-80
        if in_canvas:
            gx=(mx+int(self.ed_cam_x))//TILE_SIZE; gy=(my+int(self.ed_cam_y))//TILE_SIZE
            if mouse[0]: self.level.set(gx,gy,int(self.ed_selected))
            elif mouse[2]: self.level.set(gx,gy,TileType.EMPTY)
        for ev in events:
            if ev.type==pygame.KEYDOWN:
                if ev.key==pygame.K_ESCAPE: self.state=GameState.MENU
                elif ev.key==pygame.K_TAB: self.ed_show_grid=not self.ed_show_grid
                elif ev.key==pygame.K_p: self.ed_testing=True; self._start_game()
                elif ev.key==pygame.K_s and (keys[pygame.K_LCTRL] or keys[pygame.K_RCTRL]):
                    self.ed_input_mode="save"; self.ed_input_text=self.level.name.replace(" ","_").lower()
            elif ev.type==pygame.MOUSEWHEEL:
                if not in_canvas: self.ed_palette_scroll=max(0,self.ed_palette_scroll-ev.y*2)
                else:
                    tiles=[t for t in TileType if t!=TileType.EMPTY]
                    idx=tiles.index(self.ed_selected) if self.ed_selected in tiles else 0
                    idx=(idx+ev.y)%len(tiles); self.ed_selected=tiles[idx]

    def _update_editor_input(self, events):
        for ev in events:
            if ev.type==pygame.KEYDOWN:
                if ev.key==pygame.K_ESCAPE: self.ed_input_mode=None
                elif ev.key==pygame.K_RETURN:
                    self.ed_input_mode=None
                elif ev.key==pygame.K_BACKSPACE: self.ed_input_text=self.ed_input_text[:-1]
                elif len(self.ed_input_text)<40 and ev.unicode.isprintable(): self.ed_input_text+=ev.unicode

    def _draw_editor(self):
        self.screen.fill(self.level.bg_color)
        start_gx=max(0,int(self.ed_cam_x//TILE_SIZE))
        end_gx=min(self.level.width,int((self.ed_cam_x+SCREEN_W)//TILE_SIZE)+2)
        start_gy=max(0,int(self.ed_cam_y//TILE_SIZE))
        end_gy=min(self.level.height,int((self.ed_cam_y+SCREEN_H-80)//TILE_SIZE)+2)
        for gy in range(start_gy,end_gy):
            for gx in range(start_gx,end_gx):
                t=self.level.get(gx,gy)
                if t!=TileType.EMPTY:
                    draw_tile(self.screen,t,gx*TILE_SIZE-int(self.ed_cam_x),gy*TILE_SIZE-int(self.ed_cam_y),self.anim_frame)
        if self.ed_show_grid:
            gs=pygame.Surface((SCREEN_W,SCREEN_H-80),pygame.SRCALPHA)
            for gx in range(start_gx,end_gx+1):
                px=gx*TILE_SIZE-int(self.ed_cam_x)
                pygame.draw.line(gs,(255,255,255,30),(px,0),(px,SCREEN_H-80),1)
            for gy in range(start_gy,end_gy+1):
                py=gy*TILE_SIZE-int(self.ed_cam_y)
                pygame.draw.line(gs,(255,255,255,30),(0,py),(SCREEN_W,py),1)
            self.screen.blit(gs,(0,0))
        palette_y=SCREEN_H-80
        pygame.draw.rect(self.screen,(20,20,40),(0,palette_y,SCREEN_W,80))
        pygame.draw.line(self.screen,C_GOLD,(0,palette_y),(SCREEN_W,palette_y),2)
        tiles=[t for t in TileType if t!=TileType.EMPTY]
        cols=SCREEN_W//(TILE_SIZE+4)
        for i,t in enumerate(tiles):
            col=i%cols; row=i//cols
            px=col*(TILE_SIZE+4)+4; py=palette_y+8+row*(TILE_SIZE+4)-self.ed_palette_scroll
            if palette_y<=py<=SCREEN_H:
                draw_tile(self.screen,t,px,py,self.anim_frame)
                if t==self.ed_selected: pygame.draw.rect(self.screen,C_YELLOW,(px-2,py-2,TILE_SIZE+4,TILE_SIZE+4),2)

if __name__=="__main__":
    app = UltraMarioForever()
    app.run()
