import pygame
import sys

# Initialize Pygame
pygame.init()

# Screen dimensions
WIDTH, HEIGHT = 1000, 700
window = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Elemental Combat System")

# Colors that I should probably use
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GRAY = (180, 180, 180)
LIGHT_GRAY = (211, 211, 211)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)

# Fonts
font = pygame.font.SysFont(None, 24)
large_font = pygame.font.SysFont(None, 32)

# Elements and reactions
elements = ["Pyro", "Cryo", "Hydro", "Electro", "Dendro", "Geo", "Anemo"]


reactions = [
# Triple Reactions should be check first
    (frozenset(["Anemo", "Hydro", "Electro"]), ("Thunderstorm", 1.0, "Strikes all targets with lightning, dealing 40% of caster's max HP.", ['ALL'], "Electro")),
    (frozenset(["Dendro", "Hydro", "Cryo"]), ("Toxic Spores", 1.0, "3 Spores will emerge; after 3 turns, target takes 5% of Max HP as damage.", ['ALL'], None)),
    # Double-element reactions
    (frozenset(["Pyro", "Cryo"]), ("Melt", 1.5, "Removes ALL applied elements.", ['ALL'], None)),
    (frozenset(["Hydro", "Pyro"]), ("Vaporize", 1.5, "Removes ALL applied elements.", ['ALL'], None)),
    (frozenset(["Cryo", "Hydro"]), ("Freeze", 0, "Freezes target for 1 turn.", [], None)),  # Do not remove elements
    (frozenset(["Electro", "Cryo"]), ("Superconduct", 1.0, "Reduces target defense by 50% for 1 turn. Removes ALL applied elements.", ['ALL'], None)),
    (frozenset(["Electro", "Hydro"]), ("Electro-charged", 1.0, "Applies damage to ALL targets.", [], "Electro")),
    # Swirl reactions
    (frozenset(["Anemo", "Pyro"]), ("Swirl", 1.0, "Applies Swirled Pyro to all targets. Removes Anemo element.", ['Anemo'], None)),
    (frozenset(["Anemo", "Cryo"]), ("Swirl", 1.0, "Applies Swirled Cryo to all targets. Removes Anemo element.", ['Anemo'], None)),
    (frozenset(["Anemo", "Hydro"]), ("Swirl", 1.0, "Applies Swirled Hydro to all targets. Removes Anemo element.", ['Anemo'], None)),
    (frozenset(["Anemo", "Electro"]), ("Swirl", 1.0, "Applies Swirled Electro to all targets. Removes Anemo element.", ['Anemo'], None)),
    # Other reactions
    (frozenset(["Geo", "Pyro"]), ("Crystallize", 1.0, "Creates a shield granting immunity to Pyro for 1 turn. Removes ALL elements.", ['ALL'], None)),
    (frozenset(["Geo", "Cryo"]), ("Crystallize", 1.0, "Creates a shield granting immunity to Cryo for 1 turn. Removes ALL elements.", ['ALL'], None)),
    (frozenset(["Geo", "Hydro"]), ("Crystallize", 1.0, "Creates a shield granting immunity to Hydro for 1 turn. Removes ALL elements.", ['ALL'], None)),
    (frozenset(["Geo", "Electro"]), ("Crystallize", 1.0, "Creates a shield granting immunity to Electro for 1 turn. Removes ALL elements.", ['ALL'], None)),
    (frozenset(["Geo", "Geo"]), ("Stabilize", 1.0, "Creates a shield reducing incoming damage by 30% for 2 turns. Removes Geo elements.", ['Geo'], None)),
    (frozenset(["Hydro", "Geo"]), ("Petrify", 0, "Petrifies target for 1 turn.", ['Geo'], None)),
    (frozenset(["Electro", "Pyro"]), ("Overload", 1.0, "Disarms target for 1 turn. Removes ALL elements.", ['ALL'], None)),
    (frozenset(["Dendro", "Hydro"]), ("Bloom", 0, "Heals target by 25% of max health.", ['ALL'], None)),
    (frozenset(["Dendro", "Pyro"]), ("Burning", 1.0, "Applies 3% max HP DoT for 3 rounds.", ['ALL'], None)),
    (frozenset(["Dendro", "Anemo"]), ("Healing Winds", 0, "Heals all party members by 20% max HP over 3 rounds.", ['ALL'], None)),
    (frozenset(["Electro", "Dendro"]), ("Corrosion", 1.0, "Applies DoT equal to 5% max HP for 2 turns.", ['ALL'], None)),
    (frozenset(["Anemo", "Geo"]), ("Sandstorm", 1.0, "Targets roll at disadvantage for 1 turn. Removes ALL applied elements.", ['ALL'], None)),
    (frozenset(["Cryo", "Dendro"]), ("Frostbite", 1.0, "Applies DoT equal to 3% max HP for 3 turns and reduces movement speed by 50%.", ['ALL'], None)),
# put new reactions here
]

