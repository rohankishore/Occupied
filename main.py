from ursina import *
from ursina.prefabs.first_person_controller import FirstPersonController

app = Ursina(borderless=False)
window.title = 'HOME'
window.color = color.black
mouse.visible = True

# -------------------------------
# GLOBAL STATE
# -------------------------------
game_state = 'splash'  # 'splash' -> 'game'

# Paint System
paint_colors = [
    color.white, color.light_gray, color.gray, color.dark_gray, color.black,
    color.red, color.orange, color.yellow, color.lime, color.green,
    color.turquoise, color.cyan, color.azure, color.blue,
    color.violet, color.magenta, color.pink, color.brown,
    color.rgb(139, 69, 19) # SaddleBrown
]
current_paint_index = 6 # Default to a nice color
paint_indicator = None

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
        self.is_on = False

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

class Door(Entity):
    def __init__(self, position, rotation=(0,0,0), **kwargs):
        super().__init__(
            model='cube',
            color=color.rgb(139, 69, 19), # SaddleBrown
            scale=(2, 3.5, 0.2),
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

class FlickeringLight(PointLight):
    def __init__(self, position, color=color.white, **kwargs):
        super().__init__(position=position, color=color, **kwargs)
        self.base_color = color
        self.flicker_timer = 0
        self.is_flickering = True

    def update(self):
        if not self.is_flickering:
            return
            
        self.flicker_timer -= time.dt
        if self.flicker_timer <= 0:
            # Randomize next flicker time
            self.flicker_timer = random.uniform(0.05, 0.2)
            
            # Randomly turn off or dim
            if random.random() < 0.3:
                self.color = color.black
            else:
                # Random intensity variation
                intensity = random.uniform(0.1, 1.0) # More drastic range
                self.color = color.rgba(
                    self.base_color.r * intensity,
                    self.base_color.g * intensity,
                    self.base_color.b * intensity,
                    255
                )

def create_wall(position, scale, color=color.white):
    e = Entity(
        model='cube', 
        position=position, 
        scale=scale, 
        color=color, 
        collider='box'
    )
    return e

def create_floor(position, scale):
    e = Entity(
        model='plane', 
        position=position, 
        scale=scale, 
        color=color.gray, 
        collider='box'
    )
    return e

# -------------------------------
# GAME WORLD
# -------------------------------
player = None

def start_game():
    global game_state, player

    game_state = 'game'

    # Hide splash UI
    splash_bg.disable()
    warning_text.disable()
    continue_text.disable()

    mouse.visible = False

    # Player
    player = FirstPersonController(
        speed=5,
        mouse_sensitivity=Vec2(40, 40),
        position=(0, 1, -5)
    )

    # -------------------
    # GROUND FLOOR
    # -------------------
    
    # Main Corridor (Ground)
    corridor_color = color.light_gray
    # Floor
    create_floor(position=(0, 0, 0), scale=(4, 1, 30))
    # Ceiling
    create_wall(position=(0, 4, 0), scale=(4, 0.2, 30), color=corridor_color)
    
    # Corridor Walls
    # Left wall segments (leaving gaps for doors)
    # Gap at z=0. Wall from -15 to -1.5 (len 13.5) and 1.5 to 15 (len 13.5)
    # Let's make the gap 3 units wide (-1.5 to 1.5)
    create_wall(position=(-2, 2, -8.25), scale=(0.2, 4, 13.5), color=corridor_color) # Back part
    create_wall(position=(-2, 2, 8.25), scale=(0.2, 4, 13.5), color=corridor_color)  # Front part
    create_wall(position=(-2, 3.75, 0), scale=(0.2, 0.5, 3), color=corridor_color) # Above door
    
    # Door to Living Room
    Door(position=(-2, 1.75, -1.5), rotation=(0, 0, 0))

    # Right wall segments
    create_wall(position=(2, 2, -8.25), scale=(0.2, 4, 13.5), color=corridor_color)
    create_wall(position=(2, 2, 8.25), scale=(0.2, 4, 13.5), color=corridor_color)
    create_wall(position=(2, 3.75, 0), scale=(0.2, 0.5, 3), color=corridor_color)
    
    # Door to Kitchen
    Door(position=(2, 1.75, 1.5), rotation=(0, 180, 0))

    # End walls
    create_wall(position=(0, 2, -15), scale=(4, 4, 0.2), color=corridor_color) # Entrance
    # (Other end is stairs)

    # Corridor Lights (Flickering)
    FlickeringLight(parent=scene, position=(0, 3.5, -10), color=color.rgba(200, 200, 150, 255))
    FlickeringLight(parent=scene, position=(0, 3.5, 0), color=color.rgba(200, 200, 150, 255))
    FlickeringLight(parent=scene, position=(0, 3.5, 10), color=color.rgba(200, 200, 150, 255))

    # Living Room (Left)
    lr_color = color.red
    # Floor
    create_floor(position=(-7, 0, 0), scale=(10, 1, 10))
    # Ceiling
    create_wall(position=(-7, 4, 0), scale=(10, 0.2, 10), color=lr_color)
    # Walls
    create_wall(position=(-12, 2, 0), scale=(0.2, 4, 10), color=lr_color) # Far left
    create_wall(position=(-7, 2, 5), scale=(10, 4, 0.2), color=lr_color)  # Front
    create_wall(position=(-7, 2, -5), scale=(10, 4, 0.2), color=lr_color) # Back
    # The wall shared with corridor is at x=-2. We already built it as part of corridor.
    # But we might want the inside face to be lr_color. 
    # For simplicity, let's just leave the corridor wall as is (gray on both sides).
    
    # Light for Living Room
    lr_light = PointLight(parent=scene, position=(-7, 3, 0), color=color.orange)
    LightSwitch(position=(-2.2, 1.5, 1), rotation=(0, 90, 0), light_source=lr_light)

    # Kitchen (Right)
    k_color = color.cyan
    # Floor
    create_floor(position=(7, 0, 0), scale=(10, 1, 10))
    # Ceiling
    create_wall(position=(7, 4, 0), scale=(10, 0.2, 10), color=k_color)
    # Walls
    create_wall(position=(12, 2, 0), scale=(0.2, 4, 10), color=k_color) # Far right
    create_wall(position=(7, 2, 5), scale=(10, 4, 0.2), color=k_color)  # Front
    create_wall(position=(7, 2, -5), scale=(10, 4, 0.2), color=k_color) # Back
    
    # Light for Kitchen
    k_light = PointLight(parent=scene, position=(7, 3, 0), color=color.white)
    LightSwitch(position=(2.2, 1.5, 1), rotation=(0, -90, 0), light_source=k_light)

    # -------------------
    # STAIRCASE
    # -------------------
    # Simple steps going up at the end of the corridor (z=15)
    for i in range(10):
        Entity(
            model='cube',
            color=color.rgb(100, 100, 100),
            position=(0, i*0.4, 15 + i*0.5),
            scale=(4, 0.4, 0.5),
            collider='box'
        )
    
    # Landing at top of stairs
    create_floor(position=(0, 4, 20), scale=(4, 1, 4))

    # -------------------
    # UPPER FLOOR
    # -------------------
    
    # Upper Corridor
    uc_color = color.light_gray
    create_floor(position=(0, 4, 0), scale=(4, 1, 30)) 
    
    # Upper Corridor Walls
    create_wall(position=(-2, 6, 0), scale=(0.2, 4, 30), color=uc_color)
    create_wall(position=(2, 6, 0), scale=(0.2, 4, 30), color=uc_color)
    create_wall(position=(0, 6, -15), scale=(4, 4, 0.2), color=uc_color) # End
    
    # Master Bedroom (at z=-20, connected to corridor end)
    br_color = color.blue
    create_floor(position=(0, 4, -20), scale=(10, 1, 10))
    create_wall(position=(0, 8, -20), scale=(10, 0.2, 10), color=br_color) # Ceiling
    create_wall(position=(-5, 6, -20), scale=(0.2, 4, 10), color=br_color)
    create_wall(position=(5, 6, -20), scale=(0.2, 4, 10), color=br_color)
    create_wall(position=(0, 6, -25), scale=(10, 4, 0.2), color=br_color)
    
    # Wall between bedroom and corridor (with door)
    # Bedroom is at z=-20 (size 10, so -25 to -15). Corridor ends at -15.
    # So the shared wall is at z=-15.
    # Corridor width is 4 (-2 to 2). Bedroom width is 10 (-5 to 5).
    # We need a wall at z=-15 with a door hole.
    # Wall parts:
    # Left of door: x < -1.5
    create_wall(position=(-3.25, 6, -15), scale=(3.5, 4, 0.2), color=br_color)
    # Right of door: x > 1.5
    create_wall(position=(3.25, 6, -15), scale=(3.5, 4, 0.2), color=br_color)
    # Above door
    create_wall(position=(0, 7.75, -15), scale=(3, 0.5, 0.2), color=br_color)
    
    # Door to Bedroom
    Door(position=(-1.5, 5.75, -15), rotation=(0, 0, 0))
    
    # Light for Bedroom
    br_light = PointLight(parent=scene, position=(0, 7, -20), color=color.cyan)
    LightSwitch(position=(1, 5.5, -15.2), rotation=(0, 180, 0), light_source=br_light)

    # Ambient light for base visibility
    AmbientLight(color=color.rgba(30, 30, 30, 255))

    # Paint UI
    global paint_indicator
    paint_indicator = Entity(
        parent=camera.ui,
        model='circle',
        scale=0.05,
        position=(0.8, -0.45),
        color=paint_colors[current_paint_index]
    )
    Text(
        parent=camera.ui,
        text='[Scroll] Select Paint\n[LMB] Apply Paint',
        position=(0.65, -0.38),
        scale=0.8,
        color=color.white
    )

# -------------------------------
# INPUT HANDLING
# -------------------------------
def input(key):
    global current_paint_index
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

        # Painting
        if key == 'left mouse down':
            hit_info = raycast(camera.world_position, camera.forward, distance=10)
            if hit_info.hit:
                hit_info.entity.color = paint_colors[current_paint_index]
                
        if key == 'scroll up':
            current_paint_index = (current_paint_index + 1) % len(paint_colors)
            if paint_indicator:
                paint_indicator.color = paint_colors[current_paint_index]
        if key == 'scroll down':
            current_paint_index = (current_paint_index - 1) % len(paint_colors)
            if paint_indicator:
                paint_indicator.color = paint_colors[current_paint_index]

# -------------------------------
# UPDATE LOOP
# -------------------------------
def update():
    pass

app.run()
