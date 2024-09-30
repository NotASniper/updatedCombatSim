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