class Enemy:
    def __init__(self, name, max_hp, defense=0, elements_applied=[], is_frozen=False, is_petrified=False):
        self.name = name
        self.max_hp = max_hp
        self.current_hp = max_hp
        self.elements = elements_applied.copy()  # normal ele
        self.swirled_elements = []  # swirled ele
        self.defense = defense
        self.damage_log = []
        self.debuffs = {}  # Debuffs with their remaining durations or details
        self.is_frozen = is_frozen
        self.is_petrified = is_petrified
        self.marked = False  # For certain reactions and ultimates (Ultimates unimplemented)
        self.shield = None  # For shields from reactions (broken, should not give enemy a shield)

    def apply_element(self, element):
        if element not in self.elements:
            self.elements.append(element)
            return f"{element} applied to {self.name}."
        else:
            return f"{self.name} already has {element} applied."

    def calculate_damage(self, base_damage, multiplier=1.0, attack_element=None):
        # Apply defense reduction from debuffs
        defense = self.defense
        if "Superconduct" in self.debuffs:
            defense *= 0.5
        damage = (base_damage * multiplier) - defense
        # Apply shield effects
        if self.shield:
            if self.shield['type'] == 'Damage Reduction':
                damage *= (1 - self.shield.get('reduction', 0))
            elif self.shield['type'] == 'Elemental Immunity':
                if attack_element == self.shield.get('element'):
                    return f"{self.name} is immune to {attack_element} damage!"
        damage = max(damage, 0)  # Prevent negative damage
        self.current_hp -= damage
        self.damage_log.append(damage)
        return f"{self.name} takes {damage:.2f} damage! Remaining HP: {self.current_hp:.2f}"

    def reset_elements(self):
        self.elements = []
        self.swirled_elements = []

    def apply_debuff(self, debuff_name, duration):
        self.debuffs[debuff_name] = duration
        return f"{self.name} is affected by {debuff_name} for {duration} turn(s)."

    def update_debuffs(self): # Tick Debuffs

        to_remove = []
        messages = []
        for debuff in list(self.debuffs.keys()):
            if isinstance(self.debuffs[debuff], dict):
                # For DoT debuffs, duration is inside the dict
                self.debuffs[debuff]['duration'] -= 1
                if self.debuffs[debuff]['duration'] <= 0:
                    to_remove.append(debuff)
            else:
                # For other debuffs
                self.debuffs[debuff] -= 1
                if self.debuffs[debuff] <= 0:
                    to_remove.append(debuff)
                    if debuff == "Freeze":
                        self.is_frozen = False
                    if debuff == "Petrify":
                        self.is_petrified = False
        for debuff in to_remove:
            messages.append(f"{debuff} on {self.name} has ended.")
            del self.debuffs[debuff]
        return messages

    def update_shield(self):
        # Update shield duration
        messages = []
        if self.shield:
            self.shield['duration'] -= 1
            if self.shield['duration'] <= 0:
                messages.append(f"{self.name}'s shield has expired.")
                self.shield = None
        return messages

    def apply_dot(self, percentage, duration, dot_name):
        # Store DoT info in the debuffs dictionary
        self.debuffs[dot_name] = {'duration': duration, 'percentage': percentage}
        dot_damage = self.max_hp * (percentage / 100)
        return f"{dot_name} will deal {dot_damage:.2f} damage per turn for {duration} turns."

    def process_dot(self):
        total_dot_damage = 0
        messages = []
        for debuff in list(self.debuffs.keys()):
            debuff_info = self.debuffs[debuff]
            if isinstance(debuff_info, dict) and 'percentage' in debuff_info:
                dot_damage = self.max_hp * (debuff_info['percentage'] / 100)
                self.current_hp -= dot_damage
                total_dot_damage += dot_damage
                messages.append(f"{debuff} deals {dot_damage:.2f} damage to {self.name}.")
                # Do not decrease duration here
        if total_dot_damage > 0:
            messages.append(f"Total DoT damage this turn: {total_dot_damage:.2f}")
            messages.append(f"{self.name}'s HP after DoT: {self.current_hp:.2f}")
        return messages

    def apply_heal(self, percentage):
        heal_amount = self.max_hp * (percentage / 100)
        self.current_hp = min(self.max_hp, self.current_hp + heal_amount)
        return f"{self.name} heals for {heal_amount:.2f} HP! Current HP: {self.current_hp:.2f}"

    def check_status(self):
        status = []
        if self.is_frozen:
            status.append("Frozen")
        if self.is_petrified:
            status.append("Petrified")
        if self.marked:
            status.append("Marked")
        if self.shield:
            status.append(f"Shielded ({self.shield['type']})")
        if status:
            return f"{self.name} status: {', '.join(status)}"
        else:
            return f"{self.name} has no special status effects."

    def display_elements(self):
        elements_info = f"Current elements on {self.name}: {self.elements}"
        swirled_info = ""
        if self.swirled_elements:
            swirled_info = f"Swirled elements on {self.name}: {self.swirled_elements}"
        return elements_info + ("\n" + swirled_info if swirled_info else "")

    def process_turn(self):
        messages = []
        # Process DoT effects
        messages.extend(self.process_dot())
        # Update debuffs
        messages.extend(self.update_debuffs())
        # Update shield duration
        messages.extend(self.update_shield())
        # Handle Toxic Spores explosion
        if "Toxic Spores" in self.debuffs and self.debuffs["Toxic Spores"] == 0:
            damage = self.max_hp * 0.05
            damage_message = self.calculate_damage(damage)
            messages.append(damage_message)
            messages.append("Toxic Spores exploded!")
            del self.debuffs["Toxic Spores"]
        return messages

