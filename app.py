# -*- coding: utf-8 -*-
"""
Servidor Flask para la simulación de rescate táctico (Versión Hard-coded y Corregida).

Este script levanta un servidor web con un único endpoint '/run_simulation'
que, al ser llamado (vía GET), ejecuta la simulación con la configuración
definida internamente en el código. Los resultados se devuelven en formato JSON.
"""

from flask import Flask, jsonify
from mesa import Agent, Model
from mesa.space import MultiGrid
from mesa.time import RandomActivation
from mesa.datacollection import DataCollector
import numpy as np
from collections import defaultdict
import random

# --- Clases de la Simulación (Entidades) ---

class Hostage:
    def __init__(self, unique_id):
        self.unique_id = unique_id

class FalseAlarm:
    def __init__(self, unique_id):
        self.unique_id = unique_id

class Gate:
    def __init__(self, unique_id, is_open=False):
        self.unique_id = unique_id
        self.is_open = is_open

class Disturbance:
    def __init__(self, unique_id, severity='mild'):
        self.unique_id = unique_id
        self.severity = severity
        self.turns_in_current_state = 0

# --- Clase del Agente Táctico ---

class TacticalAgent(Agent):
    def __init__(self, unique_id, model):
        super().__init__(model)
        self.unique_id = unique_id
        self.action_points = 4
        self.carrying_hostage = False

    def step(self):
        self.action_points = 4
        while self.action_points > 0:
            possible_actions = []
            current_pos_contents = self.model.get_contents_at(self.pos)

            # 1. Moverse
            neighbors = self.model.grid.get_neighborhood(self.pos, moore=False, include_center=False)
            for neighbor_pos in neighbors:
                if self.model.can_move_to(self.pos, neighbor_pos):
                    neighbor_contents = self.model.get_contents_at(neighbor_pos)
                    cost = 2 if any(isinstance(c, Disturbance) for c in neighbor_contents) else 1
                    if self.action_points >= cost:
                        possible_actions.append(('move', neighbor_pos, cost))

            # 2. Rescatar rehén
            if not self.carrying_hostage:
                hostage_found = next((c for c in current_pos_contents if isinstance(c, Hostage)), None)
                if hostage_found and self.action_points >= 2:
                    possible_actions.append(('rescue', hostage_found, 2))

            # 3. Investigar falsa alarma
            alarm_found = next((c for c in current_pos_contents if isinstance(c, FalseAlarm)), None)
            if alarm_found and self.action_points >= 1:
                possible_actions.append(('investigate', alarm_found, 1))

            # 4. Dejar rehén
            if self.carrying_hostage and self.pos in self.model.entry_points and self.action_points >= 1:
                possible_actions.append(('dropoff', None, 1))

            # 5. Contener disturbio
            disturbance_found = next((c for c in current_pos_contents if isinstance(c, Disturbance)), None)
            if disturbance_found:
                if disturbance_found.severity == 'mild' and self.action_points >= 1:
                    possible_actions.append(('contain', disturbance_found, 1))
                elif disturbance_found.severity == 'active' and self.action_points >= 2:
                    possible_actions.append(('contain', disturbance_found, 2))

            # 6. Abrir/Cerrar reja
            gate_found = next((c for c in current_pos_contents if isinstance(c, Gate)), None)
            if gate_found and self.action_points >= 1:
                action_name = 'close_gate' if gate_found.is_open else 'open_gate'
                possible_actions.append((action_name, gate_found, 1))
            
            # 7. Derribar muro/reja
            if self.action_points >= 2:
                for neighbor_pos in self.model.grid.get_neighborhood(self.pos, moore=False, include_center=False):
                    if self.model.has_wall_between(self.pos, neighbor_pos):
                        possible_actions.append(('break_wall', neighbor_pos, 2))

            if not possible_actions:
                break
            
            action, target, cost = self.random.choice(possible_actions)

            if action == 'move':
                self.model.grid.move_agent(self, target)
            elif action == 'rescue':
                self.carrying_hostage = True
                self.model.remove_entity(target, self.pos)
            elif action == 'investigate':
                self.model.false_alarms_investigated += 1
                self.model.remove_entity(target, self.pos)
            elif action == 'dropoff':
                self.carrying_hostage = False
                self.model.hostages_rescued += 1
            elif action == 'contain':
                self.model.remove_entity(target, self.pos)
            elif action == 'open_gate':
                target.is_open = True
            elif action == 'close_gate':
                target.is_open = False
            elif action == 'break_wall':
                self.model.break_wall_between(self.pos, target)
                self.model.structural_damage += 1
            
            self.action_points -= cost

# --- Función de Visualización para el DataCollector ---

