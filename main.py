from ursina import *
from ursina.prefabs.first_person_controller import FirstPersonController
from random import uniform

app = Ursina(borderless=False)
window.title = 'HOME'
window.color = color.black
window.multisamples = 4  # Enable 4x MSAA (Anti-Aliasing)
mouse.visible = True

# -------------------------------
# GLOBAL STATE
# -------------------------------
game_state = 'splash'  # 'splash' -> 'game'
flickering_lights = []

# -------------------------------
# SPLASH / CONTENT WARNING
# -------------------------------
splash_bg = Entity(
    model='quad',
    scale=(2, 1),
    color=color.black,
    z=1
)

warning_text = Text(
    text=(
        "ADULT CONTENT WARNING\n\n"
        "This experience contains disturbing themes,\n"
        "psychological horror, and graphic imagery.\n\n"
        "Not suitable for minors, pregnant individuals,\n"
        "or players sensitive to extreme content.\n\n"
        "Proceed only if you understand and accept this."
    ),
    origin=(0, 0),
    scale=1.1,
    color=color.white
)

continue_text = Text(
    text="\n\nPress ENTER to continue\nPress ESC to quit",
    y=-0.35,
    scale=0.8,
    color=color.gray
)

# -------------------------------
# CLASSES & HELPERS
# -------------------------------
class LightSwitch(Entity):
    def __init__(self, position, rotation=(0,0,0), light_source=None, **kwargs):
        super().__init__(
            model='cube',
            color=color.dark_gray,
            scale=(0.2, 0.3, 0.05),
            position=position,
            rotation=rotation,
            collider='box',
            **kwargs
        )
        self.light_source = light_source
        self.indicator = Entity(
            parent=self,
            model='quad',
            scale=(0.5, 0.2),
            position=(0, 0.2, -0.51),
            color=color.green,
            unlit=True
        )
        self.is_on = True

    def toggle(self):
        self.is_on = not self.is_on
        if self.is_on:
            self.indicator.color = color.green
            if self.light_source: 
                self.light_source.enable()
        else:
            self.indicator.color = color.red
            if self.light_source: 
                self.light_source.disable()


class FlickeringLight:
    def __init__(self, light, interval_range=(0.08, 0.25), intensity_range=(0.35, 1.0)):
        self.light = light
        self.interval_range = interval_range
        self.intensity_range = intensity_range
        self.base_color = (
            light.color.r,
            light.color.g,
            light.color.b,
            light.color.a
        )
        self.current_intensity = intensity_range[1]
        self.target_intensity = intensity_range[1]
        self.timer = uniform(*self.interval_range)

    def update(self):
        self.timer -= time.dt
        if self.timer <= 0:
            self.timer = uniform(*self.interval_range)
            self.target_intensity = uniform(*self.intensity_range)
        self.current_intensity = lerp(
            self.current_intensity,
            self.target_intensity,
            min(1, time.dt * 8)
        )
        self._apply_intensity(self.current_intensity)

    def _apply_intensity(self, intensity):
        clamped = max(0.0, min(1.0, intensity))
        r, g, b, a = self.base_color
        self.light.color = Color(
            max(0.0, min(1.0, r * clamped)),
            max(0.0, min(1.0, g * clamped)),
            max(0.0, min(1.0, b * clamped)),
            a
        )

class Door(Entity):
    def __init__(self, position, rotation=(0,0,0), width=3.2, height=3.5, thickness=0.12, door_color=color.rgb(120, 94, 76), **kwargs):
        super().__init__(
            model='cube',
            color=door_color,
            scale=(width, height, thickness),
            position=position,
            rotation=rotation,
            collider='box',
            origin_x=0.5, # Hinge on the side
            **kwargs
        )
        self.is_open = False

    def toggle(self):
        self.is_open = not self.is_open
        if self.is_open:
            self.animate_rotation_y(self.rotation_y + 90, duration=0.5)
        else:
            self.animate_rotation_y(self.rotation_y - 90, duration=0.5)

def create_wall(position, scale, color=color.white):
    e = Entity(
        model='cube', 
        position=position, 
        scale=scale, 
        color=color, 
        texture='white_cube', 
        collider='box'
    )
    # Reduce texture repetition on walls too
    e.texture_scale = (scale[0] * 0.5, scale[1] * 0.5)
    return e

