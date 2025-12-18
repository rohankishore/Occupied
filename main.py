from ursina import *
from ursina.prefabs.first_person_controller import FirstPersonController
from ursina.shaders import unlit_shader
from random import uniform

app = Ursina(borderless=False)
window.title = 'HOME'
window.color = color.black
mouse.visible = True

# Fix white/washed out rendering - use unlit shader as default
Entity.default_shader = unlit_shader

# Disable fog
scene.fog_density = 0
scene.fog_color = color.black
camera.clip_plane_far = 500

# Set very dark ambient
window.color = color.rgb(5, 5, 8)

# -------------------------------
# GLOBAL STATE
# -------------------------------
game_state = 'splash'  # 'splash' -> 'game'
flickering_lights = []
current_focus = None
interaction_prompt = None
default_cursor_color = color.white
highlight_cursor_color = color.yellow

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
    def __init__(
        self,
        position,
        rotation=(0,0,0),
        light_source=None,
        start_on=True,
        prompt_on=None,
        prompt_off=None,
        on_first_activate=None,
        **kwargs
    ):
        super().__init__(
            model='cube',
            color=color.dark_gray,
            scale=(0.2, 0.3, 0.05),
            position=position,
            rotation=rotation,
            collider='box',
            unlit=True,
            **kwargs
        )
        self.light_source = light_source
        self.prompt_on = prompt_on
        self.prompt_off = prompt_off
        self.on_first_activate = on_first_activate
        self.has_triggered = False
        self.indicator = Entity(
            parent=self,
            model='quad',
            scale=(0.5, 0.2),
            position=(0, 0.2, -0.51),
            color=color.green,
            unlit=True
        )
        self.is_on = start_on
        if not self.is_on:
            self.indicator.color = color.red
            if self.light_source:
                self.light_source.disable()
        else:
            if self.light_source:
                self.light_source.enable()

    def toggle(self):
        self.is_on = not self.is_on
        if self.is_on:
            self.indicator.color = color.green
            if self.light_source: 
                self.light_source.enable()
            if not self.has_triggered and self.on_first_activate:
                self.on_first_activate()
                self.has_triggered = True
        else:
            self.indicator.color = color.red
            if self.light_source: 
                self.light_source.disable()

    def get_interaction_text(self):
        if self.is_on:
            return self.prompt_on or 'Press E to toggle light'
        return self.prompt_off or 'Press E to toggle light'


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


def resolve_interactable(entity):
    while entity and not isinstance(entity, (LightSwitch, Door)):
        entity = entity.parent
    return entity


def interaction_text_for(entity):
    if hasattr(entity, 'get_interaction_text'):
        return entity.get_interaction_text()
    if isinstance(entity, LightSwitch):
        return 'Press E to toggle light'
    if isinstance(entity, Door):
        return 'Press E to close door' if entity.is_open else 'Press E to open door'
    return ''

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
            unlit=True,
            **kwargs
        )
        self.is_open = False

    def toggle(self):
        self.is_open = not self.is_open
        if self.is_open:
            self.animate_rotation_y(self.rotation_y + 90, duration=0.5)
        else:
            self.animate_rotation_y(self.rotation_y - 90, duration=0.5)

def create_wall(position, scale, color=color.rgb(50,50,50), texture=None):
    e = Entity(
        model='cube', 
        position=position, 
        scale=scale, 
        color=color, 
        texture=texture, 
        collider='box',
        unlit=True
    )
    if texture:
        e.texture_scale = (scale[0], scale[1])
    return e

def create_floor(position, scale, color_value=color.rgb(40,40,40), texture=None):
    e = Entity(
        model='plane', 
        position=position, 
        scale=scale, 
        color=color_value, 
        texture=texture, 
        collider='box',
        unlit=True
    )
    if texture:
        e.texture_scale = (scale[0], scale[2])
    return e


def add_door_label(door, label_text, above_door=True):
    """Add a room number label above or on a door."""
    if above_door:
        # Create a label plate above the door
        plate = Entity(
            model='cube',
            color=color.rgb(40, 40, 50),
            scale=(1.2, 0.4, 0.08),
            position=(door.x, door.y + door.scale_y / 2 + 0.4, door.z - 0.1),
            rotation=door.rotation
        )
        return Text(
            text=label_text,
            parent=plate,
            position=(0, 0, -0.6),
            origin=(0, 0),
            scale=15,
            color=color.white,
            billboard=True
        )
    else:
        return Text(
            text=label_text,
            parent=door,
            position=(0, door.scale_y / 2 + 0.3, -door.scale_z / 2 - 0.02),
            origin=(0, 0),
            scale=0.6,
            color=color.black,
            billboard=True
        )

# -------------------------------
# GAME WORLD
# -------------------------------
player = None