def get_grid_state(model):
    """ Captura el estado del grid en un formato JSON-compatible. """
    grid_data = np.zeros((model.grid.width, model.grid.height), dtype=int)
    
    # Mapeo de valores para Unity
    for x in range(model.grid.width):
        for y in range(model.grid.height):
            pos = (x, y)
            contents = model.get_contents_at(pos)
            
            if any(isinstance(c, TacticalAgent) for c in contents): grid_data[x, y] = 2
            elif any(isinstance(c, Hostage) for c in contents): grid_data[x, y] = 3
            elif any(isinstance(c, Disturbance) for c in contents):
                d = next(c for c in contents if isinstance(c, Disturbance))
                if d.severity == 'grave': grid_data[x, y] = 8
                elif d.severity == 'active': grid_data[x, y] = 5
                else: grid_data[x, y] = 4
            elif any(isinstance(c, FalseAlarm) for c in contents): grid_data[x, y] = 7
            elif any(isinstance(c, Gate) for c in contents):
                g = next(c for c in contents if isinstance(c, Gate))
                grid_data[x, y] = 9 if g.is_open else 10
            elif pos in model.entry_points: grid_data[x, y] = 6

    # ***** INICIO DE LA CORRECCIÓN *****
    # Convertir las llaves de tupla del diccionario de muros a strings.
    # Por ejemplo, la llave (0, 1) se convierte en "0,1".
    walls_serializable = {f"{x},{y}": data for (x, y), data in model.walls.items()}
    # ***** FIN DE LA CORRECCIÓN *****

    return {
        "grid": grid_data.T.tolist(),
        "walls": walls_serializable  # Usamos el diccionario corregido
    }


# --- Modelo Principal de la Simulación ---