def create_floor(position, scale):
    e = Entity(
        model='plane', 
        position=position, 
        scale=scale, 
        color=color.white, 
        texture='assets/stonetiles_002_diff.png', 
        collider='box'
    )
    # Reduce texture repetition to avoid grainy look (make tiles larger)
    e.texture_scale = (scale[0] * 0.25, scale[2] * 0.25)
    return e

# -------------------------------
# GAME WORLD
# -------------------------------
player = None

def start_game():
    global game_state, player, flickering_lights

    game_state = 'game'
    flickering_lights.clear()

    # Hide splash UI
    splash_bg.disable()
    warning_text.disable()
    continue_text.disable()

    mouse.visible = False

    # Player
    player = FirstPersonController(
        speed=6, # Slightly faster for bigger map
        mouse_sensitivity=Vec2(40, 40),
        position=(0, 1, -40) # Start near entrance
    )

    # -------------------
    # CONSTANTS
    # -------------------
    CORRIDOR_WIDTH = 10
    CORRIDOR_LENGTH = 100 # -50 to 50
    CORRIDOR_HEIGHT = 6
    ROOM_SIZE = 14
    ROOM_HEIGHT = 6
    
    # Colors
    theme_wall = color.rgb(212, 195, 178)
    theme_ceiling = color.rgb(245, 237, 224)
    theme_door = color.rgb(100, 80, 70)

    # -------------------
    # GROUND FLOOR
    # -------------------
    
    # Main Corridor Floor
    create_floor(position=(0, 0, 0), scale=(CORRIDOR_WIDTH, 1, CORRIDOR_LENGTH))
    
    # Main Corridor Ceiling
    create_wall(position=(0, CORRIDOR_HEIGHT, 0), scale=(CORRIDOR_WIDTH, 0.2, CORRIDOR_LENGTH), color=theme_ceiling)
    
    # Entrance Wall (at z = -50)
    create_wall(position=(0, CORRIDOR_HEIGHT/2, -CORRIDOR_LENGTH/2), scale=(CORRIDOR_WIDTH, CORRIDOR_HEIGHT, 0.2), color=theme_wall)

    # Generate Rooms along the corridor
    # We'll place rooms every 20 units, from -30 to 30
    room_z_positions = [-30, -10, 10, 30]
    
    # Continuous Corridor Walls with Door Gaps
    # Corridor runs from -50 to 50.
    # Door gaps are at z +/- 1.75 for each room z.
    # We build walls in segments.
    
    # Calculate segments
    segments = []
    current_z = -50
    
    for z in room_z_positions:
        # Wall before door
        gap_start = z - 1.75
        if gap_start > current_z:
            length = gap_start - current_z
            center = current_z + length/2
            segments.append((center, length))
        
        # Door gap is skipped (z-1.75 to z+1.75)
        current_z = z + 1.75
        
    # Final segment
    if current_z < 50:
        length = 50 - current_z
        center = current_z + length/2
        segments.append((center, length))
        
    # Create Corridor Walls from segments
    for center, length in segments:
        # Left Wall
        create_wall(position=(-CORRIDOR_WIDTH/2, ROOM_HEIGHT/2, center), scale=(0.2, ROOM_HEIGHT, length), color=theme_wall)
        # Right Wall
        create_wall(position=(CORRIDOR_WIDTH/2, ROOM_HEIGHT/2, center), scale=(0.2, ROOM_HEIGHT, length), color=theme_wall)

    # Create Rooms and Doors
    for i, z in enumerate(room_z_positions):
        # --- LEFT ROOM ---
        # Room Floor
        create_floor(position=(-(CORRIDOR_WIDTH/2 + ROOM_SIZE/2), 0, z), scale=(ROOM_SIZE, 1, ROOM_SIZE))
        # Room Ceiling
        create_wall(position=(-(CORRIDOR_WIDTH/2 + ROOM_SIZE/2), ROOM_HEIGHT, z), scale=(ROOM_SIZE, 0.2, ROOM_SIZE), color=theme_ceiling)
        # Room Walls (Back, Left, Front)
        create_wall(position=(-(CORRIDOR_WIDTH/2 + ROOM_SIZE), ROOM_HEIGHT/2, z), scale=(0.2, ROOM_HEIGHT, ROOM_SIZE), color=theme_wall) # Far Left
        create_wall(position=(-(CORRIDOR_WIDTH/2 + ROOM_SIZE/2), ROOM_HEIGHT/2, z + ROOM_SIZE/2), scale=(ROOM_SIZE, ROOM_HEIGHT, 0.2), color=theme_wall) # Front
        create_wall(position=(-(CORRIDOR_WIDTH/2 + ROOM_SIZE/2), ROOM_HEIGHT/2, z - ROOM_SIZE/2), scale=(ROOM_SIZE, ROOM_HEIGHT, 0.2), color=theme_wall) # Back
        
        # Header above door
        create_wall(position=(-CORRIDOR_WIDTH/2, ROOM_HEIGHT - 1.2, z), scale=(0.2, 2.4, 3.5), color=theme_wall)

        # Door (Rotated 90 deg to fit in wall, Hinge at z-1.75)
        # Position: x=-5, y=1.85, z=z+1.75. Rot: (0, -90, 0) -> Extends to z-1.75
        Door(position=(-CORRIDOR_WIDTH/2, 1.85, z + 1.75), rotation=(0, -90, 0), width=3.5, door_color=theme_door)
        
        # Light
        l = PointLight(parent=scene, position=(-(CORRIDOR_WIDTH/2 + ROOM_SIZE/2), ROOM_HEIGHT-1, z), color=color.random_color())
        LightSwitch(position=(-CORRIDOR_WIDTH/2 - 0.2, 1.5, z + 2), rotation=(0, 90, 0), light_source=l)


        # --- RIGHT ROOM ---
        # Room Floor
        create_floor(position=((CORRIDOR_WIDTH/2 + ROOM_SIZE/2), 0, z), scale=(ROOM_SIZE, 1, ROOM_SIZE))
        # Room Ceiling
        create_wall(position=((CORRIDOR_WIDTH/2 + ROOM_SIZE/2), ROOM_HEIGHT, z), scale=(ROOM_SIZE, 0.2, ROOM_SIZE), color=theme_ceiling)
        # Room Walls
        create_wall(position=((CORRIDOR_WIDTH/2 + ROOM_SIZE), ROOM_HEIGHT/2, z), scale=(0.2, ROOM_HEIGHT, ROOM_SIZE), color=theme_wall) # Far Right
        create_wall(position=((CORRIDOR_WIDTH/2 + ROOM_SIZE/2), ROOM_HEIGHT/2, z + ROOM_SIZE/2), scale=(ROOM_SIZE, ROOM_HEIGHT, 0.2), color=theme_wall) # Front
        create_wall(position=((CORRIDOR_WIDTH/2 + ROOM_SIZE/2), ROOM_HEIGHT/2, z - ROOM_SIZE/2), scale=(ROOM_SIZE, ROOM_HEIGHT, 0.2), color=theme_wall) # Back
        
        # Header above door
        create_wall(position=(CORRIDOR_WIDTH/2, ROOM_HEIGHT - 1.2, z), scale=(0.2, 2.4, 3.5), color=theme_wall)

        # Door (Rotated 90 deg, Hinge at z-1.75)
        # Position: x=5, y=1.85, z=z-1.75. Rot: (0, 90, 0) -> Extends to z+1.75
        Door(position=(CORRIDOR_WIDTH/2, 1.85, z - 1.75), rotation=(0, 90, 0), width=3.5, door_color=theme_door)
        
        # Light
        l = PointLight(parent=scene, position=((CORRIDOR_WIDTH/2 + ROOM_SIZE/2), ROOM_HEIGHT-1, z), color=color.random_color())
        LightSwitch(position=(CORRIDOR_WIDTH/2 + 0.2, 1.5, z + 2), rotation=(0, -90, 0), light_source=l)

    # Corridor Lights (Ground)
    warm_yellow = color.rgb(255, 180, 80) # Dimly warm yellow
    for z in range(-40, 50, 20):
        light = PointLight(parent=scene, position=(0, CORRIDOR_HEIGHT-1, z), color=warm_yellow)
        flickering_lights.append(FlickeringLight(light, intensity_range=(0.4, 0.9)))

    # Corridor Lights (Upper)
    for z in range(-40, 50, 20):
        light = PointLight(parent=scene, position=(0, landing_height + CORRIDOR_HEIGHT-1, z), color=warm_yellow)
        flickering_lights.append(FlickeringLight(light, intensity_range=(0.4, 0.9)))

    # -------------------
    # STAIRCASE (Grand)
    # -------------------
    # At z = 50 (End of corridor)
    # Wide stairs in the middle
    stair_z_start = CORRIDOR_LENGTH/2 # 50
    
    # Floor for stair area
    create_floor(position=(0, 0, stair_z_start + 10), scale=(CORRIDOR_WIDTH, 1, 20))
    # Ceiling for stair area (higher?)
    create_wall(position=(0, CORRIDOR_HEIGHT + 4, stair_z_start + 10), scale=(CORRIDOR_WIDTH, 0.2, 20), color=theme_ceiling)
    
    # Walls around stairwell
    create_wall(position=(-CORRIDOR_WIDTH/2, CORRIDOR_HEIGHT/2 + 2, stair_z_start + 10), scale=(0.2, CORRIDOR_HEIGHT+4, 20), color=theme_wall)
    create_wall(position=(CORRIDOR_WIDTH/2, CORRIDOR_HEIGHT/2 + 2, stair_z_start + 10), scale=(0.2, CORRIDOR_HEIGHT+4, 20), color=theme_wall)
    create_wall(position=(0, CORRIDOR_HEIGHT/2 + 2, stair_z_start + 20), scale=(CORRIDOR_WIDTH, CORRIDOR_HEIGHT+4, 0.2), color=theme_wall) # Back wall

    # Steps
    for i in range(20):
        Entity(
            model='cube',
            color=color.rgb(100, 100, 100),
            texture='assets/wood1.jpg',
            position=(0, i*0.3, stair_z_start + i*0.5),
            scale=(6, 0.3, 0.5),
            collider='box'
        )
    
    # Landing at top
    landing_z = stair_z_start + 10 # 60
    landing_height = 6 # Match CORRIDOR_HEIGHT roughly? 20*0.3 = 6. Perfect.
    
    create_floor(position=(0, landing_height, landing_z + 5), scale=(CORRIDOR_WIDTH, 1, 10))

    # -------------------
    # UPPER FLOOR
    # -------------------
    # Upper Corridor (Same layout as bottom)
    # Floor
    create_floor(position=(0, landing_height, 0), scale=(CORRIDOR_WIDTH, 1, CORRIDOR_LENGTH))
    # Ceiling
    create_wall(position=(0, landing_height + CORRIDOR_HEIGHT, 0), scale=(CORRIDOR_WIDTH, 0.2, CORRIDOR_LENGTH), color=theme_ceiling)
    
    # Upper Entrance Wall (at z = -50)
    create_wall(position=(0, landing_height + CORRIDOR_HEIGHT/2, -CORRIDOR_LENGTH/2), scale=(CORRIDOR_WIDTH, CORRIDOR_HEIGHT, 0.2), color=theme_wall)

    # Generate Upper Rooms
    for i, z in enumerate(room_z_positions):
        # --- LEFT ROOM ---
        create_floor(position=(-(CORRIDOR_WIDTH/2 + ROOM_SIZE/2), landing_height, z), scale=(ROOM_SIZE, 1, ROOM_SIZE))
        create_wall(position=(-(CORRIDOR_WIDTH/2 + ROOM_SIZE/2), landing_height + ROOM_HEIGHT, z), scale=(ROOM_SIZE, 0.2, ROOM_SIZE), color=theme_ceiling)
        create_wall(position=(-(CORRIDOR_WIDTH/2 + ROOM_SIZE), landing_height + ROOM_HEIGHT/2, z), scale=(0.2, ROOM_HEIGHT, ROOM_SIZE), color=theme_wall)
        create_wall(position=(-(CORRIDOR_WIDTH/2 + ROOM_SIZE/2), landing_height + ROOM_HEIGHT/2, z + ROOM_SIZE/2), scale=(ROOM_SIZE, ROOM_HEIGHT, 0.2), color=theme_wall)
        create_wall(position=(-(CORRIDOR_WIDTH/2 + ROOM_SIZE/2), landing_height + ROOM_HEIGHT/2, z - ROOM_SIZE/2), scale=(ROOM_SIZE, ROOM_HEIGHT, 0.2), color=theme_wall)
        
        # Header
        create_wall(position=(-CORRIDOR_WIDTH/2, landing_height + ROOM_HEIGHT - 1.2, z), scale=(0.2, 2.4, 3.5), color=theme_wall)

        # Door (Rotated 90 deg, Hinge at z-1.75)
        Door(position=(-CORRIDOR_WIDTH/2, landing_height + 1.85, z + 1.75), rotation=(0, -90, 0), width=3.5, door_color=theme_door)
        
        l = PointLight(parent=scene, position=(-(CORRIDOR_WIDTH/2 + ROOM_SIZE/2), landing_height + ROOM_HEIGHT-1, z), color=color.random_color())
        LightSwitch(position=(-CORRIDOR_WIDTH/2 - 0.2, landing_height + 1.5, z + 2), rotation=(0, 90, 0), light_source=l)

        # --- RIGHT ROOM ---
        create_floor(position=((CORRIDOR_WIDTH/2 + ROOM_SIZE/2), landing_height, z), scale=(ROOM_SIZE, 1, ROOM_SIZE))
        create_wall(position=((CORRIDOR_WIDTH/2 + ROOM_SIZE/2), landing_height + ROOM_HEIGHT, z), scale=(ROOM_SIZE, 0.2, ROOM_SIZE), color=theme_ceiling)
        create_wall(position=((CORRIDOR_WIDTH/2 + ROOM_SIZE), landing_height + ROOM_HEIGHT/2, z), scale=(0.2, ROOM_HEIGHT, ROOM_SIZE), color=theme_wall)
        create_wall(position=((CORRIDOR_WIDTH/2 + ROOM_SIZE/2), landing_height + ROOM_HEIGHT/2, z + ROOM_SIZE/2), scale=(ROOM_SIZE, ROOM_HEIGHT, 0.2), color=theme_wall)
        create_wall(position=((CORRIDOR_WIDTH/2 + ROOM_SIZE/2), landing_height + ROOM_HEIGHT/2, z - ROOM_SIZE/2), scale=(ROOM_SIZE, ROOM_HEIGHT, 0.2), color=theme_wall)
        
        # Header
        create_wall(position=(CORRIDOR_WIDTH/2, landing_height + ROOM_HEIGHT - 0.5, z), scale=(0.2, 1, 3.5), color=theme_wall)

        # Door (Rotated 90 deg, Hinge at z-1.75)
        Door(position=(CORRIDOR_WIDTH/2, landing_height + 1.85, z - 1.75), rotation=(0, 90, 0), width=3.5, door_color=theme_door)
        
        l = PointLight(parent=scene, position=((CORRIDOR_WIDTH/2 + ROOM_SIZE/2), landing_height + ROOM_HEIGHT-1, z), color=color.random_color())
        LightSwitch(position=(CORRIDOR_WIDTH/2 + 0.2, landing_height + 1.5, z + 2), rotation=(0, -90, 0), light_source=l)

    # Upper Corridor Walls (Continuous)
    for center, length in segments:
        # Left Wall
        create_wall(position=(-CORRIDOR_WIDTH/2, landing_height + ROOM_HEIGHT/2, center), scale=(0.2, ROOM_HEIGHT, length), color=theme_wall)
        # Right Wall
        create_wall(position=(CORRIDOR_WIDTH/2, landing_height + ROOM_HEIGHT/2, center), scale=(0.2, ROOM_HEIGHT, length), color=theme_wall)

    # Ambient light
    AmbientLight(color=color.rgba(30, 30, 30, 255))

# -------------------------------
# INPUT HANDLING
# -------------------------------
def input(key):
    if game_state == 'splash':
        if key == 'enter':
            start_game()
        if key == 'escape':
            application.quit()

    elif game_state == 'game':
        if key == 'escape':
            application.quit()
        
        if key == 'e':
            hit_info = raycast(camera.world_position, camera.forward, distance=5)
            if hit_info.hit:
                if isinstance(hit_info.entity, LightSwitch):
                    hit_info.entity.toggle()
                elif isinstance(hit_info.entity, Door):
                    hit_info.entity.toggle()

# -------------------------------
# UPDATE LOOP
# -------------------------------
def update():
    for controller in flickering_lights:
        controller.update()

app.run()
