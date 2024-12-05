import pygame
import sys
import pickle
import os
import random
import matplotlib.pyplot as plt

# Initialize Pygame
pygame.init()


WIDTH, HEIGHT = 1300, 900
window = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Elemental Combat System")

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GRAY = (180, 180, 180)
LIGHT_GRAY = (211, 211, 211)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)
font = pygame.font.SysFont(None, 24)
large_font = pygame.font.SysFont(None, 28)


# =======================================================================
#              Gameplay / Damge calculations and Reactions
# =======================================================================

elements = ["Pyro", "Cryo", "Hydro", "Electro", "Dendro", "Geo", "Anemo"]


reactions = [
    # Reactions are defined by the elements required (x,y, sometimes z)
    # triple-element reactions (more specific reactions first)
    (frozenset(["Anemo", "Hydro", "Electro"]), ("Thunderstorm", 1.0, "Strikes all targets with lightning, dealing 40% of caster's max HP.", ['ALL'], "Electro")),
    (frozenset(["Dendro", "Hydro", "Cryo"]), ("Toxic Spores", 1.0, "3 Spores will emerge; after 3 turns, target takes 5% of Max HP as damage.", ['ALL'], None)),
    # double-element reactions
    (frozenset(["Pyro", "Cryo"]), ("Melt", 1.5, "Removes ALL applied elements.", ['ALL'], None)),
    (frozenset(["Hydro", "Pyro"]), ("Vaporize", 1.5, "Removes ALL applied elements.", ['ALL'], None)),
    (frozenset(["Cryo", "Hydro"]), ("Freeze", 0, "Freezes target for 1 turn.", [], None)),
    (frozenset(["Electro", "Cryo"]), ("Superconduct", 1.0, "Reduces target defense by 50% for 1 turn. Removes ALL applied elements.", ['ALL'], None)),
    (frozenset(["Electro", "Hydro"]), ("Electro-charged", 1.0, "Applies damage to ALL targets.", [], "Electro")),
    # swirl reactions
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
]

# Player class
class Player:
    def __init__(self, name, max_hp, ac, movement, initiative, element, temp_hp=0):
        self.name = name
        self.max_hp = max_hp
        self.current_hp = max_hp
        self.temp_hp = temp_hp
        self.ac = ac
        self.movement = movement
        self.initiative = initiative
        self.element = element
        self.type = 'Player'  
        self.actions_taken = 0
        self.total_damage_dealt = 0
        self.total_damage_taken = 0