class RescueModel(Model):
    def __init__(self, width=8, height=6):
        super().__init__()
        self.grid = MultiGrid(width, height, torus=False)
        self.schedule = RandomActivation(self)
        self.cell_contents = defaultdict(list)
        self.running = True
        self.hostages_rescued = 0
        self.hostages_lost = 0
        self.structural_damage = 0
        self.false_alarms_investigated = 0
        self.next_entity_id = 0
        self.turn_counter = 0
        self.min_hidden_markers = 3

        self.setup_fixed_grid()
        self.datacollector = DataCollector(model_reporters={"GridState": get_grid_state})

    def get_next_id(self):
        self.next_entity_id += 1
        return self.next_entity_id

    def get_contents_at(self, pos):
        return self.grid.get_cell_list_contents([pos]) + self.cell_contents.get(pos, [])

    def remove_entity(self, entity, pos):
        if pos in self.cell_contents and entity in self.cell_contents[pos]:
            self.cell_contents[pos].remove(entity)

    def setup_fixed_grid(self):
        # --- CONFIGURACIÓN HARD-CODED ---
        grid_walls = [
            ["1100", "1000", "1001", "1100", "1001", "1100", "1000", "1001"],
            ["0100", "0000", "0011", "0110", "0011", "0110", "0010", "0011"],
            ["0100", "0001", "1100", "1000", "1000", "1001", "1100", "1001"],
            ["0110", "0011", "0110", "0010", "0010", "0011", "0110", "0011"],
            ["1100", "1000", "1000", "1000", "1001", "1100", "1001", "1101"],
            ["0110", "0010", "0010", "0010", "0011", "0110", "0011", "0111"]
        ]
        points_of_interest = [(2, 5, 'v'), (5, 2, 'f'), (5, 8, 'v')]
        fire_markers = [(2, 2), (2, 3), (3, 2), (3, 3), (3, 4), (3, 5), (4, 4), (5, 6), (5, 7), (6, 6)]
        doors = [(1, 3, 1, 4), (2, 5, 2, 6), (2, 8, 3, 8), (3, 2, 3, 3), (4, 4, 5, 4), (4, 6, 4, 7), (6, 5, 6, 6), (6, 7, 6, 8)]
        entry_points_data = [(1, 6), (3, 1), (4, 8), (6, 3)]
        num_agents = 6

        self.walls = {}
        for row in range(self.grid.height):
            for col in range(self.grid.width):
                pos = (col, row)
                cell_walls_str = grid_walls[row][col]
                self.walls[pos] = {'top': cell_walls_str[0] == '1', 'left': cell_walls_str[1] == '1', 'bottom': cell_walls_str[2] == '1', 'right': cell_walls_str[3] == '1'}
        
        self.entry_points = [(c - 1, r - 1) for r, c in entry_points_data]

        for i in range(num_agents):
            agent = TacticalAgent(self.get_next_id(), self)
            self.schedule.add(agent)
            self.grid.place_agent(agent, random.choice(self.entry_points))
        
        for r, c, poi_type in points_of_interest:
            pos = (c - 1, r - 1)
            if poi_type == 'v': self.cell_contents[pos].append(Hostage(self.get_next_id()))
            elif poi_type == 'f': self.cell_contents[pos].append(FalseAlarm(self.get_next_id()))

        for r, c in fire_markers:
            self.cell_contents[(c - 1, r - 1)].append(Disturbance(self.get_next_id(), 'mild'))
        
        for r1, c1, r2, c2 in doors:
            self.cell_contents[(c1 - 1, r1 - 1)].append(Gate(self.get_next_id(), random.choice([True, False])))

    def can_move_to(self, from_pos, to_pos):
        from_x, from_y = from_pos
        to_x, to_y = to_pos
        if not (0 <= to_x < self.grid.width and 0 <= to_y < self.grid.height): return False
        
        dx, dy = to_x - from_x, to_y - from_y
        walls = self.walls.get(from_pos, {})
        if (dx == 1 and walls.get('right')) or (dx == -1 and walls.get('left')) or \
           (dy == 1 and walls.get('bottom')) or (dy == -1 and walls.get('top')):
            return False
        
        gates = [g for g in self.get_contents_at(to_pos) if isinstance(g, Gate)]
        if gates and not gates[0].is_open: return False
        
        return True

    def has_wall_between(self, pos1, pos2):
        dx, dy = pos2[0] - pos1[0], pos2[1] - pos1[1]
        walls1 = self.walls.get(pos1, {})
        return (dx == 1 and walls1.get('right')) or (dx == -1 and walls1.get('left')) or \
               (dy == 1 and walls1.get('bottom')) or (dy == -1 and walls1.get('top'))

    def break_wall_between(self, pos1, pos2):
        dx, dy = pos2[0] - pos1[0], pos2[1] - pos1[1]
        if pos1 in self.walls:
            if dx == 1: self.walls[pos1]['right'] = False
            elif dx == -1: self.walls[pos1]['left'] = False
            elif dy == 1: self.walls[pos1]['bottom'] = False
            elif dy == -1: self.walls[pos1]['top'] = False
        if pos2 in self.walls:
            if dx == 1: self.walls[pos2]['left'] = False
            elif dx == -1: self.walls[pos2]['right'] = False
            elif dy == 1: self.walls[pos2]['top'] = False
            elif dy == -1: self.walls[pos2]['bottom'] = False
    
    def get_available_cell(self):
        while True:
            pos = (self.random.randrange(self.grid.width), self.random.randrange(self.grid.height))
            if not any(isinstance(c, Gate) and not c.is_open for c in self.get_contents_at(pos)):
                return pos
    
    def advance_disturbances(self):
        for pos, contents in list(self.cell_contents.items()):
            for d in [c for c in contents if isinstance(c, Disturbance)]:
                d.turns_in_current_state += 1
                if d.severity == 'mild' and d.turns_in_current_state >= 4:
                    d.severity = 'active'; d.turns_in_current_state = 0
                elif d.severity == 'active' and d.turns_in_current_state >= 6:
                    d.severity = 'grave'
                    self.handle_explosion(pos, list(contents))
        
        if self.random.random() < 0.05:
            pos = self.get_available_cell()
            if not any(isinstance(c, Disturbance) for c in self.get_contents_at(pos)):
                self.cell_contents[pos].append(Disturbance(self.get_next_id(), 'mild'))

    def handle_explosion(self, pos, contents):
        self.structural_damage += 1
        for hostage in [h for h in contents if isinstance(h, Hostage)]:
            self.hostages_lost += 1
            self.remove_entity(hostage, pos)
        for disturbance in [d for d in contents if isinstance(d, Disturbance)]:
            self.remove_entity(disturbance, pos)

    def check_game_over(self):
        if self.hostages_rescued >= 7 or self.hostages_lost >= 4 or self.structural_damage >= 25:
            self.running = False
    
    def step(self):
        self.turn_counter += 1
        self.schedule.step()
        self.advance_disturbances()
        self.check_game_over()
        self.datacollector.collect(self)
    
    def get_final_stats(self):
        result = "TIEMPO AGOTADO"
        if self.hostages_rescued >= 7: result = "VICTORIA"
        elif self.hostages_lost >= 4: result = "DERROTA (Muchas víctimas perdidas)"
        elif self.structural_damage >= 25: result = "DERROTA (Colapso estructural)"
        
        return {
            "result": result, "total_steps": self.turn_counter,
            "hostages_rescued": self.hostages_rescued, "hostages_lost": self.hostages_lost,
            "structural_damage": self.structural_damage,
            "false_alarms_investigated": self.false_alarms_investigated
        }

# --- Inicialización de Flask y Definición del Endpoint ---

app = Flask(__name__)

@app.route('/run_simulation', methods=['GET'])
def run_simulation():
    max_steps = 500
    model = RescueModel()
    for _ in range(max_steps):
        if not model.running: break
        model.step()
    
    simulation_data = model.datacollector.get_model_vars_dataframe()
    
    response_data = {
        "final_stats": model.get_final_stats(),
        "steps_data": [{"step": i, "grid_state": row["GridState"]} for i, row in simulation_data.iterrows()]
    }
    
    return jsonify(response_data)

# --- Ejecución del Servidor ---

if __name__ == '__main__':
    app.run(debug=True, port=5000)