class Button:
    def __init__(self, x, y, w, h, text, callback):
        self.rect = pygame.Rect(x, y, w, h)
        self.color = LIGHT_GRAY
        self.text = text
        self.callback = callback
        self.font = font

    def draw(self, surface):
        pygame.draw.rect(surface, self.color, self.rect)
        txt_surf = self.font.render(self.text, True, BLACK)
        txt_rect = txt_surf.get_rect(center=self.rect.center)
        surface.blit(txt_surf, txt_rect)

    def is_clicked(self, pos):
        return self.rect.collidepoint(pos)

# TextInput class for Pygame
class TextInput:
    def __init__(self, x, y, w, h, text=''):
        self.rect = pygame.Rect(x, y, w, h)
        self.color_inactive = LIGHT_GRAY
        self.color_active = GRAY
        self.color = self.color_inactive
        self.text = text
        self.txt_surface = font.render(text, True, BLACK)
        self.active = False
        self.font = font

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            # Toggle active state
            if self.rect.collidepoint(event.pos):
                self.active = not self.active
            else:
                self.active = False
            self.color = self.color_active if self.active else self.color_inactive

        if event.type == pygame.KEYDOWN:
            if self.active:
                if event.key == pygame.K_RETURN:
                    self.active = False
                    self.color = self.color_inactive
                elif event.key == pygame.K_BACKSPACE:
                    self.text = self.text[:-1]
                else:
                    self.text += event.unicode
                # Re-render text
                self.txt_surface = self.font.render(self.text, True, BLACK)

    def draw(self, surface):
        # Blit the text
        surface.blit(self.txt_surface, (self.rect.x+5, self.rect.y+5))
        # Blit the rect
        pygame.draw.rect(surface, self.color, self.rect, 2)

