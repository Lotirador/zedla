import pygame
import sys

# Constants
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 400
FPS = 60
GRAVITY = 0.8

# Animation Metadata (Matching the generated image)
# Format: row_index, number_of_frames
ANIMATION_MAP = {
    "idle": (0, 4),
    "walk": (1, 8),
    "attack": (2, 7),
    "jump": (3, 5)
}

class Player(pygame.sprite.Sprite):
    def __init__(self, sheet_path):
        super().__init__()
        # Load the sheet and setup dimensions
        self.sprite_sheet = pygame.image.load(sheet_path).convert_alpha()
        self.frame_width = self.sprite_sheet.get_width() // 8
        self.frame_height = self.sprite_sheet.get_height() // 4
        
        # State variables
        self.state = "idle"
        self.frame_index = 0
        self.animation_speed = 0.15
        self.image = self.get_frame(0, 0)
        self.rect = self.image.get_rect(midbottom=(100, SCREEN_HEIGHT - 50))
        
        # Movement variables
        self.velocity_y = 0
        self.speed = 5
        self.facing_right = True

    def get_frame(self, row, col):
        """Cuts a specific frame out of the master sheet."""
        rect = pygame.Rect(col * self.frame_width, row * self.frame_height, 
                           self.frame_width, self.frame_height)
        return self.sprite_sheet.subsurface(rect)

    def handle_input(self):
        keys = pygame.key.get_pressed()
        moving = False

        if keys[pygame.K_LEFT]:
            self.rect.x -= self.speed
            self.facing_right = False
            self.state = "walk"
            moving = True
        elif keys[pygame.K_RIGHT]:
            self.rect.x += self.speed
            self.facing_right = True
            self.state = "walk"
            moving = True
        
        if not moving:
            self.state = "idle"

        if keys[pygame.K_SPACE] and self.rect.bottom >= SCREEN_HEIGHT - 50:
            self.velocity_y = -15
            
        if self.rect.bottom < SCREEN_HEIGHT - 50:
            self.state = "jump"

    def apply_gravity(self):
        self.velocity_y += GRAVITY
        self.rect.y += self.velocity_y
        if self.rect.bottom > SCREEN_HEIGHT - 50:
            self.rect.bottom = SCREEN_HEIGHT - 50

    def animate(self):
        row, max_frames = ANIMATION_MAP[self.state]
        self.frame_index += self.animation_speed
        
        if self.frame_index >= max_frames:
            self.frame_index = 0
            
        # Get frame and flip if facing left
        image = self.get_frame(row, int(self.frame_index))
        if not self.facing_right:
            image = pygame.transform.flip(image, True, False)
        
        self.image = image

    def update(self):
        self.handle_input()
        self.apply_gravity()
        self.animate()

# Initialize Pygame
pygame.init()
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
clock = pygame.time.Clock()

# Setup Player
# Save the sprite sheet from the previous message as 'knight.png'
try:
    player = Player('knight.png')
    player_group = pygame.sprite.GroupSingle(player)
except:
    print("Error: Please ensure 'knight.png' is in the folder.")
    pygame.quit()
    sys.exit()

# Main Loop
while True:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()

    screen.fill((50, 50, 50)) # Dark background
    pygame.draw.rect(screen, (100, 100, 100), (0, SCREEN_HEIGHT-50, SCREEN_WIDTH, 50)) # Floor
    
    player_group.update()
    player_group.draw(screen)
    
    pygame.display.update()
    clock.tick(FPS)