# Enemy class
class Enemy:
    def __init__(self, name, max_hp, defense=0, elements_applied=[], is_frozen=False, is_petrified=False, initiative=0):
        self.name = name
        self.max_hp = max_hp
        self.current_hp = max_hp
        self.elements = elements_applied.copy()  # Elements directly applied
        self.swirled_elements = []  # Elements via Swirl
        self.defense = defense
        self.damage_log = []
        self.debuffs = {} 
        self.is_frozen = is_frozen
        self.is_petrified = is_petrified
        self.marked = False
        self.shield = None
        self.rect = None  # For enemy selection
        self.initiative = initiative
        self.type = 'Enemy'
        self.actions_taken = 0
        self.total_damage_dealt = 0
        self.total_damage_taken = 0

    def apply_element(self, element):
        if element not in self.elements:
            self.elements.append(element)
            return f"{element} applied to {self.name}."
        else:
            return f"{self.name} already has {element} applied."

    def calculate_damage(self, base_damage, multiplier=1.0, attack_element=None):
        # Apply defense reduction from debuffs IT KEEPS GIVING ENEMIES THE SHIELDS
        defense = self.defense
        if "Superconduct" in self.debuffs:
            defense *= 0.5
        damage = (base_damage * multiplier) - defense
        if self.shield:
            if self.shield['type'] == 'Damage Reduction':
                damage *= (1 - self.shield.get('reduction', 0))
            elif self.shield['type'] == 'Elemental Immunity':
                if attack_element == self.shield.get('element'):
                    return f"{self.name} is immune to {attack_element} damage!"
        damage = max(damage, 0)  # Prevent negative damage
        self.current_hp -= damage
        self.damage_log.append(damage)
        self.total_damage_taken += damage
        return f"{self.name} takes {damage:.2f} damage! Remaining HP: {self.current_hp:.2f}"

    def reset_elements(self):
        self.elements = []
        self.swirled_elements = []

    def apply_debuff(self, debuff_name, duration):
        self.debuffs[debuff_name] = duration
        return f"{self.name} is affected by {debuff_name} for {duration} turn(s)."

    def update_debuffs(self):
        to_remove = []
        messages = []
        for debuff in list(self.debuffs.keys()):
            if isinstance(self.debuffs[debuff], dict):
                # For DoT debuffs
                self.debuffs[debuff]['duration'] -= 1
                if self.debuffs[debuff]['duration'] <= 0:
                    to_remove.append(debuff)
            else:
                self.debuffs[debuff] -= 1
                if self.debuffs[debuff] <= 0:
                    to_remove.append(debuff)
                    if debuff == "Freeze":
                        self.is_frozen = False
                    if debuff == "Petrify":
                        self.is_petrified = False
        for debuff in to_remove:
            del self.debuffs[debuff]
        return messages

    def update_shield(self):
        messages = []
        if self.shield:
            self.shield['duration'] -= 1
            if self.shield['duration'] <= 0:
                self.shield = None
        return messages

    def apply_dot(self, percentage, duration, dot_name):
        self.debuffs[dot_name] = {'duration': duration, 'percentage': percentage}
        return f"{dot_name} will deal {self.max_hp * (percentage / 100):.2f} damage per turn for {duration} turns."

    def process_dot(self):
        total_dot_damage = 0
        messages = []
        for debuff in list(self.debuffs.keys()):
            debuff_info = self.debuffs[debuff]
            if isinstance(debuff_info, dict) and 'percentage' in debuff_info:
                dot_damage = self.max_hp * (debuff_info['percentage'] / 100)
                self.current_hp -= dot_damage
                total_dot_damage += dot_damage
                self.total_damage_taken += dot_damage
        if total_dot_damage > 0:
            messages.append(f"{self.name} takes {total_dot_damage:.2f} DoT damage! Remaining HP: {self.current_hp:.2f}")
        return messages

    def apply_heal(self, percentage):
        heal_amount = self.max_hp * (percentage / 100)
        self.current_hp = min(self.max_hp, self.current_hp + heal_amount)
        return f"{self.name} heals for {heal_amount:.2f} HP! Current HP: {self.current_hp:.2f}"

    def process_turn(self):
        messages = []
        messages.extend(self.process_dot())
        messages.extend(self.update_debuffs())
        messages.extend(self.update_shield())
        if "Toxic Spores" in self.debuffs and self.debuffs["Toxic Spores"] == 0:
            damage = self.max_hp * 0.05
            damage_message = self.calculate_damage(damage)
            messages.append(damage_message)
            messages.append("Toxic Spores exploded!")
            del self.debuffs["Toxic Spores"]
        return messages

class Button:
    def __init__(self, x, y, w, h, text, callback, image=None):
        self.rect = pygame.Rect(x, y, w, h)
        self.color = LIGHT_GRAY
        self.text = text
        self.callback = callback
        self.font = font
        self.image = image

    def draw(self, surface):
        if self.image:
            surface.blit(self.image, self.rect)
        else:
            pygame.draw.rect(surface, self.color, self.rect)
            txt_surf = self.font.render(self.text, True, BLACK)
            txt_rect = txt_surf.get_rect(center=self.rect.center)
            surface.blit(txt_surf, txt_rect)

    def is_clicked(self, pos):
        return self.rect.collidepoint(pos)

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
                self.txt_surface = self.font.render(self.text, True, BLACK)

    def draw(self, surface):
        surface.blit(self.txt_surface, (self.rect.x+5, self.rect.y+5))
        pygame.draw.rect(surface, self.color, self.rect, 2)

