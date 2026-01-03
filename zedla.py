import pygame
import sys
import ollama  # pip install ollama
import textwrap  # For wrapping long lines

# --- Configuration ---
SCREEN_WIDTH = 1000
SCREEN_HEIGHT = 850
FPS = 60
GRAVITY = 0.8
GROUND_LEVEL_OFFSET = 40 

# Animation Maps (Row, Frames)
PLAYER_ANIM_MAP = {"idle": (0, 4), "walk": (1, 8), "attack": (2, 6), "jump": (3, 5)}
PXO, PX, PYO, PY = 5, 175, 3, 155

MONSTER_ANIM_MAP = {"idle": (0, 4), "walk": (1, 7), "attack": (2, 5)}
MXO, MX, MYO, MY = 0, 171, 2, 153 

# Chat configuration
CHAT_DISTANCE = 200
PRESS_KEY_DISTANCE = 220
INPUT_BOX_HEIGHT = 50
CHAT_HISTORY_LINES = 10
CHAT_BOX_WIDTH = SCREEN_WIDTH - 180  # Approx inner width for text wrapping
MONSTER_MODEL = "phi3:mini"

class ParallaxLayer:
    def __init__(self, image_path, speed_ratio, is_ground=False):
        raw_image = pygame.image.load(image_path).convert_alpha()
        
        if is_ground:
            self.image = pygame.transform.scale(raw_image, (SCREEN_WIDTH, 100))
            self.y_pos = SCREEN_HEIGHT - 100
        else:
            ratio = SCREEN_HEIGHT / raw_image.get_height()
            new_width = int(raw_image.get_width() * ratio)
            self.image = pygame.transform.scale(raw_image, (max(new_width, SCREEN_WIDTH), SCREEN_HEIGHT))
            self.y_pos = 0

        self.speed_ratio = speed_ratio
        self.width = self.image.get_width()
        self.x = 0

    def draw(self, screen, scroll_movement):
        self.x -= scroll_movement * self.speed_ratio
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
        self.is_chatting = False

    def update(self, scroll_speed):
        self.world_x -= scroll_speed
        
        if not self.is_chatting:
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

def is_facing_player(player, enemy):
    dx = enemy.rect.centerx - player.rect.centerx
    direction_to_enemy = 1 if dx > 0 else -1
    return player.facing_right == (direction_to_enemy > 0)

def generate_monster_response(player_input, history):
    context = "\n".join(history[-8:])
    prompt = f"""You are a grumpy but talkative monster in a 2D platformer game.
You speak in short, monster-like sentences (use words like 'grrr', 'human!', etc.).
Keep your reply to 1-2 short sentences only.

Previous conversation:
{context}

Player says: {player_input}

Monster replies (one or two short sentences only):"""
    
    response = ollama.generate(model=MONSTER_MODEL, prompt=prompt)
    raw_reply = response['response'].strip()
    # Force short response by taking first sentence(s)
    lines = raw_reply.split('\n')
    short_reply = ' '.join(lines[:2])  # At most 2 lines from LLM
    return short_reply

def wrap_text(text, font, max_width):
    """Wrap text into list of lines that fit within max_width"""
    words = text.split(' ')
    wrapped_lines = []
    current_line = ""
    for word in words:
        test_line = current_line + word + " "
        if font.size(test_line)[0] <= max_width:
            current_line = test_line
        else:
            wrapped_lines.append(current_line.strip())
            current_line = word + " "
    if current_line:
        wrapped_lines.append(current_line.strip())
    return wrapped_lines