# Functions
def baseAttack():
    message = "Performing a base attack..."
    log_messages.append(message)
    base_damage = float(base_damage_input.text) if base_damage_input.text else 0
    damage_message = enemy.calculate_damage(base_damage)
    log_messages.append(damage_message)
    # Display current elements
    elements_info = enemy.display_elements()
    log_messages.append(elements_info)
    # Check enemy status
    status_message = enemy.check_status()
    log_messages.append(status_message)
    # Process end-of-turn effects
    turn_messages = enemy.process_turn()
    log_messages.extend(turn_messages)
    checkDead()

def checkReact():
    reaction_effects = None
    # Collect elements separately
    applied_elements = set(enemy.elements)
    swirled_elements = set(enemy.swirled_elements)
    total_elements = applied_elements.union(swirled_elements)
    # Check reactions in order, starting with the most specific (triple-element reactions)
    for element_combination, effect in reactions:
        if element_combination.issubset(total_elements):
            reaction_effects = effect
            break

    if reaction_effects:
        reaction_name, multiplier, effect_desc, elements_to_remove, attack_element = reaction_effects
        log_messages.append(f"Reaction triggered: {reaction_name}")
        log_messages.append(f"Effect: {effect_desc}")
        base_damage = float(base_damage_input.text) if base_damage_input.text else 0

        # Handle specific reactions
        if reaction_name in ["Melt", "Vaporize"]:
            damage_message = enemy.calculate_damage(base_damage, multiplier)
            log_messages.append(damage_message)
        elif reaction_name == "Freeze":
            debuff_message = enemy.apply_debuff("Freeze", 1)
            enemy.is_frozen = True
            log_messages.append(debuff_message)
        elif reaction_name == "Superconduct":
            debuff_message = enemy.apply_debuff("Superconduct", 1)
            log_messages.append(debuff_message)
            damage_message = enemy.calculate_damage(base_damage, multiplier)
            log_messages.append(damage_message)
        elif reaction_name == "Electro-charged":
            damage_message = enemy.calculate_damage(base_damage, multiplier, attack_element=attack_element)
            log_messages.append(damage_message)
            log_messages.append("Damage applied to all targets (assuming single enemy in this script).")
        elif reaction_name == "Swirl":
            # Apply Swirled element to target
            elements_to_swirl = [elem for elem in enemy.elements if elem != 'Anemo']
            for elem in elements_to_swirl:
                if elem not in enemy.swirled_elements:
                    enemy.swirled_elements.append(elem)
                    log_messages.append(f"{elem} has been swirled onto {enemy.name}.")
        elif reaction_name == "Crystallize":
            elements_to_crystallize = [elem for elem in enemy.elements if elem != 'Geo']
            for elem in elements_to_crystallize:
                enemy.shield = {'type': 'Elemental Immunity', 'duration': 1, 'element': elem}
                log_messages.append(f"{enemy.name} gains a shield granting immunity to {elem} damage for 1 turn.")
        elif reaction_name == "Stabilize":
            enemy.shield = {'type': 'Damage Reduction', 'duration': 2, 'reduction': 0.3}
            log_messages.append(f"{enemy.name} gains a shield reducing incoming damage by 30% for 2 turns.")
        elif reaction_name == "Petrify":
            debuff_message = enemy.apply_debuff("Petrify", 1)
            enemy.is_petrified = True
            log_messages.append(debuff_message)
        elif reaction_name == "Overload":
            debuff_message = enemy.apply_debuff("Disarmed", 1)
            log_messages.append(debuff_message)
        elif reaction_name == "Burning":
            dot_message = enemy.apply_dot(3, 3, "Burning")
            log_messages.append(dot_message)
        elif reaction_name == "Corrosion":
            dot_message = enemy.apply_dot(5, 2, "Corrosion")
            log_messages.append(dot_message)
        elif reaction_name == "Frostbite":
            dot_message = enemy.apply_dot(3, 3, "Frostbite")
            log_messages.append(dot_message)
            debuff_message = enemy.apply_debuff("Movement Speed Reduction", 3)
            log_messages.append(debuff_message)
            log_messages.append("Movement speed reduced by 50% for 3 turns.")
        elif reaction_name == "Bloom":
            heal_message = enemy.apply_heal(25)
            log_messages.append(heal_message)
        elif reaction_name == "Hyperbloom":
            heal_message = enemy.apply_heal(15)
            log_messages.append(heal_message)
            log_messages.append("Rejuvenate effect applied: Heals 5% max HP per turn for 3 turns.")
        elif reaction_name == "Toxic Spores":
            log_messages.append("3 Spores will emerge from the target.")
            log_messages.append("After 3 turns, target takes 5% of Max HP as damage.")
            enemy.debuffs["Toxic Spores"] = 3  # Duration until spores burst
        elif reaction_name == "Sandstorm":
            debuff_message = enemy.apply_debuff("Disadvantage", 1)
            log_messages.append(debuff_message)
        elif reaction_name == "Thunderstorm":
            caster_max_hp = float(caster_max_hp_input.text) if caster_max_hp_input.text else 0
            damage = caster_max_hp * 0.4
            damage_message = enemy.calculate_damage(damage, attack_element='Electro')
            log_messages.append(damage_message)
            log_messages.append(f"Thunderstorm deals {damage} Electro damage to {enemy.name}.")
        else:
            damage_message = enemy.calculate_damage(base_damage, multiplier)
            log_messages.append(damage_message)

        # Remove specified elements after the reaction
        if elements_to_remove == ['ALL']:
            enemy.reset_elements()
        else:
            for elem in elements_to_remove:
                if elem in enemy.elements:
                    enemy.elements.remove(elem)
                if elem in enemy.swirled_elements:
                    enemy.swirled_elements.remove(elem)

        # Display current elements
        elements_info = enemy.display_elements()
        log_messages.append(elements_info)
    else:
        # No reaction triggered
        log_messages.append("No elemental reaction triggered.")
        base_damage = float(base_damage_input.text) if base_damage_input.text else 0
        damage_message = enemy.calculate_damage(base_damage)
        log_messages.append(damage_message)
        # Display current elements
        elements_info = enemy.display_elements()
        log_messages.append(elements_info)

    # Check enemy status
    status_message = enemy.check_status()
    log_messages.append(status_message)
    # Process end-of-turn effects
    turn_messages = enemy.process_turn()
    log_messages.extend(turn_messages)
    checkDead()