# Functions
def perform_base_attack():
    global current_actor_index
    log_messages.clear()
    actor = turn_order[current_actor_index]
    if actor.type != 'Player':
        return
    player = actor
    if not enemies:
        log_messages.append("No enemies to attack.")
        return
    target_enemy = enemies[selected_enemy_index]
    # apply player's element to the enemy
    message = target_enemy.apply_element(player.element)
    log_messages.append(message)
    # calculate base damage
    base_damage = 0
    if damage_override_input.text:
        base_damage = float(damage_override_input.text)
    elif selected_dice and dice_quantity_input.text:
        dice_quantity = int(dice_quantity_input.text)
        for _ in range(dice_quantity):
            base_damage += random.randint(1, selected_dice)
    else:
        base_damage = 1  # default
    player.actions_taken += 1
    player.total_damage_dealt += base_damage
    calculate_elemental_reaction(player, target_enemy, base_damage)
    check_enemy_defeat(target_enemy)
    advance_turn()

def calculate_elemental_reaction(player, target_enemy, base_damage):
    reaction_effects = None
    applied_elements = set(target_enemy.elements)
    swirled_elements = set(target_enemy.swirled_elements)
    total_elements = applied_elements.union(swirled_elements)
    elements_involved = total_elements.union({player.element})
    # check reacts (triple-element reactions)
    for element_combination, effect in reactions:
        if element_combination.issubset(elements_involved):
            reaction_effects = effect
            break

    if reaction_effects:
        reaction_name, multiplier, effect_desc, elements_to_remove, attack_element = reaction_effects
        log_messages.append(f"Reaction triggered: {reaction_name}")
        log_messages.append(f"Effect: {effect_desc}")

        # Handle specific reactions
        if reaction_name in ["Melt", "Vaporize"]:
            damage_message = target_enemy.calculate_damage(base_damage, multiplier)
            log_messages.append(damage_message)
        elif reaction_name == "Freeze":
            debuff_message = target_enemy.apply_debuff("Freeze", 1)
            target_enemy.is_frozen = True
            log_messages.append(debuff_message)
        elif reaction_name == "Superconduct":
            debuff_message = target_enemy.apply_debuff("Superconduct", 1)
            log_messages.append(debuff_message)
            damage_message = target_enemy.calculate_damage(base_damage, multiplier)
            log_messages.append(damage_message)
        elif reaction_name == "Electro-charged":
            for enemy in enemies[:]:
                damage_message = enemy.calculate_damage(base_damage, multiplier, attack_element=attack_element)
                log_messages.append(damage_message)
            log_messages.append("Damage applied to all targets.")
        elif reaction_name == "Swirl":
            elements_to_swirl = [elem for elem in target_enemy.elements if elem != 'Anemo']
            for elem in elements_to_swirl:
                for enemy in enemies:
                    if elem not in enemy.swirled_elements:
                        enemy.swirled_elements.append(elem)
            log_messages.append("Swirl reaction applied.")
        elif reaction_name == "Crystallize":
            elements_to_crystallize = [elem for elem in target_enemy.elements if elem != 'Geo']
            for elem in elements_to_crystallize:
                target_enemy.shield = {'type': 'Elemental Immunity', 'duration': 1, 'element': elem}
            log_messages.append(f"{target_enemy.name} gains a shield granting immunity to certain damage.")
        elif reaction_name == "Stabilize":
            target_enemy.shield = {'type': 'Damage Reduction', 'duration': 2, 'reduction': 0.3}
            log_messages.append(f"{target_enemy.name} gains a shield reducing incoming damage.")
        elif reaction_name == "Petrify":
            debuff_message = target_enemy.apply_debuff("Petrify", 1)
            target_enemy.is_petrified = True
            log_messages.append(debuff_message)
        elif reaction_name == "Overload":
            debuff_message = target_enemy.apply_debuff("Disarmed", 1)
            log_messages.append(debuff_message)
        elif reaction_name == "Burning":
            dot_message = target_enemy.apply_dot(3, 3, "Burning")
            log_messages.append(dot_message)
        elif reaction_name == "Corrosion":
            dot_message = target_enemy.apply_dot(5, 2, "Corrosion")
            log_messages.append(dot_message)
        elif reaction_name == "Frostbite":
            dot_message = target_enemy.apply_dot(3, 3, "Frostbite")
            log_messages.append(dot_message)
            debuff_message = target_enemy.apply_debuff("Movement Speed Reduction", 3)
            log_messages.append(debuff_message)
        elif reaction_name == "Bloom":
            heal_message = target_enemy.apply_heal(25)
            log_messages.append(heal_message)
        elif reaction_name == "Healing Winds":
            for player in players:
                heal_message = player_heal(player, 20)
                log_messages.append(heal_message)
            log_messages.append("Healing Winds heals all players.")
        elif reaction_name == "Toxic Spores":
            target_enemy.debuffs["Toxic Spores"] = 3 # time delay for spores
            log_messages.append("Toxic Spores applied to target.")
        elif reaction_name == "Sandstorm":
            for enemy in enemies:
                debuff_message = enemy.apply_debuff("Disadvantage", 1)
                log_messages.append(debuff_message)
            log_messages.append("Sandstorm affects all enemies.")
        elif reaction_name == "Thunderstorm":
            caster_max_hp = player.max_hp
            for enemy in enemies[:]:
                damage = caster_max_hp * 0.4
                damage_message = enemy.calculate_damage(damage, attack_element='Electro')
                log_messages.append(damage_message)
            log_messages.append("Thunderstorm strikes all enemies.")
        else:
            damage_message = target_enemy.calculate_damage(base_damage, multiplier)
            log_messages.append(damage_message)

        if elements_to_remove == ['ALL']:
            target_enemy.reset_elements()
        else:
            for elem in elements_to_remove:
                if elem in target_enemy.elements:
                    target_enemy.elements.remove(elem)
                if elem in target_enemy.swirled_elements:
                    target_enemy.swirled_elements.remove(elem)
    else:
        damage_message = target_enemy.calculate_damage(base_damage)
        log_messages.append(damage_message)

    for enemy in enemies[:]:
        turn_messages = enemy.process_turn()
        log_messages.extend(turn_messages)
        check_enemy_defeat(enemy)

