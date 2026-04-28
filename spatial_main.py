import asyncio
import json
import random
import math
import time
from PIL import Image, ImageDraw, ImageFont
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse

app = FastAPI()

class Bot:
    def __init__(self):
        self.pos = [random.uniform(-20, 20), random.uniform(-20, 20), random.uniform(-20, 20)]
        self.vel = [0.0, 0.0, 0.0]
        self.target = [0.0, 0.0, 0.0]
        self.max_speed = 1.5
        self.repel_radius = 0.8
        self.locked = False

class SpatialHash:
    def __init__(self, cell_size: float):
        self.cell_size = cell_size
        self.grid = {}

    def _hash(self, pos):
        return (
            int(math.floor(pos[0] / self.cell_size)),
            int(math.floor(pos[1] / self.cell_size)),
            int(math.floor(pos[2] / self.cell_size))
        )

    def clear(self):
        self.grid.clear()

    def insert(self, bot, bot_index):
        h = self._hash(bot.pos)
        if h not in self.grid:
            self.grid[h] = []
        self.grid[h].append(bot_index)

    def get_nearby_bots(self, pos):
        h = self._hash(pos)
        nearby = []
        # Check the cell and all 26 neighboring cells
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for dz in (-1, 0, 1):
                    cell = (h[0] + dx, h[1] + dy, h[2] + dz)
                    if cell in self.grid:
                        nearby.extend(self.grid[cell])
        return nearby