def add_element(element):
    if enemy.is_frozen or enemy.is_petrified:
        log_messages.append(f"{enemy.name} is unable to act due to being {'Frozen' if enemy.is_frozen else 'Petrified'}.")
        # Even if the enemy can't act process end-of-turn effects
        turn_messages = enemy.process_turn()
        log_messages.extend(turn_messages)
        checkDead()
    else:
        message = enemy.apply_element(element)
        log_messages.append(message)
        checkReact()

def checkDead():
    if enemy.current_hp <= 0:
        log_messages.append(f"{enemy.name} is defeated!")
        disable_buttons()

def disable_buttons():
    for button in buttons:
        button.callback = lambda: None

def draw_enemy_status(surface, enemy):
    y_offset = 100
    # Display enemy name and HP
    name_text = large_font.render(f"Enemy: {enemy.name}", True, BLACK)
    surface.blit(name_text, (300, y_offset))

    # HP bar
    hp_bar_length = 400
    hp_bar_height = 25
    fill = (enemy.current_hp / enemy.max_hp) * hp_bar_length
    pygame.draw.rect(surface, RED, (300, y_offset + 40, hp_bar_length, hp_bar_height))
    pygame.draw.rect(surface, GREEN, (300, y_offset + 40, fill, hp_bar_height))
    hp_text = font.render(f"HP: {enemy.current_hp:.2f}/{enemy.max_hp}", True, BLACK)
    surface.blit(hp_text, (300, y_offset + 70))

    # Display elements
    elements_text = font.render(f"Elements: {', '.join(enemy.elements)}", True, BLACK)
    surface.blit(elements_text, (300, y_offset + 100))

    # Display swirled elements
    if enemy.swirled_elements:
        swirled_text = font.render(f"Swirled Elements: {', '.join(enemy.swirled_elements)}", True, BLACK)
        surface.blit(swirled_text, (300, y_offset + 130))

    # Display debuffs
    if enemy.debuffs:
        debuffs_text = font.render(f"Debuffs: {', '.join(enemy.debuffs.keys())}", True, BLACK)
        surface.blit(debuffs_text, (300, y_offset + 160))

    # Display status effects
    status_effects = []
    if enemy.is_frozen:
        status_effects.append("Frozen")
    if enemy.is_petrified:
        status_effects.append("Petrified")
    if enemy.shield:
        status_effects.append(f"Shielded ({enemy.shield['type']})")

    if status_effects:
        status_text = font.render(f"Status: {', '.join(status_effects)}", True, BLACK)
        surface.blit(status_text, (300, y_offset + 190))

