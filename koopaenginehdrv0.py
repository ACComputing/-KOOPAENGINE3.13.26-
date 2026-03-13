"""
╔══════════════════════════════════════════════════════════════╗
║           ULTRA MARIO FOREVER ENGINE v1.0                    ║
║     Inspired by Thunder Engine & Mario Worker Remake         ║
║              Built with Pygame                               ║
╚══════════════════════════════════════════════════════════════╝

A complete Super Mario-style platformer engine with:
  - Full platformer physics (gravity, jumping, running)
  - Multiple tile types (ground, brick, question block, pipe, etc.)
  - Enemies (Goomba, Koopa)
  - Coins & power-ups
  - Built-in Level Editor (Mario Worker style)
  - JSON-based level format
  - Sample level: Samsoft Course Pack 1

Controls:
  GAME MODE:
    Arrow Keys / WASD  = Move & Jump
    Shift              = Run/Sprint
    ESC                = Back to Menu

  EDITOR MODE:
    Left Click         = Place tile
    Right Click        = Remove tile
    Mouse Wheel        = Scroll tile palette
    Arrow Keys         = Scroll level
    Ctrl+S             = Save level
    Ctrl+L             = Load level
    Ctrl+N             = New level
    Tab                = Toggle grid
    P                  = Test play level
    ESC                = Back to Menu
    +/-                = Resize level width
"""

import pygame
import json
import os
import sys
import math
import random
from enum import IntEnum

# ─── Constants ───────────────────────────────────────────────
TILE_SIZE = 32
SCREEN_W, SCREEN_H = 800, 608
FPS = 60
GRAVITY = 0.6
MAX_FALL = 12
JUMP_FORCE = -11
RUN_SPEED = 4.5
SPRINT_SPEED = 7
FRICTION = 0.85
ACCEL = 0.5

# Grid dimensions for editor
GRID_W = SCREEN_W // TILE_SIZE
GRID_H = SCREEN_H // TILE_SIZE

# ─── Colors ──────────────────────────────────────────────────
C_SKY        = (107, 140, 255)
C_SKY_UG     = (0, 0, 0)
C_WHITE      = (255, 255, 255)
C_BLACK      = (0, 0, 0)
C_RED        = (255, 50, 50)
C_GREEN      = (50, 200, 50)
C_DKGREEN    = (0, 130, 0)
C_BLUE       = (50, 100, 255)
C_YELLOW     = (255, 220, 0)
C_ORANGE     = (255, 165, 0)
C_BROWN      = (139, 90, 43)
C_DKBROWN    = (100, 60, 20)
C_BRICK      = (180, 80, 40)
C_GRAY       = (150, 150, 150)
C_DKGRAY     = (80, 80, 80)
C_PIPE_G     = (0, 180, 0)
C_PIPE_DG    = (0, 120, 0)
C_GOLD       = (255, 200, 0)
C_QUESTION   = (230, 170, 30)
C_SKIN       = (255, 200, 150)
C_PURPLE     = (148, 80, 210)

# ─── Tile Types ──────────────────────────────────────────────
class TileType(IntEnum):
    EMPTY         = 0
    GROUND        = 1
    BRICK         = 2
    QUESTION      = 3
    HARD_BLOCK    = 4
    PIPE_TL       = 5
    PIPE_TR       = 6
    PIPE_BL       = 7
    PIPE_BR       = 8
    COIN          = 9
    GOOMBA_SPAWN  = 10
    KOOPA_SPAWN   = 11
    PLAYER_SPAWN  = 12
    GOAL_POLE     = 13
    CLOUD         = 14
    BUSH          = 15
    HILL          = 16
    USED_BLOCK    = 17
    MUSHROOM_SPAWN= 18
    SPIKE         = 19

TILE_NAMES = {
    TileType.EMPTY:        "Empty",
    TileType.GROUND:       "Ground",
    TileType.BRICK:        "Brick",
    TileType.QUESTION:     "? Block",
    TileType.HARD_BLOCK:   "Hard Block",
    TileType.PIPE_TL:      "Pipe TL",
    TileType.PIPE_TR:      "Pipe TR",
    TileType.PIPE_BL:      "Pipe BL",
    TileType.PIPE_BR:      "Pipe BR",
    TileType.COIN:         "Coin",
    TileType.GOOMBA_SPAWN: "Goomba",
    TileType.KOOPA_SPAWN:  "Koopa",
    TileType.PLAYER_SPAWN: "Player Start",
    TileType.GOAL_POLE:    "Goal Pole",
    TileType.CLOUD:        "Cloud (BG)",
    TileType.BUSH:         "Bush (BG)",
    TileType.HILL:         "Hill (BG)",
    TileType.USED_BLOCK:   "Used Block",
    TileType.MUSHROOM_SPAWN:"Mushroom",
    TileType.SPIKE:        "Spike",
}

SOLID_TILES = {TileType.GROUND, TileType.BRICK, TileType.QUESTION,
               TileType.HARD_BLOCK, TileType.PIPE_TL, TileType.PIPE_TR,
               TileType.PIPE_BL, TileType.PIPE_BR, TileType.USED_BLOCK}

BG_TILES = {TileType.CLOUD, TileType.BUSH, TileType.HILL}

