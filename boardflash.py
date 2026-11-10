# Codebase generated with the help of ClaudeAI and ChatGPT6
# Usage of Claude:
#  1. Explaining what Flask and CSS is and looks like
#  2. how to use json with a webpage
# Usage of ChatGPT:
#  1. merge code function with main.py
#  2. remove redundancies with other portions of code and consolidate libraries

# Shared game state that can be called from main.
class Board:
    def __init__(self, size=6):
        self.size = size
        self.reset()

    def reset(self):
        # Restore all squares and clear the click count.
        self.alive = set(range(self.size * self.size))
        self.clicks = 0

    @property
    def remaining(self):
        return len(self.alive)

    def click(self, square):
        # Ignore missing or already removed squares.
        if square not in self.alive:
            return False
        self.alive.remove(square)
        self.clicks += 1
        return True

    def state(self):
        # Send only JSON-compatible values to browser clients.
        return {
            "size": self.size,
            "alive": sorted(self.alive),
            "left": self.remaining,
            "clicks": self.clicks,
            "won": self.remaining == 0,
        }