def start_game():
    global game_state, player, flickering_lights, current_focus
    global interaction_prompt, default_cursor_color

    game_state = 'game'

    flickering_lights.clear()
    current_focus = None

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
    default_cursor_color = player.cursor.color
    player.cursor.color = default_cursor_color

    interaction_prompt = Text(
        text='',
        parent=camera.ui,
        y=-0.4,
        origin=(0, 0),
        scale=0.8,
        color=color.white,
        enabled=False
    )

    # -------------------
    # GROUND FLOOR
    # -------------------
    
    # Main Corridor (Ground) - Dark horror hotel aesthetic
    corridor_color = color.rgb(90, 25, 35)  # Dark burgundy/red wallpaper
    corridor_ceiling_color = color.rgb(25, 20, 22)  # Very dark ceiling
    wood_floor_color = color.rgb(75, 45, 30)  # Dark wood floor
    
    # Floor - dark wood
    create_floor(position=(0, 0, 0), scale=(4, 1, 30), color_value=wood_floor_color)
    # Ceiling - very dark
    create_wall(position=(0, 4, 0), scale=(4, 0.2, 30), color=corridor_ceiling_color)
    
    # Baseboards (dark wood trim at bottom of walls)
    Entity(model='cube', color=color.rgb(35, 25, 20), scale=(0.25, 0.3, 30), position=(-1.9, 0.15, 0), unlit=True)
    Entity(model='cube', color=color.rgb(35, 25, 20), scale=(0.25, 0.3, 30), position=(1.9, 0.15, 0), unlit=True)
    
    # Corridor Walls - Dark burgundy
    create_wall(position=(-2, 2, -8.25), scale=(0.2, 4, 13.5), color=corridor_color)
    create_wall(position=(-2, 2, 8.25), scale=(0.2, 4, 13.5), color=corridor_color)
    create_wall(position=(-2, 3.75, 0), scale=(0.2, 0.5, 3), color=corridor_color)
    
    # Door to Living Room - dark wood
    living_room_door = Door(
        position=(-2, 1.85, -1.5),
        rotation=(0, 0, 0),
        height=3.8,
        door_color=color.rgb(50, 35, 28)
    )
    add_door_label(living_room_door, '101')

    # Right wall segments
    create_wall(position=(2, 2, -8.25), scale=(0.2, 4, 13.5), color=corridor_color)
    create_wall(position=(2, 2, 8.25), scale=(0.2, 4, 13.5), color=corridor_color)
    create_wall(position=(2, 3.75, 0), scale=(0.2, 0.5, 3), color=corridor_color)
    
    # Door to Kitchen - dark wood
    kitchen_door = Door(
        position=(2, 1.85, 1.5),
        rotation=(0, 180, 0),
        height=3.8,
        door_color=color.rgb(45, 30, 25)
    )
    add_door_label(kitchen_door, '102')

    # Corridor lighting - dim warm yellow, very atmospheric
    corridor_light_color = color.rgb(255, 180, 100)  # Warm dim yellow
    for z in (-12, -4, 4, 12):
        # Main overhead light - dimmer
        light = PointLight(parent=scene, position=(0, 3.2, z), color=corridor_light_color)
        flickering_lights.append(FlickeringLight(light, interval_range=(0.08, 0.3), intensity_range=(0.3, 0.6)))
        # Light fixture (ceiling mount)
        Entity(
            model='cube',
            color=color.rgb(30, 25, 25),
            scale=(0.5, 0.15, 0.3),
            position=(0, 3.92, z),
            unlit=True
        )
        # Glowing bulb - smaller, dimmer look
        Entity(
            model='sphere',
            color=color.rgb(255, 200, 120),
            scale=0.12,
            position=(0, 3.75, z),
            unlit=True
        )
        # Light cone effect on ceiling
        Entity(
            model='quad',
            color=color.rgb(255, 220, 150),
            scale=(0.8, 0.8),
            position=(0, 3.9, z),
            rotation_x=90,
            alpha=0.15,
            unlit=True
        )

    # End walls - dark burgundy
    create_wall(position=(0, 2, -15), scale=(4, 4, 0.2), color=corridor_color)
    # (Other end is stairs)

    # Living Room (Left) - darker tones
    lr_color = color.rgb(100, 40, 50)  # Dark red
    lr_ceiling_color = color.rgb(30, 25, 28)
    lr_floor_color = color.rgb(65, 40, 28)  # Dark wood
    # Floor
    create_floor(position=(-7, 0, 0), scale=(10, 1, 10), color_value=lr_floor_color)
    # Ceiling
    create_wall(position=(-7, 4, 0), scale=(10, 0.2, 10), color=lr_ceiling_color)
    # Walls
    create_wall(position=(-12, 2, 0), scale=(0.2, 4, 10), color=lr_color)
    create_wall(position=(-7, 2, 5), scale=(10, 4, 0.2), color=lr_color)
    create_wall(position=(-7, 2, -5), scale=(10, 4, 0.2), color=lr_color)
    # The wall shared with corridor is at x=-2. We already built it as part of corridor.
    # But we might want the inside face to be lr_color. 
    # For simplicity, let's just leave the corridor wall as is (gray on both sides).
    
    # Dim ambient light for Living Room (always on)
    PointLight(parent=scene, position=(-7, 2.5, 0), color=color.rgb(40, 35, 30))
    # Main light for Living Room (switchable)
    lr_light = PointLight(parent=scene, position=(-7, 3.5, 0), color=color.rgb(255, 200, 120))
    # Light fixture
    Entity(model='sphere', color=color.rgb(255, 220, 150), scale=0.3, position=(-7, 3.7, 0), unlit=True)
    LightSwitch(position=(-2.2, 1.5, 1), rotation=(0, 90, 0), light_source=lr_light)

    # Kitchen (Right) - darker industrial look
    k_color = color.rgb(55, 65, 60)  # Dark teal-gray
    k_ceiling_color = color.rgb(28, 30, 32)
    k_floor_color = color.rgb(50, 50, 48)  # Dark tile
    # Floor
    create_floor(position=(7, 0, 0), scale=(10, 1, 10), color_value=k_floor_color)
    # Ceiling
    create_wall(position=(7, 4, 0), scale=(10, 0.2, 10), color=k_ceiling_color)
    # Walls
    create_wall(position=(12, 2, 0), scale=(0.2, 4, 10), color=k_color)
    create_wall(position=(7, 2, 5), scale=(10, 4, 0.2), color=k_color)
    create_wall(position=(7, 2, -5), scale=(10, 4, 0.2), color=k_color)
    
    # Dim ambient light for Kitchen (always on)
    PointLight(parent=scene, position=(7, 2.5, 0), color=color.rgb(35, 40, 38))
    # Main light for Kitchen (switchable)
    k_light = PointLight(parent=scene, position=(7, 3.5, 0), color=color.rgb(255, 255, 240))
    # Light fixture
    Entity(model='cube', color=color.rgb(200, 200, 200), scale=(1.2, 0.1, 0.3), position=(7, 3.9, 0), unlit=True)
    Entity(model='sphere', color=color.rgb(255, 255, 230), scale=0.2, position=(7, 3.75, 0), unlit=True)
    LightSwitch(position=(2.2, 1.5, 1), rotation=(0, -90, 0), light_source=k_light)

    # -------------------
    # STAIRCASE - dark wood
    # -------------------
    stair_color = color.rgb(45, 30, 25)
    for i in range(10):
        Entity(
            model='cube',
            color=stair_color,
            position=(0, i*0.4, 15 + i*0.5),
            scale=(4, 0.4, 0.5),
            collider='box',
            unlit=True
        )
    
    # Landing at top of stairs
    create_floor(position=(0, 4, 20), scale=(4, 1, 4), color_value=wood_floor_color)

    # -------------------
    # UPPER FLOOR - Same dark hotel aesthetic
    # -------------------
    
    # Upper Corridor - dark burgundy
    uc_color = color.rgb(85, 28, 38)  # Dark burgundy
    uc_ceiling_color = color.rgb(22, 18, 20)  # Very dark
    uc_floor_color = color.rgb(70, 42, 28)  # Dark wood
    create_floor(position=(0, 4, 0), scale=(4, 1, 30), color_value=uc_floor_color) 
    
    # Baseboards for upper corridor
    Entity(model='cube', color=color.rgb(35, 25, 20), scale=(0.25, 0.3, 30), position=(-1.9, 4.15, 0), unlit=True)
    Entity(model='cube', color=color.rgb(35, 25, 20), scale=(0.25, 0.3, 30), position=(1.9, 4.15, 0), unlit=True)
    
    # Upper Corridor Walls - dark burgundy
    create_wall(position=(-2, 6, -5.25), scale=(0.2, 4, 19.5), color=uc_color)
    create_wall(position=(-2, 6, 11.25), scale=(0.2, 4, 7.5), color=uc_color)
    create_wall(position=(2, 6, 5.25), scale=(0.2, 4, 19.5), color=uc_color)
    create_wall(position=(2, 6, -11.25), scale=(0.2, 4, 7.5), color=uc_color)
    create_wall(position=(0, 8, 0), scale=(4, 0.2, 30), color=uc_ceiling_color)
    create_wall(position=(0, 6, -15), scale=(4, 4, 0.2), color=uc_color)

    # Upper corridor lighting - dim atmospheric
    upper_corridor_light_color = color.rgb(255, 170, 90)
    for z in (-12, -4, 4, 12):
        upper_light = PointLight(parent=scene, position=(0, 7.2, z), color=upper_corridor_light_color)
        flickering_lights.append(FlickeringLight(upper_light, interval_range=(0.1, 0.4), intensity_range=(0.25, 0.5)))
        # Light fixture
        Entity(
            model='cube',
            color=color.rgb(30, 25, 25),
            scale=(0.5, 0.12, 0.25),
            position=(0, 7.94, z),
            unlit=True
        )
        Entity(
            model='sphere',
            color=color.rgb(255, 190, 110),
            scale=0.1,
            position=(0, 7.8, z),
            unlit=True
        )
        # Light glow on ceiling
        Entity(
            model='quad',
            color=color.rgb(255, 200, 130),
            scale=(0.6, 0.6),
            position=(0, 7.9, z),
            rotation_x=90,
            alpha=0.12,
            unlit=True
        )

    # Upper Floor Dark Rooms - very dark, creepy
    dark_wall_color = color.rgb(35, 32, 40)
    dark_floor_color = color.rgb(20, 18, 22)
    dark_ceiling_color = color.rgb(18, 16, 20)

    # Room 203 - Storage (left side)
    room203_center = Vec3(-8, 4, 6)
    room203_size = Vec3(6, 4, 6)
    create_floor(position=room203_center, scale=(room203_size.x, 1, room203_size.z), color_value=dark_floor_color, texture=None)
    create_wall(position=(room203_center.x - room203_size.x / 2, room203_center.y + 2, room203_center.z), scale=(0.2, room203_size.y, room203_size.z), color=dark_wall_color, texture=None)
    create_wall(position=(room203_center.x + room203_size.x / 2, room203_center.y + 2, room203_center.z), scale=(0.2, room203_size.y, room203_size.z), color=dark_wall_color, texture=None)
    create_wall(position=(room203_center.x, room203_center.y + 2, room203_center.z + room203_size.z / 2), scale=(room203_size.x, room203_size.y, 0.2), color=dark_wall_color, texture=None)
    create_wall(position=(room203_center.x, room203_center.y + 2, room203_center.z - room203_size.z / 2), scale=(room203_size.x, room203_size.y, 0.2), color=dark_wall_color, texture=None)
    create_wall(position=(room203_center.x, room203_center.y + room203_size.y, room203_center.z), scale=(room203_size.x, 0.2, room203_size.z), color=dark_ceiling_color, texture=None)

    # Very dim ambient light so room is not pitch black
    PointLight(parent=scene, position=(room203_center.x, room203_center.y + 1.5, room203_center.z), color=color.rgb(8, 8, 12))
    # Main light (off by default)
    room203_light = PointLight(parent=scene, position=(room203_center.x, room203_center.y + 2, room203_center.z), color=color.rgb(255, 220, 200))
    room203_light.disable()

    room203_scare = Entity(
        model='quad',
        color=color.rgb(200, 20, 20),
        scale=(2.5, 2.5),
        position=(room203_center.x, room203_center.y + 1.5, room203_center.z - room203_size.z / 2 + 0.3),
        rotation_y=0,
        enabled=False,
        billboard=True
    )

    def reveal_room203():
        room203_scare.enabled = True

    storage_door = Door(
        position=(-2, 5.85, 6),
        rotation=(0, 0, 0),
        width=3.2,
        height=3.8,
        door_color=color.rgb(38, 28, 25)
    )
    add_door_label(storage_door, '203')

    LightSwitch(
        position=(-3.4, 5.5, 7.2),
        rotation=(0, 90, 0),
        light_source=room203_light,
        start_on=False,
        prompt_off='Press E to switch on lights (warning: jumpscare)',
        prompt_on='Press E to switch off lights',
        on_first_activate=reveal_room203
    )

    # Room 204 - Closet (right side)
    room204_center = Vec3(8, 4, -6)
    room204_size = Vec3(6, 4, 6)
    create_floor(position=room204_center, scale=(room204_size.x, 1, room204_size.z), color_value=dark_floor_color, texture=None)
    create_wall(position=(room204_center.x - room204_size.x / 2, room204_center.y + 2, room204_center.z), scale=(0.2, room204_size.y, room204_size.z), color=dark_wall_color, texture=None)
    create_wall(position=(room204_center.x + room204_size.x / 2, room204_center.y + 2, room204_center.z), scale=(0.2, room204_size.y, room204_size.z), color=dark_wall_color, texture=None)
    create_wall(position=(room204_center.x, room204_center.y + 2, room204_center.z + room204_size.z / 2), scale=(room204_size.x, room204_size.y, 0.2), color=dark_wall_color, texture=None)
    create_wall(position=(room204_center.x, room204_center.y + 2, room204_center.z - room204_size.z / 2), scale=(room204_size.x, room204_size.y, 0.2), color=dark_wall_color, texture=None)
    create_wall(position=(room204_center.x, room204_center.y + room204_size.y, room204_center.z), scale=(room204_size.x, 0.2, room204_size.z), color=dark_ceiling_color, texture=None)

    # Very dim ambient light so room is not pitch black
    PointLight(parent=scene, position=(room204_center.x, room204_center.y + 1.5, room204_center.z), color=color.rgb(10, 10, 15))
    # Main light (off by default)
    room204_light = PointLight(parent=scene, position=(room204_center.x, room204_center.y + 2, room204_center.z), color=color.rgb(220, 220, 255))
    room204_light.disable()

    room204_scare = Entity(
        model='quad',
        color=color.rgb(240, 0, 120),
        scale=(2.0, 2.0),
        position=(room204_center.x, room204_center.y + 1.5, room204_center.z + room204_size.z / 2 - 0.3),
        rotation_y=180,
        enabled=False,
        billboard=True
    )

    def reveal_room204():
        room204_scare.enabled = True

    closet_door = Door(
        position=(2, 5.85, -6),
        rotation=(0, 180, 0),
        width=3.2,
        height=3.8,
        door_color=color.rgb(35, 26, 24)
    )
    add_door_label(closet_door, '204')

    LightSwitch(
        position=(3.4, 5.5, -7.2),
        rotation=(0, -90, 0),
        light_source=room204_light,
        start_on=False,
        prompt_off='Press E to switch on lights (brace yourself)',
        prompt_on='Press E to switch off lights',
        on_first_activate=reveal_room204
    )
    
    # Master Bedroom (at z=-20, connected to corridor end) - dark moody
    br_color = color.rgb(70, 50, 75)  # Dark purple-gray
    br_ceiling_color = color.rgb(25, 22, 28)
    br_floor_color = color.rgb(55, 38, 30)  # Dark wood
    create_floor(position=(0, 4, -20), scale=(10, 1, 10), color_value=br_floor_color)
    create_wall(position=(0, 8, -20), scale=(10, 0.2, 10), color=br_ceiling_color)
    create_wall(position=(-5, 6, -20), scale=(0.2, 4, 10), color=br_color)
    create_wall(position=(5, 6, -20), scale=(0.2, 4, 10), color=br_color)
    create_wall(position=(0, 6, -25), scale=(10, 4, 0.2), color=br_color)
    
    # Wall between bedroom and corridor (with door)
    create_wall(position=(-3.25, 6, -15), scale=(3.5, 4, 0.2), color=uc_color)
    create_wall(position=(3.25, 6, -15), scale=(3.5, 4, 0.2), color=uc_color)
    create_wall(position=(0, 7.75, -15), scale=(3, 0.5, 0.2), color=uc_color)
    
    # Door to Bedroom - dark wood
    bedroom_door = Door(
        position=(-1.5, 5.85, -15),
        rotation=(0, 0, 0),
        width=3.4,
        height=3.8,
        door_color=color.rgb(40, 28, 25)
    )
    add_door_label(bedroom_door, '201')
    
    # Dim ambient light for Bedroom (always on, very subtle)
    PointLight(parent=scene, position=(0, 5.5, -20), color=color.rgb(25, 25, 35))
    # Main light for Bedroom (switchable)
    br_light = PointLight(parent=scene, position=(0, 7.5, -20), color=color.rgb(180, 200, 255))
    # Light fixture - ceiling lamp
    Entity(model='sphere', color=color.rgb(200, 220, 255), scale=0.35, position=(0, 7.7, -20), unlit=True)
    Entity(model='cube', color=color.rgb(60, 60, 70), scale=(0.1, 0.3, 0.1), position=(0, 7.9, -20), unlit=True)
    LightSwitch(position=(1, 5.5, -15.2), rotation=(0, 180, 0), light_source=br_light)

    # -------------------
    # DARK ROOMS (Ground Floor)
    # -------------------
    
    # Room 103 - Janitor Closet (small dark room off living room)
    room103_center = Vec3(-10, 0, -3.5)
    room103_size = Vec3(3, 3.5, 3)
    create_floor(position=room103_center, scale=(room103_size.x, 1, room103_size.z), color_value=dark_floor_color, texture=None)
    create_wall(position=(room103_center.x - room103_size.x / 2, room103_center.y + room103_size.y / 2, room103_center.z), scale=(0.2, room103_size.y, room103_size.z), color=dark_wall_color, texture=None)
    create_wall(position=(room103_center.x + room103_size.x / 2, room103_center.y + room103_size.y / 2, room103_center.z), scale=(0.2, room103_size.y, room103_size.z), color=dark_wall_color, texture=None)
    create_wall(position=(room103_center.x, room103_center.y + room103_size.y / 2, room103_center.z + room103_size.z / 2), scale=(room103_size.x, room103_size.y, 0.2), color=dark_wall_color, texture=None)
    create_wall(position=(room103_center.x, room103_center.y + room103_size.y / 2, room103_center.z - room103_size.z / 2), scale=(room103_size.x, room103_size.y, 0.2), color=dark_wall_color, texture=None)
    create_wall(position=(room103_center.x, room103_center.y + room103_size.y, room103_center.z), scale=(room103_size.x, 0.2, room103_size.z), color=dark_ceiling_color, texture=None)

    # Very dim ambient light so room is not pitch black
    PointLight(parent=scene, position=(room103_center.x, room103_center.y + 1, room103_center.z), color=color.rgb(6, 6, 10))
    # Main light (off by default)
    room103_light = PointLight(parent=scene, position=(room103_center.x, room103_center.y + 2, room103_center.z), color=color.rgb(255, 180, 150))
    room103_light.disable()

    # Creepy figure in the corner
    room103_scare = Entity(
        model='cube',
        color=color.rgb(20, 20, 25),
        scale=(0.6, 1.8, 0.4),
        position=(room103_center.x - 0.8, room103_center.y + 0.9, room103_center.z - 0.8),
        enabled=False
    )
    # Glowing eyes
    room103_eye1 = Entity(
        model='sphere',
        color=color.red,
        scale=0.1,
        position=(room103_center.x - 0.8, room103_center.y + 1.5, room103_center.z - 0.6),
        enabled=False,
        unlit=True
    )
    room103_eye2 = Entity(
        model='sphere',
        color=color.red,
        scale=0.1,
        position=(room103_center.x - 0.6, room103_center.y + 1.5, room103_center.z - 0.6),
        enabled=False,
        unlit=True
    )

    def reveal_room103():
        room103_scare.enabled = True
        room103_eye1.enabled = True
        room103_eye2.enabled = True

    room103_door = Door(
        position=(-8.5, 1.65, -3.5),
        rotation=(0, 90, 0),
        width=2.5,
        height=3.2,
        door_color=color.rgb(32, 24, 22)
    )
    add_door_label(room103_door, '103')

    # Dark room prompt text indicator
    room103_prompt = Text(
        text='[Press E to switch on lights]',
        position=(-10, 1.5, -2),
        origin=(0, 0),
        scale=8,
        color=color.rgba(255, 255, 255, 180),
        billboard=True
    )

    LightSwitch(
        position=(-8.4, 1.2, -2.2),
        rotation=(0, -90, 0),
        light_source=room103_light,
        start_on=False,
        prompt_off='Press E to switch on lights',
        prompt_on='Press E to switch off lights',
        on_first_activate=reveal_room103
    )

    # Room 104 - Utility Closet (small dark room off kitchen)
    room104_center = Vec3(10, 0, 3.5)
    room104_size = Vec3(3, 3.5, 3)
    create_floor(position=room104_center, scale=(room104_size.x, 1, room104_size.z), color_value=dark_floor_color, texture=None)
    create_wall(position=(room104_center.x - room104_size.x / 2, room104_center.y + room104_size.y / 2, room104_center.z), scale=(0.2, room104_size.y, room104_size.z), color=dark_wall_color, texture=None)
    create_wall(position=(room104_center.x + room104_size.x / 2, room104_center.y + room104_size.y / 2, room104_center.z), scale=(0.2, room104_size.y, room104_size.z), color=dark_wall_color, texture=None)
    create_wall(position=(room104_center.x, room104_center.y + room104_size.y / 2, room104_center.z + room104_size.z / 2), scale=(room104_size.x, room104_size.y, 0.2), color=dark_wall_color, texture=None)
    create_wall(position=(room104_center.x, room104_center.y + room104_size.y / 2, room104_center.z - room104_size.z / 2), scale=(room104_size.x, room104_size.y, 0.2), color=dark_wall_color, texture=None)
    create_wall(position=(room104_center.x, room104_center.y + room104_size.y, room104_center.z), scale=(room104_size.x, 0.2, room104_size.z), color=dark_ceiling_color, texture=None)

    # Very dim ambient light so room is not pitch black
    PointLight(parent=scene, position=(room104_center.x, room104_center.y + 1, room104_center.z), color=color.rgb(8, 10, 8))
    # Main light (off by default)
    room104_light = PointLight(parent=scene, position=(room104_center.x, room104_center.y + 2, room104_center.z), color=color.rgb(200, 255, 200))
    room104_light.disable()

    # Hanging body silhouette
    room104_scare = Entity(
        model='cube',
        color=color.rgb(30, 25, 25),
        scale=(0.5, 1.5, 0.3),
        position=(room104_center.x, room104_center.y + 1.8, room104_center.z),
        enabled=False
    )
    room104_rope = Entity(
        model='cube',
        color=color.rgb(80, 60, 40),
        scale=(0.05, 1.0, 0.05),
        position=(room104_center.x, room104_center.y + 3.0, room104_center.z),
        enabled=False
    )

    def reveal_room104():
        room104_scare.enabled = True
        room104_rope.enabled = True

    room104_door = Door(
        position=(8.5, 1.65, 3.5),
        rotation=(0, -90, 0),
        width=2.5,
        height=3.2,
        door_color=color.rgb(30, 25, 22)
    )
    add_door_label(room104_door, '104')

    # Dark room prompt text indicator
    room104_prompt = Text(
        text='[Press E to switch on lights]',
        position=(10, 1.5, 2),
        origin=(0, 0),
        scale=8,
        color=color.rgba(255, 255, 255, 180),
        billboard=True
    )

    LightSwitch(
        position=(8.4, 1.2, 4.8),
        rotation=(0, 90, 0),
        light_source=room104_light,
        start_on=False,
        prompt_off='Press E to switch on lights',
        prompt_on='Press E to switch off lights',
        on_first_activate=reveal_room104
    )

    # -------------------
    # UPPER FLOOR EXTRA DARK ROOM
    # -------------------
    
    # Room 202 - Small Bathroom (dark, next to bedroom)
    room202_center = Vec3(-4, 4, -22)
    room202_size = Vec3(2.5, 3.5, 4)
    create_floor(position=room202_center, scale=(room202_size.x, 1, room202_size.z), color_value=dark_floor_color, texture=None)
    create_wall(position=(room202_center.x - room202_size.x / 2, room202_center.y + room202_size.y / 2, room202_center.z), scale=(0.2, room202_size.y, room202_size.z), color=dark_wall_color, texture=None)
    create_wall(position=(room202_center.x + room202_size.x / 2, room202_center.y + room202_size.y / 2, room202_center.z), scale=(0.2, room202_size.y, room202_size.z), color=dark_wall_color, texture=None)
    create_wall(position=(room202_center.x, room202_center.y + room202_size.y / 2, room202_center.z + room202_size.z / 2), scale=(room202_size.x, room202_size.y, 0.2), color=dark_wall_color, texture=None)
    create_wall(position=(room202_center.x, room202_center.y + room202_size.y / 2, room202_center.z - room202_size.z / 2), scale=(room202_size.x, room202_size.y, 0.2), color=dark_wall_color, texture=None)
    create_wall(position=(room202_center.x, room202_center.y + room202_size.y, room202_center.z), scale=(room202_size.x, 0.2, room202_size.z), color=dark_ceiling_color, texture=None)

    # Very dim ambient light so room is not pitch black
    PointLight(parent=scene, position=(room202_center.x, room202_center.y + 1, room202_center.z), color=color.rgb(10, 10, 15))
    # Main light (off by default)
    room202_light = PointLight(parent=scene, position=(room202_center.x, room202_center.y + 2, room202_center.z), color=color.rgb(255, 255, 255))
    room202_light.disable()

    # Mirror with face appearing
    room202_mirror = Entity(
        model='quad',
        color=color.rgb(180, 180, 200),
        scale=(1.2, 1.5),
        position=(room202_center.x, room202_center.y + 1.3, room202_center.z - room202_size.z / 2 + 0.15),
        rotation_y=0
    )
    room202_face = Entity(
        model='quad',
        color=color.rgb(150, 100, 100),
        scale=(0.8, 1.0),
        position=(room202_center.x, room202_center.y + 1.3, room202_center.z - room202_size.z / 2 + 0.2),
        rotation_y=0,
        enabled=False
    )
    # Creepy smile
    room202_smile = Text(
        text=':)',
        position=(room202_center.x, room202_center.y + 1.2, room202_center.z - room202_size.z / 2 + 0.25),
        origin=(0, 0),
        scale=25,
        color=color.rgb(50, 0, 0),
        billboard=False,
        enabled=False
    )

    def reveal_room202():
        room202_face.enabled = True
        room202_smile.enabled = True

    room202_door = Door(
        position=(-2.75, 5.65, -22),
        rotation=(0, 90, 0),
        width=2.2,
        height=3.2,
        door_color=color.rgb(36, 28, 26)
    )
    add_door_label(room202_door, '202')

    # Dark room prompt text indicator
    room202_prompt = Text(
        text='[Press E to switch on lights]',
        position=(-4, 5.5, -20.5),
        origin=(0, 0),
        scale=6,
        color=color.rgba(255, 255, 255, 180),
        billboard=True
    )

    LightSwitch(
        position=(-3, 5.3, -20.2),
        rotation=(0, 0, 0),
        light_source=room202_light,
        start_on=False,
        prompt_off='Press E to switch on lights',
        prompt_on='Press E to switch off lights',
        on_first_activate=reveal_room202
    )

    # Add prompt text indicators for existing dark rooms 203 and 204
    room203_prompt = Text(
        text='[Press E to switch on lights]',
        position=(-6, 5.5, 6),
        origin=(0, 0),
        scale=8,
        color=color.rgba(255, 255, 255, 180),
        billboard=True
    )

    room204_prompt = Text(
        text='[Press E to switch on lights]',
        position=(6, 5.5, -6),
        origin=(0, 0),
        scale=8,
        color=color.rgba(255, 255, 255, 180),
        billboard=True
    )

    # -------------------
    # ADDITIONAL UPPER FLOOR ROOMS
    # -------------------
    
    # Room 205 - Study (right side, forward)
    room205_color = color.rgb(60, 45, 50)  # Dark brown-red
    room205_center = Vec3(8, 4, 10)
    room205_size = Vec3(6, 4, 6)
    create_floor(position=room205_center, scale=(room205_size.x, 1, room205_size.z), color_value=uc_floor_color)
    create_wall(position=(room205_center.x - room205_size.x / 2, room205_center.y + 2, room205_center.z), scale=(0.2, room205_size.y, room205_size.z), color=room205_color)
    create_wall(position=(room205_center.x + room205_size.x / 2, room205_center.y + 2, room205_center.z), scale=(0.2, room205_size.y, room205_size.z), color=room205_color)
    create_wall(position=(room205_center.x, room205_center.y + 2, room205_center.z + room205_size.z / 2), scale=(room205_size.x, room205_size.y, 0.2), color=room205_color)
    create_wall(position=(room205_center.x, room205_center.y + 2, room205_center.z - room205_size.z / 2), scale=(room205_size.x, room205_size.y, 0.2), color=room205_color)
    create_wall(position=(room205_center.x, room205_center.y + room205_size.y, room205_center.z), scale=(room205_size.x, 0.2, room205_size.z), color=uc_ceiling_color)
    
    # Room 205 lighting
    PointLight(parent=scene, position=(room205_center.x, room205_center.y + 1.5, room205_center.z), color=color.rgb(20, 18, 22))
    room205_light = PointLight(parent=scene, position=(room205_center.x, room205_center.y + 3, room205_center.z), color=color.rgb(255, 200, 150))
    Entity(model='sphere', color=color.rgb(255, 210, 160), scale=0.2, position=(room205_center.x, room205_center.y + 3.5, room205_center.z), unlit=True)
    
    room205_door = Door(position=(2, 5.85, 10), rotation=(0, 180, 0), width=3.2, height=3.8, door_color=color.rgb(42, 30, 26))
    add_door_label(room205_door, '205')
    LightSwitch(position=(3.5, 5.5, 8.5), rotation=(0, -90, 0), light_source=room205_light)
    
    # Room 206 - Library (left side, back) - larger room
    room206_color = color.rgb(50, 35, 45)  # Dark plum
    room206_center = Vec3(-9, 4, -8)
    room206_size = Vec3(8, 4, 8)
    create_floor(position=room206_center, scale=(room206_size.x, 1, room206_size.z), color_value=uc_floor_color)
    create_wall(position=(room206_center.x - room206_size.x / 2, room206_center.y + 2, room206_center.z), scale=(0.2, room206_size.y, room206_size.z), color=room206_color)
    create_wall(position=(room206_center.x + room206_size.x / 2, room206_center.y + 2, room206_center.z), scale=(0.2, room206_size.y, room206_size.z), color=room206_color)
    create_wall(position=(room206_center.x, room206_center.y + 2, room206_center.z + room206_size.z / 2), scale=(room206_size.x, room206_size.y, 0.2), color=room206_color)
    create_wall(position=(room206_center.x, room206_center.y + 2, room206_center.z - room206_size.z / 2), scale=(room206_size.x, room206_size.y, 0.2), color=room206_color)
    create_wall(position=(room206_center.x, room206_center.y + room206_size.y, room206_center.z), scale=(room206_size.x, 0.2, room206_size.z), color=uc_ceiling_color)
    
    # Bookshelves in library
    for shelf_z in [-10, -8, -6]:
        Entity(model='cube', color=color.rgb(35, 25, 20), scale=(0.3, 2.5, 1.5), position=(-12.5, 5.25, shelf_z), unlit=True)
    
    # Room 206 lighting
    PointLight(parent=scene, position=(room206_center.x, room206_center.y + 1.5, room206_center.z), color=color.rgb(18, 15, 20))
    room206_light = PointLight(parent=scene, position=(room206_center.x, room206_center.y + 3, room206_center.z), color=color.rgb(255, 220, 180))
    
    room206_door = Door(position=(-2, 5.85, -8), rotation=(0, 0, 0), width=3.2, height=3.8, door_color=color.rgb(38, 28, 24))
    add_door_label(room206_door, '206')
    LightSwitch(position=(-3.5, 5.5, -6.5), rotation=(0, 90, 0), light_source=room206_light)

    # -------------------
    # THIRD FLOOR (Attic Level)
    # -------------------
    
    # Stairs from floor 2 to floor 3 (at opposite end)
    for i in range(10):
        Entity(
            model='cube',
            color=color.rgb(40, 28, 24),
            position=(0, 4 + i*0.4, -26 - i*0.5),
            scale=(3.5, 0.4, 0.5),
            collider='box'
        )
    
    # Third floor corridor - narrower, darker, creepier
    floor3_y = 8
    floor3_color = color.rgb(55, 20, 28)  # Darker red
    floor3_ceiling = color.rgb(18, 14, 16)
    floor3_floor = color.rgb(50, 32, 24)
    
    # Third floor landing
    create_floor(position=(0, floor3_y, -30), scale=(3.5, 1, 4), color_value=floor3_floor)
    
    # Third floor main corridor
    create_floor(position=(0, floor3_y, -40), scale=(3.5, 1, 20), color_value=floor3_floor)
    create_wall(position=(0, floor3_y + 3.5, -40), scale=(3.5, 0.2, 20), color=floor3_ceiling)
    create_wall(position=(-1.75, floor3_y + 1.75, -40), scale=(0.2, 3.5, 20), color=floor3_color)
    create_wall(position=(1.75, floor3_y + 1.75, -40), scale=(0.2, 3.5, 20), color=floor3_color)
    create_wall(position=(0, floor3_y + 1.75, -50), scale=(3.5, 3.5, 0.2), color=floor3_color)
    
    # Baseboards floor 3
    Entity(model='cube', color=color.rgb(30, 22, 18), scale=(0.22, 0.25, 20), position=(-1.65, floor3_y + 0.12, -40), unlit=True)
    Entity(model='cube', color=color.rgb(30, 22, 18), scale=(0.22, 0.25, 20), position=(1.65, floor3_y + 0.12, -40), unlit=True)
    
    # Third floor lighting - very dim, more flickering
    for z in (-33, -40, -47):
        f3_light = PointLight(parent=scene, position=(0, floor3_y + 3, z), color=color.rgb(255, 160, 80))
        flickering_lights.append(FlickeringLight(f3_light, interval_range=(0.05, 0.2), intensity_range=(0.15, 0.4)))
        Entity(model='sphere', color=color.rgb(255, 180, 100), scale=0.08, position=(0, floor3_y + 3.3, z), unlit=True)
    
    # Room 301 - The Forbidden Room (left side) - DARK with jumpscare
    room301_center = Vec3(-5, floor3_y, -36)
    room301_size = Vec3(5, 3.5, 5)
    create_floor(position=room301_center, scale=(room301_size.x, 1, room301_size.z), color_value=dark_floor_color)
    create_wall(position=(room301_center.x - room301_size.x / 2, room301_center.y + room301_size.y / 2, room301_center.z), scale=(0.2, room301_size.y, room301_size.z), color=dark_wall_color)
    create_wall(position=(room301_center.x + room301_size.x / 2, room301_center.y + room301_size.y / 2, room301_center.z), scale=(0.2, room301_size.y, room301_size.z), color=dark_wall_color)
    create_wall(position=(room301_center.x, room301_center.y + room301_size.y / 2, room301_center.z + room301_size.z / 2), scale=(room301_size.x, room301_size.y, 0.2), color=dark_wall_color)
    create_wall(position=(room301_center.x, room301_center.y + room301_size.y / 2, room301_center.z - room301_size.z / 2), scale=(room301_size.x, room301_size.y, 0.2), color=dark_wall_color)
    create_wall(position=(room301_center.x, room301_center.y + room301_size.y, room301_center.z), scale=(room301_size.x, 0.2, room301_size.z), color=dark_ceiling_color)
    
    PointLight(parent=scene, position=(room301_center.x, room301_center.y + 1, room301_center.z), color=color.rgb(5, 4, 6))
    room301_light = PointLight(parent=scene, position=(room301_center.x, room301_center.y + 2.5, room301_center.z), color=color.rgb(255, 100, 100))
    room301_light.disable()
    
    # Creepy child figure
    room301_scare = Entity(model='cube', color=color.rgb(15, 12, 15), scale=(0.4, 1.2, 0.3), 
                           position=(room301_center.x - 1.5, room301_center.y + 0.6, room301_center.z - 1.5), enabled=False, unlit=True)
    room301_eyes = Entity(model='quad', color=color.rgb(255, 255, 255), scale=(0.25, 0.1),
                          position=(room301_center.x - 1.5, room301_center.y + 1.0, room301_center.z - 1.35), enabled=False, unlit=True)
    
    def reveal_room301():
        room301_scare.enabled = True
        room301_eyes.enabled = True
    
    room301_door = Door(position=(-1.75, floor3_y + 1.65, -36), rotation=(0, 0, 0), width=2.8, height=3.2, door_color=color.rgb(28, 20, 18))
    add_door_label(room301_door, '301')
    
    room301_prompt = Text(text='[Press E to switch on lights]', position=(-5, floor3_y + 1.5, -34.5), origin=(0, 0), scale=6, color=color.rgba(255, 255, 255, 180), billboard=True)
    
    LightSwitch(position=(-2.5, floor3_y + 1.2, -34.5), rotation=(0, 90, 0), light_source=room301_light, start_on=False,
                prompt_off='Press E to switch on lights', prompt_on='Press E to switch off lights', on_first_activate=reveal_room301)
    
    # Room 302 - The Red Room (right side) - DARK with jumpscare
    room302_center = Vec3(5, floor3_y, -44)
    room302_size = Vec3(5, 3.5, 5)
    room302_wall_color = color.rgb(60, 15, 15)  # Blood red
    create_floor(position=room302_center, scale=(room302_size.x, 1, room302_size.z), color_value=color.rgb(25, 12, 12))
    create_wall(position=(room302_center.x - room302_size.x / 2, room302_center.y + room302_size.y / 2, room302_center.z), scale=(0.2, room302_size.y, room302_size.z), color=room302_wall_color)
    create_wall(position=(room302_center.x + room302_size.x / 2, room302_center.y + room302_size.y / 2, room302_center.z), scale=(0.2, room302_size.y, room302_size.z), color=room302_wall_color)
    create_wall(position=(room302_center.x, room302_center.y + room302_size.y / 2, room302_center.z + room302_size.z / 2), scale=(room302_size.x, room302_size.y, 0.2), color=room302_wall_color)
    create_wall(position=(room302_center.x, room302_center.y + room302_size.y / 2, room302_center.z - room302_size.z / 2), scale=(room302_size.x, room302_size.y, 0.2), color=room302_wall_color)
    create_wall(position=(room302_center.x, room302_center.y + room302_size.y, room302_center.z), scale=(room302_size.x, 0.2, room302_size.z), color=color.rgb(30, 10, 10))
    
    PointLight(parent=scene, position=(room302_center.x, room302_center.y + 1, room302_center.z), color=color.rgb(8, 3, 3))
    room302_light = PointLight(parent=scene, position=(room302_center.x, room302_center.y + 2.5, room302_center.z), color=color.rgb(255, 50, 50))
    room302_light.disable()
    
    # Blood stain on wall
    room302_stain = Entity(model='quad', color=color.rgb(80, 10, 10), scale=(1.5, 1.2),
                           position=(room302_center.x, room302_center.y + 1.5, room302_center.z - room302_size.z / 2 + 0.15), enabled=False, unlit=True)
    # Written message
    room302_msg = Text(text='GET OUT', position=(room302_center.x, room302_center.y + 2, room302_center.z - room302_size.z / 2 + 0.2),
                       origin=(0, 0), scale=15, color=color.rgb(120, 20, 20), billboard=False, enabled=False)
    
    def reveal_room302():
        room302_stain.enabled = True
        room302_msg.enabled = True
    
    room302_door = Door(position=(1.75, floor3_y + 1.65, -44), rotation=(0, 180, 0), width=2.8, height=3.2, door_color=color.rgb(35, 18, 18))
    add_door_label(room302_door, '302')
    
    room302_prompt = Text(text='[Press E to switch on lights]', position=(5, floor3_y + 1.5, -42.5), origin=(0, 0), scale=6, color=color.rgba(255, 255, 255, 180), billboard=True)
    
    LightSwitch(position=(2.5, floor3_y + 1.2, -42.5), rotation=(0, -90, 0), light_source=room302_light, start_on=False,
                prompt_off='Press E to switch on lights', prompt_on='Press E to switch off lights', on_first_activate=reveal_room302)
    
    # Room 303 - End of hallway - The Final Room (pitch black with major scare)
    room303_center = Vec3(0, floor3_y, -55)
    room303_size = Vec3(6, 4, 6)
    create_floor(position=room303_center, scale=(room303_size.x, 1, room303_size.z), color_value=color.rgb(10, 8, 10))
    create_wall(position=(room303_center.x - room303_size.x / 2, room303_center.y + 2, room303_center.z), scale=(0.2, room303_size.y, room303_size.z), color=color.rgb(20, 15, 20))
    create_wall(position=(room303_center.x + room303_size.x / 2, room303_center.y + 2, room303_center.z), scale=(0.2, room303_size.y, room303_size.z), color=color.rgb(20, 15, 20))
    create_wall(position=(room303_center.x, room303_center.y + 2, room303_center.z + room303_size.z / 2), scale=(room303_size.x, room303_size.y, 0.2), color=color.rgb(20, 15, 20))
    create_wall(position=(room303_center.x, room303_center.y + 2, room303_center.z - room303_size.z / 2), scale=(room303_size.x, room303_size.y, 0.2), color=color.rgb(20, 15, 20))
    create_wall(position=(room303_center.x, room303_center.y + room303_size.y, room303_center.z), scale=(room303_size.x, 0.2, room303_size.z), color=color.rgb(12, 10, 12))
    
    PointLight(parent=scene, position=(room303_center.x, room303_center.y + 1, room303_center.z), color=color.rgb(3, 2, 4))
    room303_light = PointLight(parent=scene, position=(room303_center.x, room303_center.y + 3, room303_center.z), color=color.rgb(255, 255, 255))
    room303_light.disable()
    
    # The thing in the center of the room
    room303_scare = Entity(model='cube', color=color.rgb(0, 0, 0), scale=(1, 2.2, 0.5),
                           position=(room303_center.x, room303_center.y + 1.1, room303_center.z), enabled=False, unlit=True)
    room303_face = Entity(model='quad', color=color.rgb(200, 180, 170), scale=(0.6, 0.8),
                          position=(room303_center.x, room303_center.y + 1.8, room303_center.z + 0.26), enabled=False, unlit=True)
    room303_smile = Text(text=':)', position=(room303_center.x, room303_center.y + 1.7, room303_center.z + 0.3),
                         origin=(0, 0), scale=20, color=color.rgb(150, 0, 0), billboard=False, enabled=False)
    
    def reveal_room303():
        room303_scare.enabled = True
        room303_face.enabled = True
        room303_smile.enabled = True
    
    room303_door = Door(position=(0, floor3_y + 1.85, -52), rotation=(0, 0, 0), width=3, height=3.5, door_color=color.rgb(22, 15, 15))
    add_door_label(room303_door, '303')
    
    room303_prompt = Text(text='[Press E to switch on lights]', position=(0, floor3_y + 1.5, -53.5), origin=(0, 0), scale=6, color=color.rgba(255, 255, 255, 180), billboard=True)
    
    LightSwitch(position=(1.5, floor3_y + 1.2, -52.2), rotation=(0, 180, 0), light_source=room303_light, start_on=False,
                prompt_off='Press E to switch on lights', prompt_on='Press E to switch off lights', on_first_activate=reveal_room303)

    # -------------------
    # WALL DECORATIONS & ATMOSPHERE
    # -------------------
    
    # Paintings/frames on corridor walls (ground floor)
    for z in [-10, -6, 2, 8]:
        # Left wall frames
        Entity(model='cube', color=color.rgb(40, 30, 25), scale=(0.05, 1.2, 0.8), position=(-1.9, 2.2, z), unlit=True)
        Entity(model='quad', color=color.rgb(30, 20, 25), scale=(0.7, 1.1), position=(-1.85, 2.2, z), rotation_y=90, unlit=True)
        # Right wall frames
        Entity(model='cube', color=color.rgb(40, 30, 25), scale=(0.05, 1.2, 0.8), position=(1.9, 2.2, z + 1), unlit=True)
        Entity(model='quad', color=color.rgb(25, 18, 22), scale=(0.7, 1.1), position=(1.85, 2.2, z + 1), rotation_y=-90, unlit=True)
    
    # Upper floor frames
    for z in [-10, -2, 4, 10]:
        Entity(model='cube', color=color.rgb(38, 28, 24), scale=(0.05, 1.0, 0.7), position=(-1.9, 6.2, z), unlit=True)
        Entity(model='quad', color=color.rgb(35, 22, 28), scale=(0.6, 0.9), position=(-1.85, 6.2, z), rotation_y=90, unlit=True)
    
    # Floor 3 - creepy paintings
    for z in [-35, -42, -48]:
        Entity(model='cube', color=color.rgb(30, 22, 20), scale=(0.04, 0.8, 0.6), position=(-1.65, floor3_y + 1.8, z), unlit=True)
        Entity(model='quad', color=color.rgb(40, 15, 20), scale=(0.5, 0.7), position=(-1.6, floor3_y + 1.8, z), rotation_y=90, unlit=True)

    # Staircase lighting - dim
    for i in range(0, 10, 3):
        stair_light = PointLight(parent=scene, position=(0, i*0.4 + 1.5, 15 + i*0.5), color=color.rgb(180, 140, 80))
        flickering_lights.append(FlickeringLight(stair_light, interval_range=(0.15, 0.5), intensity_range=(0.2, 0.45)))
    
    # Staircase lighting floor 2 to 3
    for i in range(0, 10, 3):
        stair_light2 = PointLight(parent=scene, position=(0, 4 + i*0.4 + 1, -26 - i*0.5), color=color.rgb(160, 120, 70))
        flickering_lights.append(FlickeringLight(stair_light2, interval_range=(0.1, 0.35), intensity_range=(0.15, 0.35)))

    # Global ambient light - very dark for horror atmosphere
    AmbientLight(color=color.rgba(8, 6, 10, 255))

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
                target = resolve_interactable(hit_info.entity)
                if isinstance(target, LightSwitch):
                    target.toggle()
                elif isinstance(target, Door):
                    target.toggle()

# -------------------------------
# UPDATE LOOP
# -------------------------------
def update():
    for controller in flickering_lights:
        controller.update()

    if game_state != 'game':
        return

    global current_focus

    hit_info = raycast(camera.world_position, camera.forward, distance=5)
    target = resolve_interactable(hit_info.entity) if hit_info.hit else None

    target_text = interaction_text_for(target) if target else ''

    if target != current_focus or (interaction_prompt and interaction_prompt.enabled and interaction_prompt.text != target_text):
        current_focus = target
        if target and interaction_prompt:
            interaction_prompt.text = target_text
            interaction_prompt.enabled = True
            if player and player.cursor:
                player.cursor.color = highlight_cursor_color
        else:
            if interaction_prompt:
                interaction_prompt.enabled = False
            if player and player.cursor:
                player.cursor.color = default_cursor_color

app.run()