# ─── Tile Renderer ───────────────────────────────────────────
def draw_tile(surface, tile_type, x, y, anim_frame=0):
    """Draw a single tile at pixel position (x, y)."""
    r = pygame.Rect(x, y, TILE_SIZE, TILE_SIZE)
    s = TILE_SIZE

    if tile_type == TileType.GROUND:
        pygame.draw.rect(surface, C_BROWN, r)
        pygame.draw.rect(surface, C_DKBROWN, r, 1)
        # Texture dots
        for dx, dy in [(4,4),(12,8),(20,4),(8,16),(24,20),(16,28),(4,24)]:
            pygame.draw.circle(surface, C_DKBROWN, (x+dx, y+dy), 1)

    elif tile_type == TileType.BRICK:
        pygame.draw.rect(surface, C_BRICK, r)
        # Brick lines
        for row in range(4):
            yy = y + row * 8
            pygame.draw.line(surface, C_DKBROWN, (x, yy), (x+s, yy), 1)
            offset = 0 if row % 2 == 0 else 16
            for col_x in range(offset, s, 16):
                pygame.draw.line(surface, C_DKBROWN, (x+col_x, yy), (x+col_x, yy+8), 1)

    elif tile_type == TileType.QUESTION:
        pygame.draw.rect(surface, C_QUESTION, r)
        pygame.draw.rect(surface, C_DKBROWN, r, 2)
        # Draw ?
        font = pygame.font.SysFont("arial", 20, bold=True)
        txt = font.render("?", True, C_WHITE)
        surface.blit(txt, (x + s//2 - txt.get_width()//2, y + s//2 - txt.get_height()//2))

    elif tile_type == TileType.HARD_BLOCK:
        pygame.draw.rect(surface, C_GRAY, r)
        pygame.draw.rect(surface, C_DKGRAY, r, 2)
        # Cross pattern
        pygame.draw.line(surface, C_DKGRAY, (x, y), (x+s, y+s), 1)
        pygame.draw.line(surface, C_DKGRAY, (x+s, y), (x, y+s), 1)

    elif tile_type == TileType.USED_BLOCK:
        pygame.draw.rect(surface, C_DKBROWN, r)
        pygame.draw.rect(surface, C_BLACK, r, 2)

    elif tile_type in (TileType.PIPE_TL, TileType.PIPE_TR):
        pygame.draw.rect(surface, C_PIPE_G, r)
        pygame.draw.rect(surface, C_PIPE_DG, r, 2)
        if tile_type == TileType.PIPE_TL:
            pygame.draw.line(surface, C_WHITE, (x+2, y+2), (x+2, y+s-2), 2)
        else:
            pygame.draw.line(surface, C_PIPE_DG, (x+s-4, y+2), (x+s-4, y+s-2), 2)

    elif tile_type in (TileType.PIPE_BL, TileType.PIPE_BR):
        inner = pygame.Rect(x+4, y, s-8, s)
        pygame.draw.rect(surface, C_PIPE_G, inner)
        pygame.draw.rect(surface, C_PIPE_DG, inner, 1)

    elif tile_type == TileType.COIN:
        cx, cy = x + s//2, y + s//2
        wobble = math.sin(anim_frame * 0.1) * 4
        pygame.draw.ellipse(surface, C_GOLD, (cx-6+wobble, cy-8, 12, 16))
        pygame.draw.ellipse(surface, C_YELLOW, (cx-4+wobble, cy-6, 8, 12))

    elif tile_type == TileType.GOOMBA_SPAWN:
        # Brown goomba
        cx, cy = x + s//2, y + s - 4
        pygame.draw.ellipse(surface, C_BROWN, (cx-10, cy-20, 20, 14))  # body
        pygame.draw.ellipse(surface, C_DKBROWN, (cx-12, cy-26, 24, 16))  # head
        pygame.draw.circle(surface, C_WHITE, (cx-4, cy-22), 3)  # eye L
        pygame.draw.circle(surface, C_WHITE, (cx+4, cy-22), 3)  # eye R
        pygame.draw.circle(surface, C_BLACK, (cx-4, cy-21), 1)
        pygame.draw.circle(surface, C_BLACK, (cx+4, cy-21), 1)
        pygame.draw.rect(surface, C_DKBROWN, (cx-8, cy-6, 6, 6))  # foot L
        pygame.draw.rect(surface, C_DKBROWN, (cx+2, cy-6, 6, 6))  # foot R

    elif tile_type == TileType.KOOPA_SPAWN:
        cx, cy = x + s//2, y + s - 4
        pygame.draw.ellipse(surface, C_GREEN, (cx-8, cy-22, 16, 18))  # shell
        pygame.draw.ellipse(surface, C_DKGREEN, (cx-6, cy-20, 12, 14))  # inner
        pygame.draw.circle(surface, C_SKIN, (cx, cy-26), 6)  # head
        pygame.draw.circle(surface, C_WHITE, (cx-2, cy-27), 2)
        pygame.draw.circle(surface, C_BLACK, (cx-2, cy-27), 1)
        pygame.draw.rect(surface, C_ORANGE, (cx-6, cy-6, 5, 6))  # foot
        pygame.draw.rect(surface, C_ORANGE, (cx+1, cy-6, 5, 6))

    elif tile_type == TileType.PLAYER_SPAWN:
        cx, cy = x + s//2, y + s - 2
        # Hat
        pygame.draw.rect(surface, C_RED, (cx-8, cy-30, 16, 6))
        pygame.draw.rect(surface, C_RED, (cx-6, cy-28, 18, 4))
        # Face
        pygame.draw.rect(surface, C_SKIN, (cx-6, cy-24, 12, 10))
        pygame.draw.circle(surface, C_BLACK, (cx-2, cy-20), 1)  # eye
        pygame.draw.circle(surface, C_BLACK, (cx+4, cy-20), 1)
        # Body
        pygame.draw.rect(surface, C_RED, (cx-6, cy-14, 12, 8))
        # Legs
        pygame.draw.rect(surface, C_BLUE, (cx-6, cy-6, 5, 6))
        pygame.draw.rect(surface, C_BLUE, (cx+1, cy-6, 5, 6))

    elif tile_type == TileType.GOAL_POLE:
        pygame.draw.rect(surface, C_GRAY, (x + s//2 - 2, y, 4, s))
        pygame.draw.circle(surface, C_GREEN, (x + s//2, y + 4), 5)

    elif tile_type == TileType.CLOUD:
        cx, cy = x + s//2, y + s//2
        pygame.draw.ellipse(surface, C_WHITE, (cx-14, cy-4, 28, 16))
        pygame.draw.ellipse(surface, C_WHITE, (cx-8, cy-10, 16, 14))

    elif tile_type == TileType.BUSH:
        cx, cy = x + s//2, y + s - 4
        pygame.draw.ellipse(surface, C_GREEN, (cx-14, cy-8, 28, 14))
        pygame.draw.ellipse(surface, C_DKGREEN, (cx-10, cy-12, 20, 12))

    elif tile_type == TileType.HILL:
        pts = [(x, y+s), (x+s//2, y+4), (x+s, y+s)]
        pygame.draw.polygon(surface, C_GREEN, pts)
        pygame.draw.polygon(surface, C_DKGREEN, pts, 2)

    elif tile_type == TileType.MUSHROOM_SPAWN:
        cx, cy = x + s//2, y + s - 4
        pygame.draw.rect(surface, C_SKIN, (cx-4, cy-10, 8, 10))  # stem
        pygame.draw.ellipse(surface, C_RED, (cx-10, cy-20, 20, 14))  # cap
        pygame.draw.circle(surface, C_WHITE, (cx-4, cy-16), 3)
        pygame.draw.circle(surface, C_WHITE, (cx+4, cy-16), 3)

    elif tile_type == TileType.SPIKE:
        pts = [(x+4, y+s), (x+s//2, y+4), (x+s-4, y+s)]
        pygame.draw.polygon(surface, C_GRAY, pts)
        pygame.draw.polygon(surface, C_DKGRAY, pts, 2)


# ─── Level Data ──────────────────────────────────────────────
class Level:
    def __init__(self, width=200, height=19):
        self.width = width
        self.height = height
        self.tiles = [[0]*width for _ in range(height)]
        self.bg_color = C_SKY
        self.name = "Untitled"
        self.time_limit = 400
        self.music = "overworld"

    def get(self, gx, gy):
        if 0 <= gx < self.width and 0 <= gy < self.height:
            return self.tiles[gy][gx]
        return 0

    def set(self, gx, gy, val):
        if 0 <= gx < self.width and 0 <= gy < self.height:
            self.tiles[gy][gx] = val

    def to_dict(self):
        return {
            "name": self.name,
            "width": self.width,
            "height": self.height,
            "tiles": self.tiles,
            "bg_color": list(self.bg_color),
            "time_limit": self.time_limit,
            "music": self.music,
        }

    @staticmethod
    def from_dict(d):
        lv = Level(d["width"], d["height"])
        lv.tiles = d["tiles"]
        lv.bg_color = tuple(d.get("bg_color", C_SKY))
        lv.name = d.get("name", "Untitled")
        lv.time_limit = d.get("time_limit", 400)
        lv.music = d.get("music", "overworld")
        return lv

    def save(self, filepath):
        with open(filepath, 'w') as f:
            json.dump(self.to_dict(), f)

    @staticmethod
    def load(filepath):
        with open(filepath, 'r') as f:
            return Level.from_dict(json.load(f))

    def find_spawn(self):
        for gy in range(self.height):
            for gx in range(self.width):
                if self.tiles[gy][gx] == TileType.PLAYER_SPAWN:
                    return gx * TILE_SIZE, gy * TILE_SIZE
        return 3 * TILE_SIZE, 14 * TILE_SIZE


# ─── Entities ────────────────────────────────────────────────
class Player:
    def __init__(self, x, y):
        self.x, self.y = float(x), float(y)
        self.vx, self.vy = 0.0, 0.0
        self.w, self.h = 24, 30
        self.on_ground = False
        self.facing = 1  # 1=right, -1=left
        self.alive = True
        self.big = False
        self.coins = 0
        self.score = 0
        self.lives = 3
        self.won = False
        self.anim_frame = 0
        self.invincible = 0

    @property
    def rect(self):
        return pygame.Rect(int(self.x), int(self.y), self.w, self.h)

    def update(self, keys, level):
        if not self.alive:
            self.vy += GRAVITY
            self.y += self.vy
            return

        # Horizontal movement
        ax = 0
        speed = SPRINT_SPEED if (keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT]) else RUN_SPEED
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            ax = -ACCEL
            self.facing = -1
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            ax = ACCEL
            self.facing = 1

        self.vx += ax
        self.vx *= FRICTION
        self.vx = max(-speed, min(speed, self.vx))
        if abs(self.vx) < 0.1:
            self.vx = 0

        # Horizontal collision
        self.x += self.vx
        self._collide_x(level)

        # Vertical
        if (keys[pygame.K_UP] or keys[pygame.K_w] or keys[pygame.K_SPACE]) and self.on_ground:
            self.vy = JUMP_FORCE
            self.on_ground = False

        self.vy += GRAVITY
        if self.vy > MAX_FALL:
            self.vy = MAX_FALL

        self.y += self.vy
        self.on_ground = False
        self._collide_y(level)

        # Fall off screen
        if self.y > level.height * TILE_SIZE + 100:
            self.die()

        self.anim_frame += 1
        if self.invincible > 0:
            self.invincible -= 1

    def _collide_x(self, level):
        rect = self.rect
        for gy in range(max(0, rect.top // TILE_SIZE), min(level.height, rect.bottom // TILE_SIZE + 1)):
            for gx in range(max(0, rect.left // TILE_SIZE), min(level.width, rect.right // TILE_SIZE + 1)):
                if level.get(gx, gy) in SOLID_TILES:
                    tr = pygame.Rect(gx*TILE_SIZE, gy*TILE_SIZE, TILE_SIZE, TILE_SIZE)
                    if rect.colliderect(tr):
                        if self.vx > 0:
                            self.x = tr.left - self.w
                        elif self.vx < 0:
                            self.x = tr.right
                        self.vx = 0
                        rect = self.rect

    def _collide_y(self, level):
        rect = self.rect
        for gy in range(max(0, rect.top // TILE_SIZE), min(level.height, rect.bottom // TILE_SIZE + 1)):
            for gx in range(max(0, rect.left // TILE_SIZE), min(level.width, rect.right // TILE_SIZE + 1)):
                tile = level.get(gx, gy)
                if tile in SOLID_TILES:
                    tr = pygame.Rect(gx*TILE_SIZE, gy*TILE_SIZE, TILE_SIZE, TILE_SIZE)
                    if rect.colliderect(tr):
                        if self.vy > 0:
                            self.y = tr.top - self.h
                            self.vy = 0
                            self.on_ground = True
                        elif self.vy < 0:
                            self.y = tr.bottom
                            self.vy = 0
                            # Hit block from below
                            if tile == TileType.QUESTION:
                                level.set(gx, gy, TileType.USED_BLOCK)
                                self.coins += 1
                                self.score += 200
                            elif tile == TileType.BRICK:
                                if self.big:
                                    level.set(gx, gy, TileType.EMPTY)
                                    self.score += 50
                        rect = self.rect

    def die(self):
        if self.invincible > 0:
            return
        if self.big:
            self.big = False
            self.invincible = 90
            self.h = 30
            return
        self.alive = False
        self.vy = JUMP_FORCE
        self.lives -= 1

    def draw(self, surface, cam_x):
        sx = int(self.x - cam_x)
        sy = int(self.y)
        if not self.alive:
            # Death animation
            draw_mario(surface, sx, sy, self.facing, False, True)
            return
        if self.invincible > 0 and self.anim_frame % 6 < 3:
            return  # Blink
        draw_mario(surface, sx, sy, self.facing, self.big, False)


def draw_mario(surface, sx, sy, facing, big, dead):
    """Draw Mario sprite procedurally."""
    if dead:
        # Upside down
        pygame.draw.rect(surface, C_RED, (sx+4, sy+16, 16, 8))
        pygame.draw.rect(surface, C_SKIN, (sx+6, sy+8, 12, 10))
        pygame.draw.rect(surface, C_BLUE, (sx+4, sy, 8, 10))
        pygame.draw.rect(surface, C_BLUE, (sx+12, sy, 8, 10))
        return

    h_off = 0
    if big:
        h_off = -20
    # Hat
    hat_w = 16
    pygame.draw.rect(surface, C_RED, (sx+4, sy+h_off, hat_w, 6))
    # Face
    pygame.draw.rect(surface, C_SKIN, (sx+6, sy+6+h_off, 12, 10))
    ex = sx + 10 if facing > 0 else sx + 10
    pygame.draw.circle(surface, C_BLACK, (ex, sy+10+h_off), 1)
    # Mustache
    pygame.draw.line(surface, C_DKBROWN, (sx+8, sy+14+h_off), (sx+16, sy+14+h_off), 1)
    # Body
    body_h = 14 if big else 8
    pygame.draw.rect(surface, C_RED, (sx+4, sy+16+h_off, 16, body_h))
    # Overalls
    ov_y = sy + 20 + h_off if big else sy + 20 + h_off
    pygame.draw.rect(surface, C_BLUE, (sx+4, ov_y, 7, 10))
    pygame.draw.rect(surface, C_BLUE, (sx+13, ov_y, 7, 10))


class Enemy:
    def __init__(self, x, y, etype="goomba"):
        self.x, self.y = float(x), float(y)
        self.vx = -1.5
        self.vy = 0.0
        self.w, self.h = 28, 28
        self.alive = True
        self.etype = etype
        self.squish_timer = 0
        self.anim = 0

    @property
    def rect(self):
        return pygame.Rect(int(self.x), int(self.y), self.w, self.h)

    def update(self, level):
        if not self.alive:
            self.squish_timer -= 1
            return self.squish_timer > 0

        self.vy += GRAVITY
        if self.vy > MAX_FALL:
            self.vy = MAX_FALL

        self.x += self.vx
        # Wall collision
        rect = self.rect
        for gy in range(max(0, rect.top//TILE_SIZE), min(level.height, rect.bottom//TILE_SIZE+1)):
            for gx in range(max(0, rect.left//TILE_SIZE), min(level.width, rect.right//TILE_SIZE+1)):
                if level.get(gx, gy) in SOLID_TILES:
                    tr = pygame.Rect(gx*TILE_SIZE, gy*TILE_SIZE, TILE_SIZE, TILE_SIZE)
                    if rect.colliderect(tr):
                        self.vx *= -1
                        self.x += self.vx * 2
                        break

        self.y += self.vy
        rect = self.rect
        for gy in range(max(0, rect.top//TILE_SIZE), min(level.height, rect.bottom//TILE_SIZE+1)):
            for gx in range(max(0, rect.left//TILE_SIZE), min(level.width, rect.right//TILE_SIZE+1)):
                if level.get(gx, gy) in SOLID_TILES:
                    tr = pygame.Rect(gx*TILE_SIZE, gy*TILE_SIZE, TILE_SIZE, TILE_SIZE)
                    if rect.colliderect(tr):
                        if self.vy > 0:
                            self.y = tr.top - self.h
                            self.vy = 0
                        rect = self.rect

        if self.y > level.height * TILE_SIZE + 100:
            return False

        self.anim += 1
        return True

    def stomp(self):
        self.alive = False
        self.squish_timer = 20

    def draw(self, surface, cam_x, anim_frame):
        sx = int(self.x - cam_x)
        sy = int(self.y)
        if not self.alive:
            # Squished
            pygame.draw.ellipse(surface, C_BROWN if self.etype == "goomba" else C_GREEN,
                                (sx, sy + self.h - 8, self.w, 8))
            return
        if self.etype == "goomba":
            draw_tile(surface, TileType.GOOMBA_SPAWN, sx+2, sy+2, anim_frame)
        else:
            draw_tile(surface, TileType.KOOPA_SPAWN, sx+2, sy+2, anim_frame)


class CoinParticle:
    def __init__(self, x, y):
        self.x, self.y = x, y
        self.vy = -8
        self.timer = 30

    def update(self):
        self.y += self.vy
        self.vy += 0.4
        self.timer -= 1
        return self.timer > 0

    def draw(self, surface, cam_x):
        sx = int(self.x - cam_x)
        pygame.draw.circle(surface, C_GOLD, (sx, int(self.y)), 6)
        pygame.draw.circle(surface, C_YELLOW, (sx, int(self.y)), 4)


# ─── Game State ──────────────────────────────────────────────
class GameState:
    MENU = 0
    PLAYING = 1
    EDITOR = 2
    GAME_OVER = 3
    WIN = 4


# ─── Main Application ───────────────────────────────────────
class UltraMarioForever:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption("Ultra Mario Forever Engine v1.0")
        self.screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
        self.clock = pygame.time.Clock()
        self.state = GameState.MENU
        self.font = pygame.font.SysFont("arial", 24, bold=True)
        self.font_sm = pygame.font.SysFont("arial", 16)
        self.font_lg = pygame.font.SysFont("arial", 48, bold=True)
        self.font_title = pygame.font.SysFont("arial", 56, bold=True)

        self.level = None
        self.player = None
        self.enemies = []
        self.particles = []
        self.cam_x = 0
        self.anim_frame = 0
        self.game_timer = 0

        # Editor state
        self.ed_cam_x = 0
        self.ed_cam_y = 0
        self.ed_selected = TileType.GROUND
        self.ed_show_grid = True
        self.ed_palette_scroll = 0
        self.ed_filename = ""
        self.ed_input_mode = None  # None, "save", "load", "name"
        self.ed_input_text = ""
        self.ed_testing = False

        self.levels_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "levels")
        os.makedirs(self.levels_dir, exist_ok=True)

        # Menu
        self.menu_sel = 0
        self.menu_items = ["Play Level", "Level Editor", "Quit"]

        # Level select
        self.level_files = []
        self.level_sel = 0

    def run(self):
        running = True
        while running:
            dt = self.clock.tick(FPS)
            self.anim_frame += 1

            events = pygame.event.get()
            for ev in events:
                if ev.type == pygame.QUIT:
                    running = False

            if self.state == GameState.MENU:
                self._update_menu(events)
                self._draw_menu()
            elif self.state == GameState.PLAYING:
                self._update_game(events)
                self._draw_game()
            elif self.state == GameState.EDITOR:
                self._update_editor(events)
                self._draw_editor()
            elif self.state == GameState.GAME_OVER:
                self._update_gameover(events)
                self._draw_gameover()
            elif self.state == GameState.WIN:
                self._update_win(events)
                self._draw_win()

            pygame.display.flip()

        pygame.quit()

    # ─── Menu ────────────────────────────────────────────────
    def _update_menu(self, events):
        for ev in events:
            if ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_UP:
                    self.menu_sel = (self.menu_sel - 1) % len(self.menu_items)
                elif ev.key == pygame.K_DOWN:
                    self.menu_sel = (self.menu_sel + 1) % len(self.menu_items)
                elif ev.key in (pygame.K_RETURN, pygame.K_SPACE):
                    if self.menu_sel == 0:
                        self._scan_levels()
                        if self.level_files:
                            self._load_and_play(self.level_files[0])
                        else:
                            # Generate sample level
                            self._generate_sample_level()
                            self._start_game()
                    elif self.menu_sel == 1:
                        self.level = Level(200, 19)
                        self.level.name = "New Level"
                        self.ed_cam_x = 0
                        self.ed_cam_y = 0
                        self.state = GameState.EDITOR
                    elif self.menu_sel == 2:
                        pygame.quit()
                        sys.exit()

    def _draw_menu(self):
        self.screen.fill(C_SKY)
        # Decorative ground
        for gx in range(GRID_W + 1):
            for gy in range(GRID_H - 2, GRID_H):
                draw_tile(self.screen, TileType.GROUND, gx*TILE_SIZE, gy*TILE_SIZE)

        # Decorative clouds
        for i in range(5):
            cx = (i * 170 + self.anim_frame // 3) % (SCREEN_W + 100) - 50
            draw_tile(self.screen, TileType.CLOUD, cx, 40 + i*20)

        # Title
        title = self.font_title.render("ULTRA MARIO", True, C_WHITE)
        title2 = self.font_lg.render("FOREVER", True, C_YELLOW)
        shadow = self.font_title.render("ULTRA MARIO", True, C_BLACK)
        shadow2 = self.font_lg.render("FOREVER", True, C_BLACK)
        self.screen.blit(shadow, (SCREEN_W//2 - shadow.get_width()//2 + 3, 83))
        self.screen.blit(title, (SCREEN_W//2 - title.get_width()//2, 80))
        self.screen.blit(shadow2, (SCREEN_W//2 - shadow2.get_width()//2 + 3, 143))
        self.screen.blit(title2, (SCREEN_W//2 - title2.get_width()//2, 140))

        # Version
        ver = self.font_sm.render("Engine v1.0 — Pygame Edition", True, C_WHITE)
        self.screen.blit(ver, (SCREEN_W//2 - ver.get_width()//2, 195))

        # Menu items
        for i, item in enumerate(self.menu_items):
            color = C_YELLOW if i == self.menu_sel else C_WHITE
            prefix = "▶ " if i == self.menu_sel else "  "
            txt = self.font.render(prefix + item, True, color)
            self.screen.blit(txt, (SCREEN_W//2 - txt.get_width()//2, 280 + i * 50))

        # Footer
        foot = self.font_sm.render("Arrow Keys: Navigate  |  Enter: Select", True, C_WHITE)
        self.screen.blit(foot, (SCREEN_W//2 - foot.get_width()//2, SCREEN_H - 80))

        # Draw Mario
        draw_mario(self.screen, 120, SCREEN_H - 2*TILE_SIZE - 32, 1, False, False)

    # ─── Game ────────────────────────────────────────────────
    def _start_game(self):
        sx, sy = self.level.find_spawn()
        self.player = Player(sx, sy)
        self.enemies = []
        self.particles = []
        self.cam_x = 0
        self.game_timer = self.level.time_limit * FPS // 10

        # Spawn enemies from level
        for gy in range(self.level.height):
            for gx in range(self.level.width):
                t = self.level.get(gx, gy)
                if t == TileType.GOOMBA_SPAWN:
                    self.enemies.append(Enemy(gx*TILE_SIZE+2, gy*TILE_SIZE+4, "goomba"))
                elif t == TileType.KOOPA_SPAWN:
                    self.enemies.append(Enemy(gx*TILE_SIZE+2, gy*TILE_SIZE+2, "koopa"))

        self.state = GameState.PLAYING

    def _update_game(self, events):
        for ev in events:
            if ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_ESCAPE:
                    if self.ed_testing:
                        self.ed_testing = False
                        self.state = GameState.EDITOR
                        return
                    self.state = GameState.MENU
                    return

        if not self.player.alive:
            self.player.update(pygame.key.get_pressed(), self.level)
            if self.player.y > SCREEN_H + 200:
                if self.player.lives > 0:
                    self._start_game()
                else:
                    self.state = GameState.GAME_OVER
            return

        keys = pygame.key.get_pressed()
        self.player.update(keys, self.level)

        # Camera
        target = self.player.x - SCREEN_W // 3
        self.cam_x += (target - self.cam_x) * 0.1
        self.cam_x = max(0, min(self.cam_x, self.level.width * TILE_SIZE - SCREEN_W))

        # Enemies
        self.enemies = [e for e in self.enemies if e.update(self.level)]

        # Player vs enemies
        pr = self.player.rect
        for e in self.enemies:
            if not e.alive:
                continue
            er = e.rect
            if pr.colliderect(er):
                if self.player.vy > 0 and self.player.y + self.player.h - 10 < e.y + e.h//2:
                    e.stomp()
                    self.player.vy = JUMP_FORCE * 0.6
                    self.player.score += 100
                else:
                    self.player.die()

        # Coin collection
        pr = self.player.rect
        for gy in range(max(0, pr.top//TILE_SIZE), min(self.level.height, pr.bottom//TILE_SIZE+1)):
            for gx in range(max(0, pr.left//TILE_SIZE), min(self.level.width, pr.right//TILE_SIZE+1)):
                t = self.level.get(gx, gy)
                if t == TileType.COIN:
                    cr = pygame.Rect(gx*TILE_SIZE, gy*TILE_SIZE, TILE_SIZE, TILE_SIZE)
                    if pr.colliderect(cr):
                        self.level.set(gx, gy, TileType.EMPTY)
                        self.player.coins += 1
                        self.player.score += 100
                        self.particles.append(CoinParticle(gx*TILE_SIZE+16, gy*TILE_SIZE))
                elif t == TileType.MUSHROOM_SPAWN:
                    mr = pygame.Rect(gx*TILE_SIZE, gy*TILE_SIZE, TILE_SIZE, TILE_SIZE)
                    if pr.colliderect(mr):
                        self.level.set(gx, gy, TileType.EMPTY)
                        if not self.player.big:
                            self.player.big = True
                            self.player.h = 50
                            self.player.y -= 20
                        self.player.score += 1000
                elif t == TileType.SPIKE:
                    sr = pygame.Rect(gx*TILE_SIZE+4, gy*TILE_SIZE+8, TILE_SIZE-8, TILE_SIZE-8)
                    if pr.colliderect(sr):
                        self.player.die()
                elif t == TileType.GOAL_POLE:
                    gr = pygame.Rect(gx*TILE_SIZE, gy*TILE_SIZE, TILE_SIZE, TILE_SIZE)
                    if pr.colliderect(gr):
                        self.player.won = True
                        self.player.score += 5000
                        self.state = GameState.WIN

        # Particles
        self.particles = [p for p in self.particles if p.update()]

        # Timer
        self.game_timer -= 1
        if self.game_timer <= 0:
            self.player.die()

    def _draw_game(self):
        self.screen.fill(self.level.bg_color)

        # Draw bg tiles first
        start_gx = max(0, int(self.cam_x // TILE_SIZE) - 1)
        end_gx = min(self.level.width, int((self.cam_x + SCREEN_W) // TILE_SIZE) + 2)

        for gy in range(self.level.height):
            for gx in range(start_gx, end_gx):
                t = self.level.get(gx, gy)
                if t in BG_TILES:
                    px = gx * TILE_SIZE - int(self.cam_x)
                    py = gy * TILE_SIZE
                    draw_tile(self.screen, t, px, py, self.anim_frame)

        # Draw solid tiles and coins
        for gy in range(self.level.height):
            for gx in range(start_gx, end_gx):
                t = self.level.get(gx, gy)
                if t != TileType.EMPTY and t not in BG_TILES and t not in (
                        TileType.GOOMBA_SPAWN, TileType.KOOPA_SPAWN, TileType.PLAYER_SPAWN):
                    px = gx * TILE_SIZE - int(self.cam_x)
                    py = gy * TILE_SIZE
                    draw_tile(self.screen, t, px, py, self.anim_frame)

        # Enemies
        for e in self.enemies:
            e.draw(self.screen, self.cam_x, self.anim_frame)

        # Player
        self.player.draw(self.screen, self.cam_x)

        # Particles
        for p in self.particles:
            p.draw(self.screen, self.cam_x)

        # HUD
        self._draw_hud()

    def _draw_hud(self):
        hud_bg = pygame.Surface((SCREEN_W, 36), pygame.SRCALPHA)
        hud_bg.fill((0, 0, 0, 140))
        self.screen.blit(hud_bg, (0, 0))

        items = [
            f"SCORE: {self.player.score:06d}",
            f"COINS: {self.player.coins}",
            f"LIVES: {self.player.lives}",
            f"TIME: {max(0, self.game_timer // 6)}",
        ]
        x = 10
        for item in items:
            txt = self.font_sm.render(item, True, C_WHITE)
            self.screen.blit(txt, (x, 10))
            x += txt.get_width() + 30

        # Level name
        name = self.font_sm.render(self.level.name, True, C_YELLOW)
        self.screen.blit(name, (SCREEN_W - name.get_width() - 10, 10))

    # ─── Game Over / Win ─────────────────────────────────────
    def _update_gameover(self, events):
        for ev in events:
            if ev.type == pygame.KEYDOWN:
                self.state = GameState.MENU

    def _draw_gameover(self):
        self.screen.fill(C_BLACK)
        txt = self.font_lg.render("GAME OVER", True, C_RED)
        self.screen.blit(txt, (SCREEN_W//2 - txt.get_width()//2, SCREEN_H//2 - 50))
        sc = self.font.render(f"Score: {self.player.score}", True, C_WHITE)
        self.screen.blit(sc, (SCREEN_W//2 - sc.get_width()//2, SCREEN_H//2 + 20))
        hint = self.font_sm.render("Press any key to return to menu", True, C_GRAY)
        self.screen.blit(hint, (SCREEN_W//2 - hint.get_width()//2, SCREEN_H//2 + 70))

    def _update_win(self, events):
        for ev in events:
            if ev.type == pygame.KEYDOWN:
                if self.ed_testing:
                    self.ed_testing = False
                    self.state = GameState.EDITOR
                else:
                    self.state = GameState.MENU

    def _draw_win(self):
        self.screen.fill(C_BLACK)
        txt = self.font_lg.render("LEVEL CLEAR!", True, C_GREEN)
        self.screen.blit(txt, (SCREEN_W//2 - txt.get_width()//2, SCREEN_H//2 - 50))
        sc = self.font.render(f"Score: {self.player.score}", True, C_YELLOW)
        self.screen.blit(sc, (SCREEN_W//2 - sc.get_width()//2, SCREEN_H//2 + 20))
        hint = self.font_sm.render("Press any key to continue", True, C_GRAY)
        self.screen.blit(hint, (SCREEN_W//2 - hint.get_width()//2, SCREEN_H//2 + 70))

    # ─── Editor ──────────────────────────────────────────────
    def _update_editor(self, events):
        if self.ed_input_mode:
            self._update_editor_input(events)
            return

        keys = pygame.key.get_pressed()
        scroll_spd = 8
        if keys[pygame.K_LEFT]:
            self.ed_cam_x -= scroll_spd
        if keys[pygame.K_RIGHT]:
            self.ed_cam_x += scroll_spd
        if keys[pygame.K_UP]:
            self.ed_cam_y -= scroll_spd
        if keys[pygame.K_DOWN]:
            self.ed_cam_y += scroll_spd
        self.ed_cam_x = max(0, min(self.ed_cam_x, self.level.width * TILE_SIZE - SCREEN_W))
        self.ed_cam_y = max(0, min(self.ed_cam_y, self.level.height * TILE_SIZE - SCREEN_H + 80))

        mouse = pygame.mouse.get_pressed()
        mx, my = pygame.mouse.get_pos()

        # Palette area is bottom 80px
        palette_h = 80
        in_canvas = my < SCREEN_H - palette_h

        if in_canvas:
            gx = (mx + int(self.ed_cam_x)) // TILE_SIZE
            gy = (my + int(self.ed_cam_y)) // TILE_SIZE
            if mouse[0]:  # Left click = place
                self.level.set(gx, gy, int(self.ed_selected))
            elif mouse[2]:  # Right click = erase
                self.level.set(gx, gy, TileType.EMPTY)

        for ev in events:
            if ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_ESCAPE:
                    self.state = GameState.MENU
                elif ev.key == pygame.K_TAB:
                    self.ed_show_grid = not self.ed_show_grid
                elif ev.key == pygame.K_p:
                    # Test play
                    self.ed_testing = True
                    self._start_game()
                elif ev.key == pygame.K_s and (keys[pygame.K_LCTRL] or keys[pygame.K_RCTRL]):
                    self.ed_input_mode = "save"
                    self.ed_input_text = self.level.name.replace(" ", "_").lower()
                elif ev.key == pygame.K_l and (keys[pygame.K_LCTRL] or keys[pygame.K_RCTRL]):
                    self.ed_input_mode = "load"
                    self.ed_input_text = ""
                    self._scan_levels()
                elif ev.key == pygame.K_n and (keys[pygame.K_LCTRL] or keys[pygame.K_RCTRL]):
                    self.ed_input_mode = "name"
                    self.ed_input_text = self.level.name
                elif ev.key == pygame.K_PLUS or ev.key == pygame.K_EQUALS:
                    self.level.width = min(500, self.level.width + 10)
                    for row in self.level.tiles:
                        while len(row) < self.level.width:
                            row.append(0)
                elif ev.key == pygame.K_MINUS:
                    self.level.width = max(25, self.level.width - 10)
                    for row in self.level.tiles:
                        while len(row) > self.level.width:
                            row.pop()

            elif ev.type == pygame.MOUSEWHEEL:
                if not in_canvas:
                    self.ed_palette_scroll -= ev.y * 2
                    self.ed_palette_scroll = max(0, self.ed_palette_scroll)
                else:
                    # Scroll through tiles with wheel in canvas
                    tiles = [t for t in TileType if t != TileType.EMPTY]
                    idx = tiles.index(self.ed_selected) if self.ed_selected in tiles else 0
                    idx = (idx + ev.y) % len(tiles)
                    self.ed_selected = tiles[idx]

            elif ev.type == pygame.MOUSEBUTTONDOWN:
                if not in_canvas and ev.button == 1:
                    # Click in palette
                    self._palette_click(mx, my)

    def _update_editor_input(self, events):
        for ev in events:
            if ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_ESCAPE:
                    self.ed_input_mode = None
                elif ev.key == pygame.K_RETURN:
                    if self.ed_input_mode == "save":
                        fname = self.ed_input_text.strip()
                        if fname:
                            if not fname.endswith(".json"):
                                fname += ".json"
                            path = os.path.join(self.levels_dir, fname)
                            self.level.save(path)
                    elif self.ed_input_mode == "load":
                        if self.level_files:
                            idx = min(self.level_sel, len(self.level_files)-1)
                            path = os.path.join(self.levels_dir, self.level_files[idx])
                            try:
                                self.level = Level.load(path)
                            except:
                                pass
                    elif self.ed_input_mode == "name":
                        self.level.name = self.ed_input_text.strip() or "Untitled"
                    self.ed_input_mode = None
                elif ev.key == pygame.K_BACKSPACE:
                    self.ed_input_text = self.ed_input_text[:-1]
                elif ev.key == pygame.K_UP and self.ed_input_mode == "load":
                    self.level_sel = max(0, self.level_sel - 1)
                elif ev.key == pygame.K_DOWN and self.ed_input_mode == "load":
                    self.level_sel = min(len(self.level_files)-1, self.level_sel + 1)
                else:
                    if len(self.ed_input_text) < 40 and ev.unicode.isprintable():
                        self.ed_input_text += ev.unicode

    def _palette_click(self, mx, my):
        palette_y = SCREEN_H - 80
        tiles = [t for t in TileType if t != TileType.EMPTY]
        cols = SCREEN_W // (TILE_SIZE + 4)
        for i, t in enumerate(tiles):
            col = i % cols
            row = i // cols
            px = col * (TILE_SIZE + 4) + 4
            py = palette_y + 8 + row * (TILE_SIZE + 4) - self.ed_palette_scroll
            if px <= mx <= px + TILE_SIZE and py <= my <= py + TILE_SIZE:
                self.ed_selected = t
                break

    def _draw_editor(self):
        self.screen.fill(self.level.bg_color)

        # Draw tiles
        start_gx = max(0, int(self.ed_cam_x // TILE_SIZE))
        end_gx = min(self.level.width, int((self.ed_cam_x + SCREEN_W) // TILE_SIZE) + 2)
        start_gy = max(0, int(self.ed_cam_y // TILE_SIZE))
        end_gy = min(self.level.height, int((self.ed_cam_y + SCREEN_H - 80) // TILE_SIZE) + 2)

        for gy in range(start_gy, end_gy):
            for gx in range(start_gx, end_gx):
                t = self.level.get(gx, gy)
                px = gx * TILE_SIZE - int(self.ed_cam_x)
                py = gy * TILE_SIZE - int(self.ed_cam_y)
                if t != TileType.EMPTY:
                    draw_tile(self.screen, t, px, py, self.anim_frame)

        # Grid
        if self.ed_show_grid:
            for gx in range(start_gx, end_gx + 1):
                px = gx * TILE_SIZE - int(self.ed_cam_x)
                pygame.draw.line(self.screen, (255,255,255,50), (px, 0), (px, SCREEN_H-80), 1)
            for gy in range(start_gy, end_gy + 1):
                py = gy * TILE_SIZE - int(self.ed_cam_y)
                pygame.draw.line(self.screen, (255,255,255,50), (0, py), (SCREEN_W, py), 1)

        # Mouse highlight
        mx, my = pygame.mouse.get_pos()
        if my < SCREEN_H - 80:
            gx = (mx + int(self.ed_cam_x)) // TILE_SIZE
            gy = (my + int(self.ed_cam_y)) // TILE_SIZE
            hx = gx * TILE_SIZE - int(self.ed_cam_x)
            hy = gy * TILE_SIZE - int(self.ed_cam_y)
            highlight = pygame.Surface((TILE_SIZE, TILE_SIZE), pygame.SRCALPHA)
            highlight.fill((255, 255, 255, 60))
            self.screen.blit(highlight, (hx, hy))
            # Preview
            preview = pygame.Surface((TILE_SIZE, TILE_SIZE), pygame.SRCALPHA)
            preview.set_alpha(128)
            draw_tile(preview, self.ed_selected, 0, 0, self.anim_frame)
            self.screen.blit(preview, (hx, hy))

        # Palette background
        palette_y = SCREEN_H - 80
        pygame.draw.rect(self.screen, (30, 30, 50), (0, palette_y, SCREEN_W, 80))
        pygame.draw.line(self.screen, C_WHITE, (0, palette_y), (SCREEN_W, palette_y), 2)

        tiles = [t for t in TileType if t != TileType.EMPTY]
        cols = SCREEN_W // (TILE_SIZE + 4)
        for i, t in enumerate(tiles):
            col = i % cols
            row = i // cols
            px = col * (TILE_SIZE + 4) + 4
            py = palette_y + 8 + row * (TILE_SIZE + 4) - self.ed_palette_scroll
            if palette_y <= py <= SCREEN_H:
                draw_tile(self.screen, t, px, py, self.anim_frame)
                if t == self.ed_selected:
                    pygame.draw.rect(self.screen, C_YELLOW, (px-2, py-2, TILE_SIZE+4, TILE_SIZE+4), 2)

        # Top HUD
        hud = pygame.Surface((SCREEN_W, 30), pygame.SRCALPHA)
        hud.fill((0, 0, 0, 160))
        self.screen.blit(hud, (0, 0))

        sel_name = TILE_NAMES.get(self.ed_selected, "?")
        info = f"Level: {self.level.name}  |  Size: {self.level.width}x{self.level.height}  |  Selected: {sel_name}  |  P=Play  Ctrl+S=Save  Ctrl+L=Load"
        txt = self.font_sm.render(info, True, C_WHITE)
        self.screen.blit(txt, (6, 7))

        # Input dialog
        if self.ed_input_mode:
            self._draw_editor_dialog()

    def _draw_editor_dialog(self):
        # Overlay
        overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        self.screen.blit(overlay, (0, 0))

        bx, by, bw, bh = SCREEN_W//2 - 200, SCREEN_H//2 - 100, 400, 200
        pygame.draw.rect(self.screen, (40, 40, 60), (bx, by, bw, bh), border_radius=8)
        pygame.draw.rect(self.screen, C_WHITE, (bx, by, bw, bh), 2, border_radius=8)

        if self.ed_input_mode == "save":
            title = "Save Level"
            prompt = "Filename:"
            txt = self.font.render(title, True, C_YELLOW)
            self.screen.blit(txt, (bx + bw//2 - txt.get_width()//2, by + 15))
            pt = self.font_sm.render(prompt, True, C_WHITE)
            self.screen.blit(pt, (bx + 20, by + 60))
            # Input box
            pygame.draw.rect(self.screen, C_WHITE, (bx+20, by+85, bw-40, 30), 1)
            it = self.font_sm.render(self.ed_input_text + "_", True, C_WHITE)
            self.screen.blit(it, (bx+25, by+90))
            hint = self.font_sm.render("Enter to save, ESC to cancel", True, C_GRAY)
            self.screen.blit(hint, (bx + bw//2 - hint.get_width()//2, by + 150))

        elif self.ed_input_mode == "load":
            title = "Load Level"
            txt = self.font.render(title, True, C_YELLOW)
            self.screen.blit(txt, (bx + bw//2 - txt.get_width()//2, by + 15))
            if self.level_files:
                for i, f in enumerate(self.level_files[:5]):
                    color = C_YELLOW if i == self.level_sel else C_WHITE
                    prefix = "▶ " if i == self.level_sel else "  "
                    ft = self.font_sm.render(prefix + f, True, color)
                    self.screen.blit(ft, (bx + 20, by + 55 + i * 22))
            else:
                nt = self.font_sm.render("No levels found.", True, C_GRAY)
                self.screen.blit(nt, (bx + 20, by + 60))
            hint = self.font_sm.render("Up/Down to select, Enter to load, ESC cancel", True, C_GRAY)
            self.screen.blit(hint, (bx + bw//2 - hint.get_width()//2, by + 170))

        elif self.ed_input_mode == "name":
            title = "Level Name"
            txt = self.font.render(title, True, C_YELLOW)
            self.screen.blit(txt, (bx + bw//2 - txt.get_width()//2, by + 15))
            pygame.draw.rect(self.screen, C_WHITE, (bx+20, by+65, bw-40, 30), 1)
            it = self.font_sm.render(self.ed_input_text + "_", True, C_WHITE)
            self.screen.blit(it, (bx+25, by+70))
            hint = self.font_sm.render("Enter to confirm, ESC cancel", True, C_GRAY)
            self.screen.blit(hint, (bx + bw//2 - hint.get_width()//2, by + 150))

    def _scan_levels(self):
        self.level_files = []
        if os.path.isdir(self.levels_dir):
            self.level_files = sorted([f for f in os.listdir(self.levels_dir) if f.endswith(".json")])
        self.level_sel = 0

    def _load_and_play(self, filename):
        path = os.path.join(self.levels_dir, filename)
        try:
            self.level = Level.load(path)
            self._start_game()
        except Exception as e:
            print(f"Error loading level: {e}")
            self.state = GameState.MENU

    # ─── Sample Level Generator ──────────────────────────────
    def _generate_sample_level(self):
        """Generate the 'Samsoft Course Pack 1' sample level."""
        lv = Level(200, 19)
        lv.name = "Samsoft Course Pack 1"

        # Ground floor (rows 17-18)
        for gx in range(200):
            # Gaps
            if gx in range(18, 21) or gx in range(42, 46) or gx in range(85, 89) or gx in range(140, 144):
                continue
            lv.set(gx, 17, TileType.GROUND)
            lv.set(gx, 18, TileType.GROUND)

        # Player spawn
        lv.set(3, 16, TileType.PLAYER_SPAWN)

        # Section 1: Intro area (0-30)
        # Bricks and ? blocks
        for gx in [8, 9, 10, 11, 12]:
            lv.set(gx, 13, TileType.BRICK)
        lv.set(10, 13, TileType.QUESTION)  # ? block with coin

        # Coins above bricks
        for gx in [9, 10, 11]:
            lv.set(gx, 11, TileType.COIN)

        # Goombas
        lv.set(14, 16, TileType.GOOMBA_SPAWN)
        lv.set(16, 16, TileType.GOOMBA_SPAWN)

        # Pipe
        lv.set(22, 15, TileType.PIPE_TL)
        lv.set(23, 15, TileType.PIPE_TR)
        lv.set(22, 16, TileType.PIPE_BL)
        lv.set(23, 16, TileType.PIPE_BR)

        # Floating coins over gap
        for gx in [18, 19, 20]:
            lv.set(gx, 14, TileType.COIN)

        # Section 2: Platforming (30-60)
        # Staircase
        for i in range(5):
            for j in range(i+1):
                lv.set(30+i, 16-j, TileType.GROUND)

        # Floating platforms
        for gx in [37, 38, 39]:
            lv.set(gx, 13, TileType.BRICK)
        lv.set(38, 13, TileType.QUESTION)

        # Mushroom
        lv.set(38, 10, TileType.MUSHROOM_SPAWN)

        # Koopa
        lv.set(40, 16, TileType.KOOPA_SPAWN)

        # More bricks
        for gx in range(48, 55):
            lv.set(gx, 13, TileType.BRICK)
        lv.set(50, 13, TileType.QUESTION)
        lv.set(52, 13, TileType.QUESTION)

        # Coins row
        for gx in range(48, 55):
            lv.set(gx, 10, TileType.COIN)

        # Enemies
        lv.set(53, 16, TileType.GOOMBA_SPAWN)
        lv.set(55, 16, TileType.GOOMBA_SPAWN)
        lv.set(57, 16, TileType.GOOMBA_SPAWN)

        # Section 3: Pipes area (60-90)
        # Multiple pipes
        for px, h in [(62, 2), (66, 3), (70, 4), (74, 2)]:
            for dy in range(h):
                gy = 16 - dy
                if dy == 0 and h > 1:
                    lv.set(px, gy, TileType.PIPE_BL)
                    lv.set(px+1, gy, TileType.PIPE_BR)
                elif dy == h - 1:
                    lv.set(px, gy, TileType.PIPE_TL)
                    lv.set(px+1, gy, TileType.PIPE_TR)
                else:
                    lv.set(px, gy, TileType.PIPE_BL)
                    lv.set(px+1, gy, TileType.PIPE_BR)

        # Spikes before gap
        for gx in [82, 83, 84]:
            lv.set(gx, 16, TileType.SPIKE)

        # Coin trail over gap
        for gx in range(85, 89):
            lv.set(gx, 13, TileType.COIN)

        # Section 4: Hard block fortress (90-120)
        # Fortress structure
        for gx in range(95, 105):
            lv.set(gx, 14, TileType.HARD_BLOCK)
        for gx in range(97, 103):
            lv.set(gx, 11, TileType.HARD_BLOCK)
        for gy in range(11, 15):
            lv.set(95, gy, TileType.HARD_BLOCK)
            lv.set(104, gy, TileType.HARD_BLOCK)

        # Coins inside fortress
        for gx in range(97, 103):
            lv.set(gx, 12, TileType.COIN)
            lv.set(gx, 13, TileType.COIN)

        # Enemies around fortress
        lv.set(92, 16, TileType.KOOPA_SPAWN)
        lv.set(106, 16, TileType.GOOMBA_SPAWN)
        lv.set(108, 16, TileType.GOOMBA_SPAWN)

        # ? blocks above fortress
        lv.set(99, 8, TileType.QUESTION)
        lv.set(100, 8, TileType.QUESTION)

        # Section 5: Platforming finale (120-160)
        # Ascending platforms
        for i, gx in enumerate([122, 126, 130, 134]):
            for dx in range(3):
                lv.set(gx+dx, 15-i*2, TileType.BRICK)
            lv.set(gx+1, 14-i*2, TileType.COIN)

        # Moving coin row (high up)
        for gx in range(135, 142):
            lv.set(gx, 7, TileType.COIN)

        # Stairs down
        for i in range(6):
            for j in range(6-i):
                lv.set(148+i, 11+j, TileType.GROUND)

        # More enemies
        lv.set(150, 16, TileType.KOOPA_SPAWN)
        lv.set(155, 16, TileType.GOOMBA_SPAWN)

        # Section 6: Run to goal (160-195)
        # Flat run with enemies
        lv.set(165, 16, TileType.GOOMBA_SPAWN)
        lv.set(168, 16, TileType.GOOMBA_SPAWN)
        lv.set(170, 16, TileType.KOOPA_SPAWN)
        lv.set(173, 16, TileType.GOOMBA_SPAWN)

        # Final staircase to flag
        for i in range(8):
            for j in range(i+1):
                lv.set(180+i, 16-j, TileType.GROUND)

        # Goal pole
        for gy in range(5, 17):
            lv.set(190, gy, TileType.GOAL_POLE)

        # Background decorations
        clouds = [(5, 3), (20, 2), (40, 4), (60, 2), (80, 3), (100, 2),
                  (120, 4), (145, 2), (170, 3), (190, 2)]
        for cx, cy in clouds:
            lv.set(cx, cy, TileType.CLOUD)

        bushes = [(7, 16), (25, 16), (50, 16), (78, 16), (110, 16), (160, 16)]
        for bx, by in bushes:
            lv.set(bx, by, TileType.BUSH)

        hills = [(2, 16), (35, 16), (65, 16), (115, 16), (155, 16)]
        for hx, hy in hills:
            lv.set(hx, hy, TileType.HILL)

        self.level = lv
        # Save it too
        lv.save(os.path.join(self.levels_dir, "samsoft_course_pack_1.json"))


# ─── Entry Point ─────────────────────────────────────────────
if __name__ == "__main__":
    game = UltraMarioForever()
    game.run()