def check_enemy_defeat(enemy):
    if enemy.current_hp <= 0:
        if enemy in enemies:
            enemies.remove(enemy)
        if enemy in turn_order:
            index = turn_order.index(enemy)
            turn_order.pop(index)
            global current_actor_index
            if index <= current_actor_index and current_actor_index > 0:
                current_actor_index -= 1
        log_messages.append(f"{enemy.name} has been defeated!")
    if not enemies:
        disable_buttons()
        log_messages.append("All enemies have been defeated!")

def disable_buttons():
    for button in buttons:
        button.callback = lambda: None

def enemies_turn(enemy):
    if enemy.is_frozen or enemy.is_petrified:
        log_messages.append(f"{enemy.name} is unable to act.")
        return
    enemy.actions_taken += 1
    enemy_damage = float(enemy_damage_input.text) if enemy_damage_input.text else 10
    if not players:
        return
    target_player = random.choice(players)
    target_player.current_hp -= enemy_damage
    target_player.total_damage_taken += enemy_damage
    enemy.total_damage_dealt += enemy_damage
    log_messages.append(f"{enemy.name} attacks {target_player.name} for {enemy_damage} damage.")
    if target_player.current_hp <= 0:
        log_messages.append(f"{target_player.name} has been defeated!")
        players.remove(target_player)
        if target_player in turn_order:
            index = turn_order.index(target_player)
            turn_order.pop(index)
            global current_actor_index
            if index <= current_actor_index and current_actor_index > 0:
                current_actor_index -= 1
        if not players:
            log_messages.append("All players have been defeated! Game Over.")
            disable_buttons()

