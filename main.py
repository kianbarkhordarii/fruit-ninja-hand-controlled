import pygame
import sys
import random
import cv2
import numpy as np

# Modules
from audio_manager import AudioManager
from input_manager import MouseInput, HandInput
from ui_manager import SceneManager
from game_engine import ClassicMode, SurvivalMode
from game_objects import Blade, Fruit, Bomb, SlicedFruit, Explosion, SplashEffect
from menu_cursor import MenuCursor

# Colors
WHITE = (255, 255, 255)

# Config
WIDTH, HEIGHT = 800, 600 # Keeping larger window for menu usability
FPS = 60
MIN_CUT_VELOCITY = 150 # Rescaled 

def run_game(screen, shared_camera=None, audio=None):
    """
    Runs the Fruit Ninja game loop.

    screen        : the pygame display surface
    shared_camera : an optional pre-opened camera. If None, the game opens
                    its own webcam when hand input is used.
    audio         : an AudioManager (created locally if None)

    Returns "QUIT" when the player closes the game.
    """
    clock = pygame.time.Clock()

    # Systems
    if audio is None:
        audio = AudioManager()
    ui = SceneManager(WIDTH, HEIGHT)

    # Hand input for navigating the menus with a finger.
    try:
        menu_hand = HandInput(WIDTH, HEIGHT, shared_camera=shared_camera)
    except Exception as e:
        print(f"Could not start camera for menu navigation: {e}")
        menu_hand = None
    menu_cursor = MenuCursor(dwell_time=1.0)


    # Load Background
    try:
        bg_raw = pygame.image.load("assets/background/game_background.jpg").convert()
        bg_img = pygame.transform.scale(bg_raw, (WIDTH, HEIGHT))
        # Darken it
        dark = pygame.Surface((WIDTH, HEIGHT))
        dark.set_alpha(80) # 30% dark
        dark.fill((0, 0, 0))
        bg_img.blit(dark, (0,0))
    except Exception as e:
        print(f"Background load error: {e}")
        bg_img = pygame.Surface((WIDTH, HEIGHT))
        bg_img.fill((50, 50, 50))

    # Game State Variables
    input_provider = None
    game_mode = None
    blade = Blade()
    
    all_sprites = pygame.sprite.Group()
    fruits = pygame.sprite.Group() # Only active fruits (not slices or bombs)
    
    # VFX State
    shake_timer = 0
    
    # Start Music
    audio.play_music("menu")
    
    # Which scenes are "menu" scenes navigated by the hand cursor
    MENU_SCENES = ("MENU", "MODE_SEL", "INPUT_SEL", "OVER")

    exit_reason = "QUIT"
    running = True
    while running:
        mx, my = pygame.mouse.get_pos()
        click = False

        # --- Hand cursor position for menus ---
        # Read the hand ONLY on menu scenes. During gameplay the game reads the
        # camera itself, so reading here too would call get_input twice a frame.
        on_menu = ui.current_scene in MENU_SCENES or (
            ui.current_scene == "GAME" and ui.is_paused
        )
        hand_x, hand_y = None, None
        if on_menu and menu_hand is not None:
            try:
                hx, hy, _hvel, _hpaused = menu_hand.get_input()
                hand_x, hand_y = hx, hy
            except Exception:
                hand_x, hand_y = None, None
        menu_cursor.update_position(hand_x, hand_y)
        
        # Shake Logic
        shake_x, shake_y = 0, 0
        if shake_timer > 0:
            shake_timer -= 1
            shake_x = random.randint(-5, 5)
            shake_y = random.randint(-5, 5)

        # Event Loop
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                exit_reason = "QUIT"
                running = False
            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    click = True
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE and ui.current_scene == "GAME":
                    ui.is_paused = not ui.is_paused
                # Q anywhere -> quit
                elif event.key == pygame.K_q:
                    exit_reason = "QUIT"
                    running = False


        # --- SCENE LOGIC ---
        
        if ui.current_scene == "MENU":
            screen.blit(bg_img, (0,0))
            action = menu_cursor.process(ui.get_buttons("MENU"))
            ui.draw_menu(screen)
            menu_cursor.draw(screen)
            if action == "GOTO_MODE":
                ui.push_scene("MODE_SEL")
                audio.play_sfx("start")

        elif ui.current_scene == "MODE_SEL":
            screen.blit(bg_img, (0,0))
            action = menu_cursor.process(ui.get_buttons("MODE_SEL"))
            ui.draw_mode_select(screen)
            menu_cursor.draw(screen)
            
            if action == "MODE_CLASSIC":
                game_mode = ClassicMode()
                ui.push_scene("INPUT_SEL")
                audio.play_sfx("start")
            elif action == "MODE_SURVIVAL":
                game_mode = SurvivalMode()
                ui.push_scene("INPUT_SEL")
                audio.play_sfx("start")
            elif action == "BACK":
                ui.pop_scene()
                audio.play_sfx("start")
                
        elif ui.current_scene == "INPUT_SEL":
            screen.blit(bg_img, (0,0))
            action = menu_cursor.process(ui.get_buttons("INPUT_SEL"))
            ui.draw_input_select(screen)
            menu_cursor.draw(screen)
            
            if action:
                if action == "INPUT_MOUSE":
                    input_provider = MouseInput(WIDTH, HEIGHT)
                    ui.push_scene("GAME")
                    audio.play_music("game_slow")
                    all_sprites.empty()
                    fruits.empty()
                    blade = Blade()
                elif action == "INPUT_HAND":
                    # Reuse the already-open menu camera for gameplay
                    input_provider = menu_hand
                    ui.push_scene("GAME")
                    audio.play_music("game_slow")
                    all_sprites.empty()
                    fruits.empty()
                    blade = Blade()
                elif action == "BACK":
                    ui.pop_scene()
                    audio.play_sfx("start")

        elif ui.current_scene == "GAME":
            # Check if paused
            if ui.is_paused:
                # Draw game state frozen
                if hasattr(input_provider, 'get_frame'):
                    frame = input_provider.get_frame()
                    if frame is not None:
                        img_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                        img_rgb = np.rot90(img_rgb)
                        surf = pygame.surfarray.make_surface(img_rgb)
                        surf = pygame.transform.flip(surf, True, False)
                        screen.blit(pygame.transform.scale(surf, (WIDTH, HEIGHT)), (0,0))
                        screen.blit(bg_img, (0,0), special_flags=pygame.BLEND_MULT)
                    else:
                        screen.blit(bg_img, (0,0))
                else:
                    screen.blit(bg_img, (shake_x, shake_y))
                
                all_sprites.draw(screen)
                blade.draw(screen)
                
                # HUD
                hud = ui.font_small.render(game_mode.get_status(), True, WHITE)
                screen.blit(hud, (20, 20))
                
                # Pause menu (hand cursor)
                action = menu_cursor.process(ui.get_buttons("PAUSE"))
                ui.draw_pause(screen)
                menu_cursor.draw(screen)
                
                if action == "RESUME":
                    ui.is_paused = False
                    audio.play_sfx("start")
                elif action == "BACK":
                    ui.is_paused = False
                    # Only clean up if it's a separate provider (e.g. mouse).
                    # The shared menu camera must stay open for menu navigation.
                    if input_provider and input_provider is not menu_hand:
                        input_provider.cleanup()
                    input_provider = None
                    ui.pop_scene()
                    audio.play_music("menu")
            else:
                # Normal gameplay
                ix, iy, velocity, input_paused = input_provider.get_input()
                
                # Draw Background
                if hasattr(input_provider, 'get_frame'):
                    frame = input_provider.get_frame()
                    if frame is not None:
                        img_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                        img_rgb = np.rot90(img_rgb)
                        surf = pygame.surfarray.make_surface(img_rgb)
                        surf = pygame.transform.flip(surf, True, False)
                        screen.blit(pygame.transform.scale(surf, (WIDTH, HEIGHT)), (0,0))
                        screen.blit(bg_img, (0,0), special_flags=pygame.BLEND_MULT)
                    else:
                        screen.blit(bg_img, (0,0))
                else:
                    screen.blit(bg_img, (shake_x, shake_y))
                
                # Update Logic (only if not palm-paused)
                if not input_paused:
                    if ix is not None:
                        blade.update(ix, iy)
                    
                    # Spawner
                    if random.randint(1, 40) == 1:
                        spawn_x = random.randint(100, WIDTH-100)
                        spawn_y = HEIGHT + 20
                        
                        if random.randint(1, 5) == 1:
                            b = Bomb(spawn_x, spawn_y, WIDTH, HEIGHT)
                            all_sprites.add(b)
                            fruits.add(b)
                        else:
                            f = Fruit(spawn_x, spawn_y, WIDTH, HEIGHT)
                            all_sprites.add(f)
                            fruits.add(f)
                    
                    all_sprites.update()
                    
                    # Collisions
                    segments = blade.get_segments()
                    if velocity > MIN_CUT_VELOCITY and segments:
                        hit_count = 0
                        for entity in list(fruits):
                            if entity.check_slice(segments):
                                hit_count += 1
                                
                                if isinstance(entity, Bomb):
                                    audio.play_sfx("bomb")
                                    boom = Explosion(entity.pos_x, entity.pos_y)
                                    all_sprites.add(boom)
                                    entity.kill()
                                    game_mode.on_bomb()
                                    shake_timer = 20
                                else:
                                    audio.play_sfx("splat")
                                    pts = game_mode.on_slice(entity)
                                    
                                    splash = SplashEffect(entity.pos_x, entity.pos_y, entity.fruit_type, velocity)
                                    all_sprites.add(splash)
                                    
                                    h1 = SlicedFruit(entity.pos_x, entity.pos_y, entity.fruit_type, 1)
                                    h2 = SlicedFruit(entity.pos_x, entity.pos_y, entity.fruit_type, 2)
                                    all_sprites.add(h1)
                                    all_sprites.add(h2)
                                    entity.kill()
                        
                        if hit_count > 1:
                            audio.play_sfx("combo")

                    # Check dropped fruits
                    for entity in list(fruits):
                        if entity.rect.top > HEIGHT:
                            if not isinstance(entity, Bomb):
                                game_mode.on_miss()
                                entity.kill()
                            else:
                                entity.kill()

                    # Check Game Over
                    if game_mode.game_over:
                        ui.current_scene = "OVER"
                        audio.play_sfx("over")
                        audio.stop_music()
                
                # Draw Game
                all_sprites.draw(screen)
                blade.draw(screen)
                
                # Palm pause indicator
                if input_paused:
                    txt = ui.font_big.render("PALM PAUSE", True, (255, 255, 0))
                    screen.blit(txt, (WIDTH//2 - txt.get_width()//2, HEIGHT//2))
                
                # HUD
                hud = ui.font_small.render(game_mode.get_status(), True, WHITE)
                screen.blit(hud, (20, 20))
                
                # Pause hint
                hint = ui.font_small.render("ESC to Pause", True, (150, 150, 150))
                screen.blit(hint, (WIDTH - hint.get_width() - 20, 20))

        elif ui.current_scene == "OVER":
            # Keep drawing game in background
            all_sprites.draw(screen)
            action = menu_cursor.process(ui.get_buttons("OVER"))
            ui.draw_game_over(screen, game_mode.score)
            menu_cursor.draw(screen)
            
            if action == "GOTO_MENU":
                # Keep the shared menu camera alive; only close a separate provider
                if input_provider and input_provider is not menu_hand:
                    input_provider.cleanup()
                input_provider = None
                ui.current_scene = "MENU"
                ui.scene_stack.clear()
                audio.play_music("menu")
            elif action == "RESTART":
                ui.current_scene = "GAME"
                audio.play_music("game_slow")
                
                if isinstance(game_mode, ClassicMode):
                    game_mode = ClassicMode()
                else:
                    game_mode = SurvivalMode()
                    
                all_sprites.empty()
                fruits.empty()
                blade = Blade()

        pygame.display.flip()
        clock.tick(FPS)
        
    
    # Cleanup — only close things this game owns.
    if input_provider and input_provider is not menu_hand:
        if hasattr(input_provider, "cleanup"):
            input_provider.cleanup()
    if menu_hand is not None:
        menu_hand.cleanup()

    try:
        audio.stop_music()
    except Exception:
        pass

    return exit_reason


if __name__ == "__main__":
    pygame.init()
    _screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Fruit Ninja — Hand Controlled")
    run_game(_screen)
    pygame.quit()
    sys.exit()