def displayLog(surface, logs):
    max_logs = 5
    start_y = 500
    for i, message in enumerate(logs[-max_logs:]):
        log_text = font.render(message, True, BLACK)
        surface.blit(log_text, (10, start_y + i * 20))

# Set up buttons and inputs
buttons = []
button_width, button_height = 100, 40

# Create element  (Pyro Cryo, etc)
for i, elem in enumerate(elements):
    x = 10
    y = 10 + i * (button_height + 5)
    btn = Button(x, y, button_width, button_height, elem, lambda e=elem: add_element(e))
    buttons.append(btn)

# Base Attack Button
base_attack_btn = Button(10, 10 + len(elements) * (button_height + 5), button_width, button_height, "Base Attack", baseAttack)
buttons.append(base_attack_btn)

# Create Text Inputs
base_damage_input = TextInput(150, 10, 100, 32, '25')
caster_max_hp_input = TextInput(150, 52, 100, 32, '100')

# Labels for Text Inputs
base_damage_label = font.render("Base Damage:", True, BLACK)
caster_max_hp_label = font.render("Caster Max HP:", True, BLACK)

# Initialize Enemy and Logs
enemy = Enemy("Frostbeast", 500, defense=20)
log_messages = []

# Main Game Loop
running = True
clock = pygame.time.Clock()

while running:
    window.fill(WHITE)

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        # Handle text input events
        base_damage_input.handle_event(event)
        caster_max_hp_input.handle_event(event)

        if event.type == pygame.MOUSEBUTTONDOWN:
            pos = pygame.mouse.get_pos()
            for button in buttons:
                if button.is_clicked(pos):
                    button.callback()
    for button in buttons:
        button.draw(window)

    window.blit(base_damage_label, (260, 18))
    base_damage_input.draw(window)
    window.blit(caster_max_hp_label, (260, 60))
    caster_max_hp_input.draw(window)


    draw_enemy_status(window, enemy)

    # Display log messages
    displayLog(window, log_messages)

    # Update display
    pygame.display.flip()

    # Cap the frame rate
    clock.tick(30)

pygame.quit()
sys.exit()