def player_heal(player, percentage):
    heal_amount = player.max_hp * (percentage / 100)
    player.current_hp = min(player.max_hp, player.current_hp + heal_amount)
    return f"{player.name} heals for {heal_amount:.2f} HP! Current HP: {player.current_hp:.2f}"

def advance_turn():
    global current_actor_index
    if not turn_order:
        return
    current_actor_index = (current_actor_index + 1) % len(turn_order)
    if not turn_order:
        return
    while turn_order[current_actor_index].type == 'Enemy':
        enemy = turn_order[current_actor_index]
        enemies_turn(enemy)
        for player in players[:]:
            if player.current_hp <= 0:
                players.remove(player)
                if player in turn_order:
                    index = turn_order.index(player)
                    turn_order.pop(index)
                    if index <= current_actor_index and current_actor_index > 0:
                        current_actor_index -= 1
        if not players or not enemies or not turn_order:
            break
        current_actor_index = (current_actor_index + 1) % len(turn_order)
        if current_actor_index >= len(turn_order):
            current_actor_index = 0
        if turn_order[current_actor_index].type != 'Enemy':
            break

# Drawing functions (sourced from pygame libraries)
def draw_enemies_status(surface, enemies):
    y_offset = 100
    x_offset = 220 
    enemy_width = 200
    enemy_height = 240
    spacing = 20
    max_enemies_per_row = 4
    for idx, enemy in enumerate(enemies):
        row = idx // max_enemies_per_row
        col = idx % max_enemies_per_row
        enemy_x = x_offset + col * (enemy_width + spacing)
        enemy_y = y_offset + row * (enemy_height + 100)

        # enemy stuff 
        name_text = large_font.render(f"Enemy: {enemy.name}", True, BLACK)
        surface.blit(name_text, (enemy_x, enemy_y))
        hp_bar_length = 180
        hp_bar_height = 25
        fill = max((enemy.current_hp / enemy.max_hp) * hp_bar_length, 0)
        pygame.draw.rect(surface, RED, (enemy_x, enemy_y + 40, hp_bar_length, hp_bar_height))
        pygame.draw.rect(surface, GREEN, (enemy_x, enemy_y + 40, fill, hp_bar_height))
        hp_text = font.render(f"HP: {enemy.current_hp:.2f}/{enemy.max_hp}", True, BLACK)
        surface.blit(hp_text, (enemy_x, enemy_y + 70))

        #elements
        elements_text = font.render(f"Elements: {', '.join(enemy.elements)}", True, BLACK)
        surface.blit(elements_text, (enemy_x, enemy_y + 100))
        if enemy.swirled_elements:
            swirled_text = font.render(f"Swirled: {', '.join(enemy.swirled_elements)}", True, BLACK)
            surface.blit(swirled_text, (enemy_x, enemy_y + 130))

        # debuffs
        if enemy.debuffs:
            debuffs_text = font.render(f"Debuffs: {', '.join(enemy.debuffs.keys())}", True, BLACK)
            surface.blit(debuffs_text, (enemy_x, enemy_y + 160))

        # status effects
        status_effects = []
        if enemy.is_frozen:
            status_effects.append("Frozen")
        if enemy.is_petrified:
            status_effects.append("Petrified")
        if enemy.shield:
            status_effects.append(f"Shielded ({enemy.shield['type']})")

        if status_effects:
            status_text = font.render(f"Status: {', '.join(status_effects)}", True, BLACK)
            surface.blit(status_text, (enemy_x, enemy_y + 190))

        # enemy selector
        enemy_rect = pygame.Rect(enemy_x - 10, enemy_y - 10, enemy_width, enemy_height)
        enemy.rect = enemy_rect
        if enemies and enemy == enemies[selected_enemy_index]:
            pygame.draw.rect(surface, BLUE, enemy_rect, 2)
        else:
            pygame.draw.rect(surface, BLACK, enemy_rect, 1)

