import asyncio
import json
import random
import math
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse

app = FastAPI()

class Bot:
    def __init__(self):
        self.pos = [random.uniform(-10, 10), random.uniform(-10, 10), random.uniform(-10, 10)]
        self.vel = [0.0, 0.0, 0.0]
        self.target = [0.0, 0.0, 0.0]
        self.max_speed = 1.5      # Increased from 0.5 for faster movement
        self.max_force = 0.5      # Increased limit
        self.repel_radius = 0.8   # Reduced to allow tight packing in lattice
        self.locked = False       # Lattice snap
        self.load_bearing = False # Structural support flag

class HiveMind:
    def __init__(self, num_bots: int):
        self.num_bots = num_bots
        self.bots = [Bot() for _ in range(num_bots)]
        self.shapes = ["sphere", "wall", "ring", "cube"]
        self.shape_idx = 0
        self.command_shape = self.shapes[self.shape_idx]
        self.assign_targets()

    def generate_sphere_targets(self):
        targets = []
        radius = 10.0
        # Simple random points in sphere
        for _ in range(self.num_bots):
            theta = random.uniform(0, 2 * math.pi)
            phi = math.acos(random.uniform(-1, 1))
            x = radius * math.sin(phi) * math.cos(theta)
            y = radius * math.sin(phi) * math.sin(theta)
            z = radius * math.cos(phi)
            targets.append([x, y, z])
        return targets
        
    def generate_wall_targets(self):
        targets = []
        size = int(math.ceil(math.sqrt(self.num_bots)))
        spacing = 1.5
        for i in range(self.num_bots):
            x = ((i % size) - size//2) * spacing
            y = ((i // size) - size//2) * spacing
            z = 0.0
            targets.append([x, y, z])
        return targets

    def generate_ring_targets(self):
        targets = []
        radius = 15.0
        for i in range(self.num_bots):
            theta = (i / self.num_bots) * 2.0 * math.pi
            x = radius * math.cos(theta)
            y = 0.0
            z = radius * math.sin(theta)
            targets.append([x, y, z])
        return targets

    def generate_cube_targets(self):
        targets = []
        side = int(round(self.num_bots ** (1. / 3.)))
        if side == 0: side = 1
        spacing = 2.0
        for i in range(self.num_bots):
            x = ((i % side) - side / 2.0) * spacing
            y = (((i // side) % side) - side / 2.0) * spacing
            z = ((i // (side * side)) - side / 2.0) * spacing
            targets.append([x, y, z])
        return targets

    def assign_targets(self):
        if self.command_shape == "sphere":
            targets = self.generate_sphere_targets()
        elif self.command_shape == "wall":
            targets = self.generate_wall_targets()
        elif self.command_shape == "ring":
            targets = self.generate_ring_targets()
        else:
            targets = self.generate_cube_targets()
            
        # Greedy assignment to nearest target to prevent traffic jams
        unassigned_targets = list(targets)
        for bot in self.bots:
            # Find closest available target
            closest_tgt = min(unassigned_targets, key=lambda t: math.hypot(
                math.hypot(bot.pos[0]-t[0], bot.pos[1]-t[1]), bot.pos[2]-t[2]
            ))
            bot.target = closest_tgt
            unassigned_targets.remove(closest_tgt)
            
            # Release latches on shape change
            bot.locked = False
            bot.load_bearing = False

    def update(self):
        # 1. Docking / Latching Logic
        for b in self.bots:
            if not b.locked:
                dx = b.target[0] - b.pos[0]
                dy = b.target[1] - b.pos[1]
                dz = b.target[2] - b.pos[2]
                dist_to_target = math.hypot(math.hypot(dx, dy), dz)
                # If close to target slot, dock and lock into the lattice
                if dist_to_target < 0.6:
                    b.locked = True
                    b.pos = list(b.target)
                    b.vel = [0.0, 0.0, 0.0]

        # 2. Physics for Free Bots
        for i, b in enumerate(self.bots):
            if b.locked:
                continue

            # 1. Seek target
            steer = [b.target[j] - b.pos[j] for j in range(3)]
            dist = math.hypot(math.hypot(steer[0], steer[1]), steer[2])
            if dist > 0:
                steer = [(s / dist) * b.max_speed for s in steer]
                steer = [steer[j] - b.vel[j] for j in range(3)]
            
            # 2. Separation force and Reinforcement Pull
            sep = [0.0, 0.0, 0.0]
            reinforce_pull = [0.0, 0.0, 0.0]
            count = 0
            
            for j, other in enumerate(self.bots):
                if i != j:
                    diff = [b.pos[k] - other.pos[k] for k in range(3)]
                    d = math.hypot(math.hypot(diff[0], diff[1]), diff[2])
                    
                    if 0 < d < b.repel_radius:
                        sep = [sep[k] + (diff[k] / d) for k in range(3)]
                        count += 1
                        
                    # Structural Support: Pull free bots towards load-bearing nodes smoothly
                    if other.load_bearing and 0 < d < 5.0:
                        reinforce_pull = [reinforce_pull[k] - (diff[k] / d) * 0.05 for k in range(3)]

            if count > 0:
                sep = [s / count for s in sep]
            
            # Apply forces
            for k in range(3):
                # Steering gets higher weight to overcome random separation clusters
                b.vel[k] = (b.vel[k] + steer[k] * 0.5 + sep[k] * 0.4 + reinforce_pull[k]) * 0.90
                # Clamp velocity
                if b.vel[k] > b.max_speed: b.vel[k] = b.max_speed
                if b.vel[k] < -b.max_speed: b.vel[k] = -b.max_speed
                
                b.pos[k] += b.vel[k]

        # 3. Load-Bearing Assessment
        for b in self.bots:
            b.load_bearing = False
            if b.locked:
                # Naive structural check: if locked, and another bot is locked directly above it
                for other in self.bots:
                    if other is not b and other.locked:
                        dx = abs(other.pos[0] - b.pos[0])
                        dz = abs(other.pos[2] - b.pos[2])
                        dy = other.pos[1] - b.pos[1]
                        # Only consider it load_bearing if someone is resting its weight on it
                        if dx < 0.5 and dz < 0.5 and 0.5 < dy < 2.5:
                            b.load_bearing = True
                            break

hive = HiveMind(512)

@app.get("/")
async def get():
    with open("index.html", "r") as f:
        return HTMLResponse(f.read())

@app.get("/set_shape/{shape}")
async def set_shape(shape: str):
    if shape in hive.shapes:
        hive.command_shape = shape
        hive.shape_idx = hive.shapes.index(shape)
        hive.assign_targets()
    return {"shape": hive.command_shape}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            hive.update()
            
            positions = [
                {
                    "x": b.pos[0], "y": b.pos[1], "z": b.pos[2],
                    "s": 2 if b.load_bearing else (1 if b.locked else 0)
                }
                for b in hive.bots
            ]
            
            await websocket.send_text(json.dumps({"positions": positions}))
            await asyncio.sleep(0.05)  
            
    except WebSocketDisconnect:
        print("Client disconnected")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