def main():
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    clock = pygame.time.Clock()
    font = pygame.font.SysFont(None, 32)
    big_font = pygame.font.SysFont(None, 48)

    # Setup layers
    bg_layer = ParallaxLayer("background.png", 0.25)
    try:
        ground_layer = ParallaxLayer("ground.png", 1.0, is_ground=True)
    except:
        ground_layer = None
        print("Warning: ground.png not found.")

    player = Player('knight.png', PLAYER_ANIM_MAP, PXO, PX, PYO, PY, (SCREEN_WIDTH // 2, SCREEN_HEIGHT - GROUND_LEVEL_OFFSET))
    enemy = Enemy('monster.png', MONSTER_ANIM_MAP, MXO, MX, MYO, MY, (1200, SCREEN_HEIGHT - GROUND_LEVEL_OFFSET))
    
    player_group = pygame.sprite.GroupSingle(player)
    enemies = pygame.sprite.Group(enemy)

    # Chat state
    in_chat = False
    user_text = ""
    chat_history = []
    waiting_for_llm = False
    show_press_z = False

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    pygame.quit(); sys.exit()
                
                if event.key == pygame.K_z and show_press_z and not in_chat:
                    in_chat = True
                    user_text = ""
                    chat_history = ["Monster: Grrr... you dare speak to me, human?"]
                    enemy.is_chatting = True
                    enemy.state = "idle"

                if in_chat:
                    if event.key == pygame.K_RETURN:
                        if user_text.strip():
                            chat_history.append(f"Player: {user_text}")
                            waiting_for_llm = True
                            user_text = ""
                    elif event.key == pygame.K_BACKSPACE:
                        user_text = user_text[:-1]
                    else:
                        user_text += event.unicode

        player_group.update()
        scroll = player.current_scroll
        enemies.update(scroll)

        # Proximity checks
        dist = abs(player.rect.centerx - enemy.rect.centerx)
        facing = is_facing_player(player, enemy)
        near_enough_for_prompt = dist < PRESS_KEY_DISTANCE
        in_range_for_chat = dist < CHAT_DISTANCE

        show_press_z = near_enough_for_prompt and facing and not in_chat

        if in_chat and (not in_range_for_chat or not facing):
            in_chat = False
            chat_history = []
            waiting_for_llm = False
            enemy.is_chatting = False
            enemy.state = "walk"

        # Generate response (only once after player sends message)
        if waiting_for_llm:
            monster_reply = generate_monster_response(chat_history[-1][7:], chat_history)
            chat_history.append(f"Monster: {monster_reply}")
            waiting_for_llm = False

        # Drawing
        screen.fill((30, 30, 50))
        bg_layer.draw(screen, scroll)
        if ground_layer:
            ground_layer.draw(screen, scroll)
        else:
            pygame.draw.rect(screen, (40, 60, 40), (0, SCREEN_HEIGHT - GROUND_LEVEL_OFFSET, SCREEN_WIDTH, GROUND_LEVEL_OFFSET))
        
        player_group.draw(screen)
        enemies.draw(screen)

        # "Press Z to talk" prompt
        if show_press_z:
            prompt_text = big_font.render("Press Z to talk", True, (255, 255, 100))
            prompt_rect = prompt_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT - 200))
            bg_rect = prompt_rect.inflate(40, 20)
            pygame.draw.rect(screen, (0, 0, 0, 180), bg_rect)
            screen.blit(prompt_text, prompt_rect)

        # Chat UI
        if in_chat:
            chat_bg = pygame.Surface((SCREEN_WIDTH - 100, 300))
            chat_bg.set_alpha(200)
            chat_bg.fill((0, 0, 0))
            screen.blit(chat_bg, (50, 50))

            # Display chat history with proper line wrapping
            y_offset = 70
            for line in chat_history[-CHAT_HISTORY_LINES:]:
                prefix = "Player: " if line.startswith("Player:") else "Monster: "
                message = line[len(prefix):] if line.startswith(("Player:", "Monster:")) else line
                color = (200, 255, 200) if line.startswith("Player:") else (255, 200, 200)
                
                # Speaker prefix
                prefix_surf = font.render(prefix, True, color)
                screen.blit(prefix_surf, (70, y_offset))
                
                # Wrapped message text
                wrapped_lines = wrap_text(message, font, CHAT_BOX_WIDTH - 20)
                for wrapped_line in wrapped_lines:
                    text_surf = font.render(wrapped_line, True, color)
                    screen.blit(text_surf, (70 + font.size(prefix + " ")[0], y_offset))
                    y_offset += 30
                y_offset += 10  # Small gap between messages

            # Input box
            cursor = "_" if (pygame.time.get_ticks() // 500) % 2 == 0 else ""
            input_surf = font.render(user_text + cursor, True, (255, 255, 255))
            pygame.draw.rect(screen, (50, 50, 50), (50, SCREEN_HEIGHT - INPUT_BOX_HEIGHT - 50, SCREEN_WIDTH - 100, INPUT_BOX_HEIGHT))
            screen.blit(input_surf, (70, SCREEN_HEIGHT - INPUT_BOX_HEIGHT - 40))

            instr = font.render("Type your message and press ENTER • Walk away to end chat", True, (150, 150, 150))
            screen.blit(instr, (70, SCREEN_HEIGHT - INPUT_BOX_HEIGHT - 80))

        pygame.display.flip()
        clock.tick(FPS)

if __name__ == "__main__":
    main()