def display_logs(surface, logs):
    # log messages
    max_logs = 10
    log_area_height = max_logs * 20 + 10
    start_y = HEIGHT - log_area_height - 10
    log_background = pygame.Rect(220, start_y - 5, WIDTH - 440, log_area_height + 10)
    pygame.draw.rect(surface, LIGHT_GRAY, log_background)
    for i, message in enumerate(logs[-max_logs:]):
        log_text = font.render(message, True, BLACK)
        surface.blit(log_text, (230, start_y + i * 20))
def draw_current_actor(surface):
    if not turn_order:
        return
    actor = turn_order[current_actor_index]
    if actor.type == 'Player':
        player_info = f"Current Player: {actor.name} - Element: {actor.element}"
    else:
        player_info = f"Current Enemy: {actor.name}"
    player_text = font.render(player_info, True, BLACK)
    surface.blit(player_text, (220, 10))

def draw_players_info(surface):
    y_offset = 10
    x_offset = WIDTH - 320  
    for idx, player in enumerate(players):
        current_marker = ">> " if turn_order and turn_order[current_actor_index] == player else ""
        player_info = f"{current_marker}{idx + 1}. {player.name} - Element: {player.element}"
        player_text = font.render(player_info, True, BLACK)
        surface.blit(player_text, (x_offset, y_offset + idx * 70))

    
        hp_bar_length = 180
        hp_bar_height = 20
        fill = max((player.current_hp / player.max_hp) * hp_bar_length, 0)
        pygame.draw.rect(surface, RED, (x_offset, y_offset + idx * 70 + 30, hp_bar_length, hp_bar_height))
        pygame.draw.rect(surface, GREEN, (x_offset, y_offset + idx * 70 + 30, fill, hp_bar_height))
        hp_text = font.render(f"HP: {player.current_hp:.2f}/{player.max_hp}", True, BLACK)
        surface.blit(hp_text, (x_offset, y_offset + idx * 70 + 55))

