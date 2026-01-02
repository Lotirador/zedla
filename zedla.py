import pygame
import sys

# --- Configuration ---
SCREEN_WIDTH = 1000
SCREEN_HEIGHT = 850
FPS = 60
GRAVITY = 0.8
# The height from the bottom where the character actually stands
GROUND_LEVEL_OFFSET = 40 

# Animation Maps (Row, Frames)
PLAYER_ANIM_MAP = {"idle": (0, 4), "walk": (1, 8), "attack": (2, 6), "jump": (3, 5)}
PXO, PX, PYO, PY = 5, 175, 3, 155

MONSTER_ANIM_MAP = {"idle": (0, 4), "walk": (1, 7), "attack": (2, 5)}
MXO, MX, MYO, MY = 0, 171, 2, 153 

class ParallaxLayer:
    def __init__(self, image_path, speed_ratio, is_ground=False):
        raw_image = pygame.image.load(image_path).convert_alpha()
        
        if is_ground:
            # Scale ground to a specific height (e.g., 100px) and fit screen width
            self.image = pygame.transform.scale(raw_image, (SCREEN_WIDTH, 100))
            self.y_pos = SCREEN_HEIGHT - 100
        else:
            # Scale background to cover full screen height
            ratio = SCREEN_HEIGHT / raw_image.get_height()
            new_width = int(raw_image.get_width() * ratio)
            self.image = pygame.transform.scale(raw_image, (max(new_width, SCREEN_WIDTH), SCREEN_HEIGHT))
            self.y_pos = 0

        self.speed_ratio = speed_ratio
        self.width = self.image.get_width()
        self.x = 0

    def draw(self, screen, scroll_movement):
        self.x -= scroll_movement * self.speed_ratio
        # Wrap around
        if self.x <= -self.width: self.x += self.width
        if self.x > 0: self.x -= self.width
        
        screen.blit(self.image, (self.x, self.y_pos))
        screen.blit(self.image, (self.x + self.width, self.y_pos))

class Entity(pygame.sprite.Sprite):
    def __init__(self, sheet_path, animation_map, amxo, amx, amyo, amy, pos):
        super().__init__()
        self.sprite_sheet = pygame.image.load(sheet_path).convert_alpha()
        self.frame_width, self.frame_height = amx, amy
        self.state, self.frame_index = "idle", 0
        self.animation_speed = 0.15
        self.facing_right = True
        self.velocity_y = 0
        self.animation_map = animation_map
        self.amxo, self.amyo = amxo, amyo
        self.image = self.get_frame(0, 0)
        self.rect = self.image.get_rect(midbottom=pos)

    def get_frame(self, row, col):
        x, y = self.amxo + col * self.frame_width, self.amyo + row * self.frame_height
        return self.sprite_sheet.subsurface(pygame.Rect(x, y, self.frame_width, self.frame_height))

    def animate(self):
        row, max_frames = self.animation_map[self.state]
        self.frame_index = (self.frame_index + self.animation_speed) % max_frames
        new_image = self.get_frame(row, int(self.frame_index))
        if not self.facing_right: new_image = pygame.transform.flip(new_image, True, False)
        self.image = new_image

class Enemy(Entity):
    def __init__(self, sheet_path, animation_map, xo, x, yo, y, pos):
        super().__init__(sheet_path, animation_map, xo, x, yo, y, pos)
        self.speed = 2
        self.world_x = pos[0]
        self.patrol_timer = 0
        self.state = "walk"

    def update(self, scroll_speed):
        self.world_x -= scroll_speed
        if self.facing_right:
            self.world_x += self.speed
            self.patrol_timer += self.speed
            if self.patrol_timer > 300: self.facing_right = False
        else:
            self.world_x -= self.speed
            self.patrol_timer -= self.speed
            if self.patrol_timer < -300: self.facing_right = True
        self.rect.x = self.world_x
        self.animate()

class Player(Entity):
    def __init__(self, sheet_path, animation_map, xo, x, yo, y, pos):
        super().__init__(sheet_path, animation_map, xo, x, yo, y, pos)
        self.speed = 7
        self.is_jumping = False
        self.is_attacking = False
        self.current_scroll = 0

    def handle_input(self):
        keys = pygame.key.get_pressed()
        self.current_scroll = 0
        moving = False

        if keys[pygame.K_RIGHT]:
            self.current_scroll = self.speed
            self.facing_right, moving = True, True
        elif keys[pygame.K_LEFT]:
            self.current_scroll = -self.speed
            self.facing_right, moving = False, True
        
        if keys[pygame.K_SPACE] and not self.is_jumping:
            self.velocity_y = -18
            self.is_jumping = True

        self.is_attacking = keys[pygame.K_a]

        self.velocity_y += GRAVITY
        self.rect.y += self.velocity_y
        
        floor_y = SCREEN_HEIGHT - GROUND_LEVEL_OFFSET
        if self.rect.bottom > floor_y:
            self.rect.bottom, self.velocity_y, self.is_jumping = floor_y, 0, False

        if self.is_jumping: self.state = "jump"
        elif self.is_attacking: self.state = "attack"
        elif moving: self.state = "walk"
        else: self.state = "idle"

    def update(self):
        self.handle_input()
        self.animate()

def main():
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    clock = pygame.time.Clock()

    # --- SETUP LAYERS ---
    # Background (Moves slow)
    bg_layer = ParallaxLayer("background.png", 0.25)
    # Ground (Moves at 1.0 speed, same as player movement)
    # Ensure you have a 'ground.png' file in the folder!
    try:
        ground_layer = ParallaxLayer("ground.png", 1.0, is_ground=True)
    except:
        # Fallback if ground.png is missing
        ground_layer = None
        print("Warning: ground.png not found. Using solid color.")

    player = Player('knight.png', PLAYER_ANIM_MAP, PXO, PX, PYO, PY, (SCREEN_WIDTH // 2, SCREEN_HEIGHT - GROUND_LEVEL_OFFSET))
    enemy = Enemy('monster.png', MONSTER_ANIM_MAP, MXO, MX, MYO, MY, (1200, SCREEN_HEIGHT - GROUND_LEVEL_OFFSET))
    
    player_group = pygame.sprite.GroupSingle(player)
    enemies = pygame.sprite.Group(enemy)

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    pygame.quit(); sys.exit()

        player_group.update()
        scroll = player.current_scroll
        enemies.update(scroll)

        screen.fill((30, 30, 50))
        
        # 1. Background
        bg_layer.draw(screen, scroll)
        
        # 2. Ground
        if ground_layer:
            ground_layer.draw(screen, scroll)
        else:
            pygame.draw.rect(screen, (40, 60, 40), (0, SCREEN_HEIGHT - GROUND_LEVEL_OFFSET, SCREEN_WIDTH, GROUND_LEVEL_OFFSET))
        
        # 3. Entities
        player_group.draw(screen)
        enemies.draw(screen)

        pygame.display.flip()
        clock.tick(FPS)

if __name__ == "__main__":
    main()