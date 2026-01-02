import pygame
import sys

# --- Configuration ---
SCREEN_WIDTH = 1000
SCREEN_HEIGHT = 850
FPS = 60
GRAVITY = 0.8

# Animation Map: (Row Index, Number of Frames)
PLAYER_ANIM_MAP = {
    "idle": (0, 4),
    "walk": (1, 8),
    "attack": (2, 6),
    "jump": (3, 5)
}

PXO=5
PX=175
PYO=3
PY=155

MONSTER_ANIM_MAP = {
    "idle": (0, 4),
    "walk": (1, 7),
    "attack": (2, 5),
}

MXO=0
MX=1200//7-1
MYO=2
MY=462//3-1

background = "background.png"

class Entity(pygame.sprite.Sprite):
    """Base class for Player and Enemy to share animation logic."""
    def __init__(self, sheet_path,animation_map,amxo,amx,amyo,amy, pos):
        super().__init__()
        self.sprite_sheet = pygame.image.load(sheet_path).convert_alpha()
        self.frame_width = amx  
        self.frame_height = amy
        self.state = "idle"
        self.frame_index = 0
        self.animation_speed = 0.15
        self.facing_right = True
        self.velocity_y = 0
        self.animation_map = animation_map
        self.amxo = amxo
        self.amyo = amyo
        self.image = self.get_frame(0, 0)
        self.rect = self.image.get_rect(midbottom=pos)

    def get_frame(self, row, col):
        x = self.amxo + col * self.frame_width
        y = self.amyo + row * self.frame_height
        rect = pygame.Rect(x, y, self.frame_width, self.frame_height)
        try:
            return self.sprite_sheet.subsurface(rect)
        except ValueError:
            print(f"Invalid subsurface rect: {rect}")
            return pygame.Surface((self.frame_width, self.frame_height), pygame.SRCALPHA)

    def animate(self):
        row, max_frames = self.animation_map[self.state]
        self.frame_index += self.animation_speed
        if self.frame_index >= max_frames:
            self.frame_index = 0
        
        new_image = self.get_frame(row, int(self.frame_index))
        if not self.facing_right:
            new_image = pygame.transform.flip(new_image, True, False)
        self.image = new_image

class Enemy(Entity):
    def __init__(self, sheet_path, animation_map,xo,x,yo,y, pos):
        super().__init__(sheet_path, animation_map,xo,x,yo,y, pos)
        self.speed = 2
        self.move_range = 300
        self.start_x = pos[0]
        self.state = "walk"

    def update(self):
        # Simple AI: Patrol back and forth
        if self.facing_right:
            self.rect.x += self.speed
            if self.rect.x > self.start_x + self.move_range:
                self.facing_right = False
        else:
            self.rect.x -= self.speed
            if self.rect.x < self.start_x - self.move_range:
                self.facing_right = True
        
        self.animate()

class Player(Entity):
    def __init__(self, sheet_path, animation_map,xo,x,yo,y, pos):
        super().__init__(sheet_path, animation_map,xo,x,yo,y, pos)
        self.speed = 7
        self.is_jumping = False
        self.is_attacking = False

    def handle_input(self):
        keys = pygame.key.get_pressed()
        moving = False
        if keys[pygame.K_LEFT]:
            self.rect.x -= self.speed
            self.facing_right = False
            moving = True
        elif keys[pygame.K_RIGHT]:
            self.rect.x += self.speed
            self.facing_right = True
            moving = True
        
        if keys[pygame.K_SPACE] and not self.is_jumping:
            self.velocity_y = -18
            self.is_jumping = True

        self.is_attacking = keys[pygame.K_a]

        if self.is_jumping: self.state = "jump"
        elif self.is_attacking: self.state = "attack"
        elif moving: self.state = "walk"
        else: self.state = "idle"

    def apply_physics(self):
        self.velocity_y += GRAVITY
        self.rect.y += self.velocity_y
        floor_y = SCREEN_HEIGHT - 40
        if self.rect.bottom > floor_y:
            self.rect.bottom = floor_y
            self.velocity_y = 0
            self.is_jumping = False

    def update(self):
        self.handle_input()
        self.apply_physics()
        self.animate()

def main():
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    clock = pygame.time.Clock()

    # Load Background (Optional: replace with an image load)
    if background:
        bg_surface = pygame.image.load(background).convert()
    
    player = Player('knight.png', PLAYER_ANIM_MAP, PXO, PX, PYO, PY, (200, SCREEN_HEIGHT ))
    enemy = Enemy('monster.png', MONSTER_ANIM_MAP, MXO, MX, MYO, MY, (SCREEN_WIDTH - 400, SCREEN_HEIGHT - 40))
    
    player_group = pygame.sprite.GroupSingle(player)
    enemies = pygame.sprite.Group(enemy)

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

        # Update
        player_group.update()
        enemies.update()

        # Draw
        screen.fill((20, 20, 40)) # Dark night sky
        
        # Draw a simple mountain background (Parallax effect can be added here)
        if background:
            screen.blit(bg_surface, (0, 0))
        else :
            pygame.draw.polygon(screen, (40, 40, 60), [(0, 750), (400, 200), (800, 750)])
            pygame.draw.polygon(screen, (35, 35, 55), [(600, 750), (1000, 300), (1400, 750)])
            pygame.draw.rect(screen, (30, 50, 30), (0, SCREEN_HEIGHT-40, SCREEN_WIDTH, 40)) 
        
        # Draw sprites
        player_group.draw(screen)
        enemies.draw(screen)

        pygame.display.flip()
        clock.tick(FPS)

if __name__ == "__main__":
    main()