# =====================================================================================================
#                                   Menu and character creation
# =====================================================================================================
def main_menu():
    menu_running = True
    clock = pygame.time.Clock()

    players = []
    if os.path.exists('players.pkl'):
        with open('players.pkl', 'rb') as f:
            players = pickle.load(f)
            # Reset players' current HP to max HP at the start of the game
            for player in players:
                player.current_hp = player.max_hp

    # Buttons
    create_player_btn = Button(150, 400, 150, 40, "Create New Player", None)
    start_game_btn = Button(320, 400, 100, 40, "Start Game", None)
    roll_initiative_btn = Button(440, 400, 150, 40, "Roll Initiative", None)

    def create_player_callback():
        nonlocal creating_player
        creating_player = True

    def start_game_callback():
        if players:
            nonlocal menu_running
            menu_running = False
            with open('players.pkl', 'wb') as f:
                pickle.dump(players, f)

    def roll_initiative_callback():
        for idx, player in enumerate(players):
            player.initiative = random.randint(1, 20)
            if idx < len(initiative_inputs):
                initiative_inputs[idx].text = str(player.initiative)
                initiative_inputs[idx].txt_surface = font.render(initiative_inputs[idx].text, True, BLACK)

    create_player_btn.callback = create_player_callback
    start_game_btn.callback = start_game_callback
    roll_initiative_btn.callback = roll_initiative_callback

    # text inputs for player attributes
    name_input = TextInput(150, 50, 200, 32, '')
    hp_input = TextInput(150, 100, 200, 32, '')
    ac_input = TextInput(150, 150, 200, 32, '')
    movement_input = TextInput(150, 200, 200, 32, '')
    initiative_input = TextInput(150, 250, 200, 32, '')

    # Labels
    name_label = font.render("Name:", True, BLACK)
    hp_label = font.render("Max HP:", True, BLACK)
    ac_label = font.render("AC:", True, BLACK)
    movement_label = font.render("Movement:", True, BLACK)
    initiative_label = font.render("Initiative:", True, BLACK)

    # Element selection
    selected_element = None

    def set_selected_element(elem):
        nonlocal selected_element
        selected_element = elem

    element_buttons = []
    button_width, button_height = 100, 40
    x_start = 150
    y = 300
    for i, elem in enumerate(elements):
        x = x_start + i * (button_width + 5)
        btn = Button(x, y, button_width, button_height, elem, lambda e=elem: set_selected_element(e))
        element_buttons.append(btn)

    creating_player = False
    initiative_inputs = [] 
    remove_buttons = []     

    while menu_running:
        window.fill(WHITE)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            if creating_player:
                name_input.handle_event(event)
                hp_input.handle_event(event)
                ac_input.handle_event(event)
                movement_input.handle_event(event)
                initiative_input.handle_event(event)
            else:
                for init_input in initiative_inputs:
                    init_input.handle_event(event)

            if event.type == pygame.MOUSEBUTTONDOWN:
                pos = pygame.mouse.get_pos()
                if creating_player:
                    for btn in element_buttons:
                        if btn.is_clicked(pos):
                            btn.callback()
                    if create_player_btn.is_clicked(pos):
                        name = name_input.text
                        max_hp = int(hp_input.text) if hp_input.text else 0
                        ac = int(ac_input.text) if ac_input.text else 0
                        movement = int(movement_input.text) if movement_input.text else 0
                        initiative = int(initiative_input.text) if initiative_input.text else random.randint(1, 20)
                        if name and selected_element:
                            player = Player(name, max_hp, ac, movement, initiative, element=selected_element)
                            players.append(player)
                            name_input.text = ''
                            name_input.txt_surface = font.render('', True, BLACK)
                            hp_input.text = ''
                            hp_input.txt_surface = font.render('', True, BLACK)
                            ac_input.text = ''
                            ac_input.txt_surface = font.render('', True, BLACK)
                            movement_input.text = ''
                            movement_input.txt_surface = font.render('', True, BLACK)
                            initiative_input.text = ''
                            initiative_input.txt_surface = font.render('', True, BLACK)
                            selected_element = None
                            creating_player = False
                        else:
                            # i forgot what i needed to put here
                            pass
                else:
                    if create_player_btn.is_clicked(pos):
                        create_player_btn.callback()
                    elif start_game_btn.is_clicked(pos):
                        start_game_btn.callback()
                    elif roll_initiative_btn.is_clicked(pos):
                        roll_initiative_btn.callback()
                    for btn in element_buttons:
                        if btn.is_clicked(pos):
                            btn.callback()
                    for btn, idx in remove_buttons:
                        if btn.is_clicked(pos):
                            del players[idx]
                            del initiative_inputs[idx]
                            # Save updated players list to players.pkl
                            with open('players.pkl', 'wb') as f:
                                pickle.dump(players, f)
                            break 

        if creating_player:
            # draw stiuff
            window.blit(name_label, (50, 58))
            name_input.draw(window)
            window.blit(hp_label, (50, 108))
            hp_input.draw(window)
            window.blit(ac_label, (50, 158))
            ac_input.draw(window)
            window.blit(movement_label, (50, 208))
            movement_input.draw(window)
            window.blit(initiative_label, (50, 258))
            initiative_input.draw(window)

        
            for btn in element_buttons:
                btn.draw(window)

            selected_element_text = font.render(f"Selected Element: {selected_element}", True, BLACK)
            window.blit(selected_element_text, (150, y + button_height + 10))
            create_player_btn.draw(window)
        else:
            y_offset = 50
            window.blit(large_font.render("Existing Players:", True, BLACK), (50, y_offset))
            y_offset += 30
            remove_buttons = []
            for idx, player in enumerate(players):
                player_info = f"{idx + 1}. {player.name} - HP: {player.max_hp}, AC: {player.ac}, Movement: {player.movement}, Element: {player.element}"
                player_text = font.render(player_info, True, BLACK)
                window.blit(player_text, (50, y_offset + idx * 60))
                remove_btn = Button(600, y_offset + idx * 60, 80, 30, "Remove", None)
                remove_buttons.append((remove_btn, idx))
                remove_btn.draw(window)
                if idx >= len(initiative_inputs):
    
                    init_input = TextInput(700, y_offset + idx * 60, 60, 30, str(player.initiative))
                    initiative_inputs.append(init_input)
                else:
                    init_input = initiative_inputs[idx]

                init_label = font.render("Initiative:", True, BLACK)
                window.blit(init_label, (700, y_offset + idx * 60 - 20))
                init_input.draw(window)

                if init_input.text:
                    try:
                        player.initiative = int(init_input.text)
                    except ValueError:
                        pass 

            create_player_btn.draw(window)
            start_game_btn.draw(window)
            roll_initiative_btn.draw(window)

        pygame.display.flip()
        clock.tick(30)

    players.sort(key=lambda x: x.initiative, reverse=True)

    return players


