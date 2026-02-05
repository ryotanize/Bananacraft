import math

class Terraformer:
    def __init__(self, rcon_client):
        self.rcon = rcon_client

    def terraform(self, origin, width=200, depth=200, base_y=64):
        """
        Clears the area and creates a flat foundation.
        origin: (x, y, z) tuple - The North-West corner of the area.
        width, depth: dimensions of the area.
        base_y: The Y level of the floor (ground level).
        """
        ox, oy, oz = origin
        cmds = []
        
        # 1. Force Load the area to prevent command failures
        # Calculate chunk coords
        c1_x = math.floor(ox / 16)
        c1_z = math.floor(oz / 16)
        c2_x = math.floor((ox + width) / 16)
        c2_z = math.floor((oz + depth) / 16)
        
        cmds.append(f"forceload add {c1_x} {c1_z} {c2_x} {c2_z}")
        
        # 2. Split area into smaller chunks for /fill (max vol 32768)
        # 30x30x50 = 45000 (Too big)
        # 20x20x50 = 20000 (Safe)
        
        chunk_size = 20
        height_clear = 50
        
        print(f"Terraforming area starting at {origin} ({width}x{depth})...")
        
        for x in range(0, width, chunk_size):
            for z in range(0, depth, chunk_size):
                # Calculate bounds for this chunk
                x1 = ox + x
                z1 = oz + z
                x2 = min(ox + x + chunk_size - 1, ox + width - 1)
                z2 = min(oz + z + chunk_size - 1, oz + depth - 1)
                
                # A. Clear Air (Above ground)
                # Minecraft max height is usually 320. Base is often 64.
                # We need to clear from base_y up to 320.
                # 20x20 area = 400 blocks per layer.
                # Max volume 32768 / 400 = 81 layers safe.
                # So we can do chunks of 80 height safely.
                
                max_height = 320
                start_h = base_y
                
                while start_h < max_height:
                    end_h = min(start_h + 80, max_height)
                    cmd_air = f"fill {x1} {start_h} {z1} {x2} {end_h} {z2} air"
                    cmds.append(cmd_air)
                    start_h += 80  # Next segment overlap not needed for air
                
                # B. Foundation (Ground level - 1)
                # /fill x1 y1 z1 x2 y2 z2 grass_block
                ground_y = base_y - 1
                cmd_floor = f"fill {x1} {ground_y} {z1} {x2} {ground_y} {z2} grass_block"
                cmds.append(cmd_floor)
                
                 # C. Deep Foundation (optional, ensuring no holes below)
                sub_y = base_y - 2
                cmd_sub = f"fill {x1} {sub_y} {z1} {x2} {sub_y} {z2} stone"
                cmds.append(cmd_sub)

        # Execute
        print(f"Generated {len(cmds)} terraforming commands.")
        
        # Send in batches to avoid timeout?
        # RconClient handles valid connection, but large lists might block.
        # We'll rely on client implementation.
        logs = self.rcon.connect_and_send(cmds)
        return logs
