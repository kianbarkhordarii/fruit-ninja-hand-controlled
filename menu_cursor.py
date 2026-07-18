import pygame
import time
import math


class MenuCursor:
    """
    A hand-driven cursor for menu navigation.

    - Tracks a screen position (x, y) coming from the hand tracker.
    - Implements "dwell to click": if the finger stays over the same button
      for `dwell_time` seconds, it fires a click for that button.
    - Draws a visible pointer and a progress ring while dwelling.
    """

    def __init__(self, dwell_time=1.0):
        self.x = None
        self.y = None
        self.active = False          # True when a hand is detected this frame

        self.dwell_time = dwell_time
        self.hover_action = None     # action code currently being dwelled on
        self.hover_start = 0.0       # time when dwell on current action began
        self.progress = 0.0          # 0..1 progress of the current dwell
        self.just_clicked_action = None

        # A short cooldown so a single dwell doesn't fire repeatedly
        self.cooldown_until = 0.0

    def update_position(self, x, y):
        """Feed the latest hand position. Pass (None, None) if no hand."""
        if x is None or y is None:
            self.active = False
            self.x, self.y = None, None
            # Reset dwell if hand disappears
            self.hover_action = None
            self.progress = 0.0
        else:
            self.active = True
            self.x, self.y = x, y

    def process(self, buttons):
        """
        Given the list of buttons currently on screen, determine hover and
        whether a dwell-click just completed.

        `buttons` is a list of FrameButton objects.
        Returns the action code if a click fired this frame, else None.
        """
        self.just_clicked_action = None

        if not self.active or self.x is None:
            self.hover_action = None
            self.progress = 0.0
            return None

        now = time.time()

        # Find which button (if any) the cursor is over
        current = None
        for btn in buttons:
            is_over = btn.rect.collidepoint(self.x, self.y)
            btn.hover = is_over
            btn.target_scale = 1.05 if is_over else 1.0
            if is_over:
                current = btn

        # In cooldown right after a click: don't start a new dwell yet
        if now < self.cooldown_until:
            self.hover_action = None
            self.progress = 0.0
            return None

        if current is None:
            # Not over any button -> reset dwell
            self.hover_action = None
            self.progress = 0.0
            return None

        # We are over a button
        if self.hover_action != current.action:
            # Started hovering a new button -> restart the dwell timer
            self.hover_action = current.action
            self.hover_start = now
            self.progress = 0.0
        else:
            # Still on the same button -> advance progress
            elapsed = now - self.hover_start
            self.progress = min(elapsed / self.dwell_time, 1.0)
            if self.progress >= 1.0:
                # Fire the click
                self.just_clicked_action = current.action
                current.target_scale = 0.95
                self.hover_action = None
                self.progress = 0.0
                self.cooldown_until = now + 0.6   # brief pause before next click
                return current.action

        return None

    def draw(self, screen):
        """Draw the pointer and dwell progress ring."""
        if not self.active or self.x is None:
            return

        x, y = int(self.x), int(self.y)

        # Outer soft glow
        glow = pygame.Surface((60, 60), pygame.SRCALPHA)
        pygame.draw.circle(glow, (0, 255, 255, 40), (30, 30), 28)
        screen.blit(glow, (x - 30, y - 30))

        # Core pointer dot
        pygame.draw.circle(screen, (0, 255, 255), (x, y), 10)
        pygame.draw.circle(screen, (255, 255, 255), (x, y), 10, 2)

        # Dwell progress ring
        if self.progress > 0:
            radius = 22
            start_angle = -math.pi / 2
            end_angle = start_angle + (2 * math.pi * self.progress)
            # Draw an arc as a series of points for smoothness
            points = []
            steps = max(2, int(self.progress * 40))
            for i in range(steps + 1):
                a = start_angle + (end_angle - start_angle) * (i / steps)
                px = x + radius * math.cos(a)
                py = y + radius * math.sin(a)
                points.append((px, py))
            if len(points) >= 2:
                pygame.draw.lines(screen, (255, 255, 0), False, points, 4)