players = main_menu()
current_actor_index = 0

# hardcoded tests
enemies = [
    Enemy("Harin", 120, defense=0, initiative=random.randint(1, 20)),
    Enemy("Sigurd", 300, defense=10, initiative=random.randint(1, 20)),
]

selected_enemy_index = 0
log_messages = []

# create rurn order from initiative
turn_order = players + enemies
turn_order.sort(key=lambda x: x.initiative, reverse=True)
current_actor_index = 0

buttons = []
button_width, button_height = 180, 40  # Adjusted button width
base_attack_btn = Button(10, 10, button_width, button_height, "Attack", perform_base_attack)
buttons.append(base_attack_btn)
dice_buttons = []
dice_types = {'d4':4, 'd6':6, 'd8':8, 'd10':10, 'd12':12, 'd20':20}
selected_dice = None

def set_selected_dice(dice_value):
    global selected_dice
    selected_dice = dice_value

x_offset = 10
y_offset = 60
for dice_name, dice_value in dice_types.items():
    btn = Button(x_offset, y_offset, button_width, button_height, dice_name, lambda v=dice_value: set_selected_dice(v))
    dice_buttons.append(btn)
    y_offset += button_height + 5

dice_quantity_input = TextInput(10, y_offset + 10, button_width, 32, '1')
dice_quantity_label = font.render("Dice Quantity:", True, BLACK)
damage_override_input = TextInput(10, y_offset + 60, button_width, 32, '')
damage_override_label = font.render("Damage Override:", True, BLACK)
enemy_damage_input = TextInput(10, y_offset + 110, button_width, 32, '10')
enemy_damage_label = font.render("Enemy Damage:", True, BLACK)
selected_dice_text_position = y_offset + 160

# GAME LOOP:
running = True
clock = pygame.time.Clock()

while running:
    window.fill(WHITE)

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        dice_quantity_input.handle_event(event)
        damage_override_input.handle_event(event)
        enemy_damage_input.handle_event(event)

        if event.type == pygame.MOUSEBUTTONDOWN:
            pos = pygame.mouse.get_pos()
            for button in buttons:
                if button.is_clicked(pos):
                    button.callback()
            for btn in dice_buttons:
                if btn.is_clicked(pos):
                    btn.callback()
            for idx, enemy in enumerate(enemies):
                if enemy.rect and enemy.rect.collidepoint(pos):
                    selected_enemy_index = idx

    for button in buttons:
        button.draw(window)
    for btn in dice_buttons:
        btn.draw(window)

    window.blit(dice_quantity_label, (10, dice_quantity_input.rect.y - 20))
    dice_quantity_input.draw(window)

    window.blit(damage_override_label, (10, damage_override_input.rect.y - 20))
    damage_override_input.draw(window)

    window.blit(enemy_damage_label, (10, enemy_damage_input.rect.y - 20))
    enemy_damage_input.draw(window)

    selected_dice_text = font.render(f"Selected Dice: d{selected_dice}", True, BLACK)
    window.blit(selected_dice_text, (10, selected_dice_text_position))

    draw_enemies_status(window, enemies)
    draw_current_actor(window)
    draw_players_info(window)
    display_logs(window, log_messages)

    pygame.display.flip()

    clock.tick(30)
pygame.quit()
sys.exit()