class HiveMind:
    def __init__(self, num_bots: int):
        self.num_bots = num_bots
        self.bots = [Bot() for _ in range(num_bots)]
        self.shapes = ["sphere", "wall", "ring", "cube", "rim", "tokamak", "arc_reactor"]
        self.shape_idx = 0
        self.command_shape = self.shapes[self.shape_idx]
        self.spatial_hash = SpatialHash(cell_size=1.0) # Larger than repel_radius
        self.custom_text = "HELLO"
        self.assign_targets()

    def generate_sphere_targets(self):
        targets = []
        radius = 20.0
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
        cols = int(math.ceil(math.sqrt(self.num_bots)))
        rows = int(math.ceil(self.num_bots / cols))
        
        R = 0.44  # Hex radius
        spacing_x = math.sqrt(3) * R
        spacing_y = 1.5 * R

        for i in range(self.num_bots):
            col = i % cols
            row = i // cols
            
            x = (col - cols/2.0) * spacing_x
            if row % 2 == 1:
                x += spacing_x / 2.0
                
            y = (row - rows/2.0) * spacing_y
            z = 0.0
            targets.append([x, y, z])
            
        return targets

    def generate_ring_targets(self):
        targets = []
        radius = 25.0
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
        spacing = 1.5
        for i in range(self.num_bots):
            x = ((i % side) - side / 2.0) * spacing
            y = (((i // side) % side) - side / 2.0) * spacing
            z = ((i // (side * side)) - side / 2.0) * spacing
            targets.append([x, y, z])
        return targets

    def generate_rim_targets(self):
        # A mathematical approximation of a 5-spoke car wheel rim
        targets = []
        rim_bots = int(self.num_bots * 0.45)   # 45% for the outer barrel
        hub_bots = int(self.num_bots * 0.15)   # 15% for the center hub
        spokes = 5
        spoke_bots = (self.num_bots - rim_bots - hub_bots) // spokes
        
        r_outer = 18.0
        r_inner = 3.0
        thickness = 4.0

        # Outer Barrel
        for i in range(rim_bots):
            theta = (i / rim_bots) * 2.0 * math.pi
            z = ((i % 3) - 1.0) * thickness * 0.8
            targets.append([r_outer * math.cos(theta), r_outer * math.sin(theta), z])

        # Center Hub
        for i in range(hub_bots):
            theta = (i / hub_bots) * 2.0 * math.pi
            z = ((i % 3) - 1.0) * thickness * 0.5
            targets.append([r_inner * math.cos(theta), r_inner * math.sin(theta), z])

        # 5 Spokes connecting inner and outer
        for s in range(spokes):
            angle = (s / spokes) * 2.0 * math.pi
            current_spoke_bots = spoke_bots + (1 if s < (self.num_bots - rim_bots - hub_bots) % spokes else 0)
            for i in range(current_spoke_bots):
                f = i / (current_spoke_bots - 1) if current_spoke_bots > 1 else 0.5
                r = r_inner + f * (r_outer - r_inner)
                z = ((i % 2) - 0.5) * thickness * 0.5
                targets.append([r * math.cos(angle), r * math.sin(angle), z])

        # Failsafe pad/trim
        while len(targets) < self.num_bots:
            targets.append([0.0, 0.0, 0.0])
        return targets[:self.num_bots]

    def generate_tokamak_targets(self):
        targets = []
        R = 15.0  # Major radius
        r = 5.0   # Minor radius
        for _ in range(self.num_bots):
            u = random.uniform(0, 2 * math.pi)
            v = random.uniform(0, 2 * math.pi)
            x = (R + r * math.cos(v)) * math.cos(u)
            z = (R + r * math.cos(v)) * math.sin(u)
            y = r * math.sin(v)
            targets.append([x, y, z])
        return targets

    def generate_arc_reactor_targets(self):
        targets = []
        core_bots = int(self.num_bots * 0.20)
        inner_ring_bots = int(self.num_bots * 0.40)
        outer_ring_bots = int(self.num_bots * 0.25)
        strut_bots = self.num_bots - core_bots - inner_ring_bots - outer_ring_bots
        
        # 1. Glowing Core (dense sphere)
        for _ in range(core_bots):
            theta = random.uniform(0, 2 * math.pi)
            phi = math.acos(random.uniform(-1, 1))
            r = random.uniform(0.0, 4.0)
            x = r * math.sin(phi) * math.cos(theta)
            y = r * math.sin(phi) * math.sin(theta)
            z = r * math.cos(phi)
            # Flatten slightly on Z
            targets.append([x, y, z * 0.5])
            
        # 2. Inner Ring (thick and compact)
        for _ in range(inner_ring_bots):
            theta = random.uniform(0, 2 * math.pi)
            r = random.uniform(8.0, 11.0)
            z = random.uniform(-1.5, 1.5)
            targets.append([r * math.cos(theta), r * math.sin(theta), z])
            
        # 3. Outer Ring (thin)
        for _ in range(outer_ring_bots):
            theta = random.uniform(0, 2 * math.pi)
            r = random.uniform(16.0, 17.5)
            z = random.uniform(-1.0, 1.0)
            targets.append([r * math.cos(theta), r * math.sin(theta), z])
            
        # 4. Struts (connecting inner and outer rings)
        num_struts = 10
        bots_per_strut = max(1, strut_bots // num_struts)
        for s in range(num_struts):
            angle = (s / num_struts) * 2 * math.pi
            for i in range(bots_per_strut):
                f = i / bots_per_strut
                r = 11.0 + f * (16.0 - 11.0)
                z = random.uniform(-0.5, 0.5)
                # Scatter slightly along the strut width
                p_angle = angle + random.uniform(-0.02, 0.02)
                targets.append([r * math.cos(p_angle), r * math.sin(p_angle), z])
                
        # Fill remainder with center points if any are lost due to rounding
        while len(targets) < self.num_bots:
            targets.append([0.0, 0.0, 0.0])
            
        return targets[:self.num_bots]

    def generate_text_targets(self):
        # 1. Create a 2D blank canvas
        img = Image.new('1', (150, 40), color=0)
        d = ImageDraw.Draw(img)
        
        # 2. Draw text using a default built-in font
        try:
            f = ImageFont.load_default()
            d.text((10, 10), self.custom_text, font=f, fill=1)
        except:
            d.text((10, 10), self.custom_text, fill=1)

        # 3. Extract the 1s (white pixels) into a list of 3D coordinates
        pixels = []
        for x in range(img.width):
            for y in range(img.height):
                if img.getpixel((x, y)) > 0:
                    # Scale pixel spacing up
                    gx = (x - 75) * 0.4
                    gy = -(y - 20) * 0.4
                    pixels.append([gx, gy, random.uniform(-0.5, 0.5)])
        
        if not pixels:
            return self.generate_sphere_targets()

        # 4. We uniformly copy the pixels until we hit `self.num_bots` Exactly 
        # so all bots have somewhere to go
        targets = []
        for i in range(self.num_bots):
            t = pixels[i % len(pixels)]
            # Add slight jitter to thicken the shape
            z_jitter = random.uniform(-1.0, 1.0)
            xy_jitter = random.uniform(-0.1, 0.1)
            targets.append([t[0] + xy_jitter, t[1] + xy_jitter, t[2] + z_jitter])
            
        return targets

    def assign_targets(self):
        if self.command_shape == "sphere":
            targets = self.generate_sphere_targets()
        elif self.command_shape == "wall":
            targets = self.generate_wall_targets()
        elif self.command_shape == "ring":
            targets = self.generate_ring_targets()
        elif self.command_shape == "cube":
            targets = self.generate_cube_targets()
        elif self.command_shape == "text":
            targets = self.generate_text_targets()
        elif self.command_shape == "tokamak":
            targets = self.generate_tokamak_targets()
        elif self.command_shape == "arc_reactor":
            targets = self.generate_arc_reactor_targets()
        else:
            targets = self.generate_rim_targets()
            
        # Fast greedy assignment
        unassigned = list(targets)
        for b in self.bots:
            closest = min(unassigned, key=lambda t: (b.pos[0]-t[0])**2 + (b.pos[1]-t[1])**2 + (b.pos[2]-t[2])**2)
            b.target = closest
            unassigned.remove(closest)
            b.locked = False

    def update(self):
        # 1. Populate Spatial Hash Grid
        self.spatial_hash.clear()
        for i, b in enumerate(self.bots):
            self.spatial_hash.insert(b, i)

        # 2. Docking Logic
        for b in self.bots:
            if not b.locked:
                dist_sq = (b.target[0] - b.pos[0])**2 + (b.target[1] - b.pos[1])**2 + (b.target[2] - b.pos[2])**2
                if dist_sq < 0.36: # 0.6 squared
                    b.locked = True
                    b.pos = list(b.target)
                    b.vel = [0.0, 0.0, 0.0]

        # 3. Physics via Spatial Partitioning
        for i, b in enumerate(self.bots):
            if b.locked:
                continue

            # Steer
            steer = [b.target[j] - b.pos[j] for j in range(3)]
            dist = math.hypot(math.hypot(steer[0], steer[1]), steer[2])
            if dist > 0:
                steer = [(s / dist) * b.max_speed - b.vel[j] for j, s in enumerate(steer)]
            
            # Separation (Using Spatial Hash instead of checking all bots)
            sep = [0.0, 0.0, 0.0]
            count = 0
            
            nearby_bot_indices = self.spatial_hash.get_nearby_bots(b.pos)
            for j in nearby_bot_indices:
                if i != j:
                    other = self.bots[j]
                    diff = [b.pos[k] - other.pos[k] for k in range(3)]
                    d_sq = diff[0]**2 + diff[1]**2 + diff[2]**2
                    
                    if 0 < d_sq < (b.repel_radius ** 2):
                        d = math.sqrt(d_sq)
                        sep = [sep[k] + (diff[k] / d) for k in range(3)]
                        count += 1

            if count > 0:
                sep = [s / count for s in sep]
            
            # Apply
            for k in range(3):
                b.vel[k] = (b.vel[k] + steer[k] * 0.4 + sep[k] * 0.6) * 0.9
                # Clamp velocity
                if b.vel[k] > b.max_speed: b.vel[k] = b.max_speed
                if b.vel[k] < -b.max_speed: b.vel[k] = -b.max_speed
                b.pos[k] += b.vel[k]

# Jumped from 512 to 2000 bots!
hive = HiveMind(1000)

@app.get("/")
async def get():
    with open("spatial_index.html", "r") as f:
        return HTMLResponse(f.read())

@app.get("/set_shape/{shape}")
async def set_shape(shape: str):
    if shape in hive.shapes or shape == 'text':
        hive.command_shape = shape
        hive.assign_targets()
    return {"shape": hive.command_shape}

@app.get("/set_text/{text}")
async def set_text(text: str):
    hive.custom_text = text.upper()
    hive.command_shape = "text"
    hive.assign_targets()
    return {"shape": f"Text: {hive.custom_text}"}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            # Measure time to log backend performance
            start_t = time.perf_counter()
            hive.update()
            end_t = time.perf_counter()
            
            positions = [{"x": b.pos[0], "y": b.pos[1], "z": b.pos[2]} for b in hive.bots]
            
            await websocket.send_text(json.dumps({"positions": positions}))
            # Roughly 20 fps
            await asyncio.sleep(max(0.01, 0.05 - (end_t - start_t)))
            
    except WebSocketDisconnect:
        print("Client disconnected")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("spatial_main:app", host="127.0.0.1", port=8000, reload=True)