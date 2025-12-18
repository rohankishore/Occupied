from ursina import *
from ursina.prefabs.first_person_controller import FirstPersonController
from random import uniform

app = Ursina(borderless=False)
window.title = 'HOME'
window.color = color.black
mouse.visible = True

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
            **kwargs
        )
        self.is_open = False

    def toggle(self):
        self.is_open = not self.is_open
        if self.is_open:
            self.animate_rotation_y(self.rotation_y + 90, duration=0.5)
        else:
            self.animate_rotation_y(self.rotation_y - 90, duration=0.5)

def create_wall(position, scale, color=color.white, texture='white_cube'):
    e = Entity(
        model='cube', 
        position=position, 
        scale=scale, 
        color=color, 
        texture=texture, 
        collider='box'
    )
    if texture:
        e.texture_scale = (scale[0], scale[1])
    return e

def create_floor(position, scale, color_value=color.gray, texture='white_cube'):
    e = Entity(
        model='plane', 
        position=position, 
        scale=scale, 
        color=color_value, 
        texture=texture, 
        collider='box'
    )
    if texture:
        e.texture_scale = (scale[0], scale[2])
    return e


def add_door_label(door, label_text):
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
    
    # Main Corridor (Ground)
    corridor_color = color.rgb(212, 195, 178)
    corridor_ceiling_color = color.rgb(245, 237, 224)
    # Floor
    create_floor(position=(0, 0, 0), scale=(4, 1, 30))
    # Ceiling
    create_wall(position=(0, 4, 0), scale=(4, 0.2, 30), color=corridor_ceiling_color)
    
    # Corridor Walls
    # Left wall segments (leaving gaps for doors)
    # Gap at z=0. Wall from -15 to -1.5 (len 13.5) and 1.5 to 15 (len 13.5)
    # Let's make the gap 3 units wide (-1.5 to 1.5)
    create_wall(position=(-2, 2, -8.25), scale=(0.2, 4, 13.5), color=corridor_color) # Back part
    create_wall(position=(-2, 2, 8.25), scale=(0.2, 4, 13.5), color=corridor_color)  # Front part
    create_wall(position=(-2, 3.75, 0), scale=(0.2, 0.5, 3), color=corridor_color) # Above door
    
    # Door to Living Room
    living_room_door = Door(
        position=(-2, 1.85, -1.5),
        rotation=(0, 0, 0),
        height=3.8,
        door_color=color.rgb(155, 115, 95)
    )
    add_door_label(living_room_door, '101')

    # Right wall segments
    create_wall(position=(2, 2, -8.25), scale=(0.2, 4, 13.5), color=corridor_color)
    create_wall(position=(2, 2, 8.25), scale=(0.2, 4, 13.5), color=corridor_color)
    create_wall(position=(2, 3.75, 0), scale=(0.2, 0.5, 3), color=corridor_color)
    
    # Door to Kitchen
    kitchen_door = Door(
        position=(2, 1.85, 1.5),
        rotation=(0, 180, 0),
        height=3.8,
        door_color=color.rgb(120, 150, 170)
    )
    add_door_label(kitchen_door, '102')

    # Corridor lighting
    corridor_light_color = color.rgb(255, 236, 200)
    for z in (-12, -4, 4, 12):
        light = PointLight(parent=scene, position=(0, 2.8, z), color=corridor_light_color)
        flickering_lights.append(FlickeringLight(light))

    # End walls
    create_wall(position=(0, 2, -15), scale=(4, 4, 0.2), color=corridor_color) # Entrance
    # (Other end is stairs)

    # Living Room (Left)
    lr_color = color.rgb(214, 168, 146)
    lr_ceiling_color = color.rgb(238, 210, 188)
    # Floor
    create_floor(position=(-7, 0, 0), scale=(10, 1, 10))
    # Ceiling
    create_wall(position=(-7, 4, 0), scale=(10, 0.2, 10), color=lr_ceiling_color)
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
    k_color = color.rgb(167, 206, 188)
    k_ceiling_color = color.rgb(230, 242, 236)
    # Floor
    create_floor(position=(7, 0, 0), scale=(10, 1, 10))
    # Ceiling
    create_wall(position=(7, 4, 0), scale=(10, 0.2, 10), color=k_ceiling_color)
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
    uc_color = color.rgb(205, 200, 190)
    uc_ceiling_color = color.rgb(236, 230, 220)
    create_floor(position=(0, 4, 0), scale=(4, 1, 30)) 
    
    # Upper Corridor Walls (segmented for additional rooms)
    create_wall(position=(-2, 6, -5.25), scale=(0.2, 4, 19.5), color=uc_color)
    create_wall(position=(-2, 6, 11.25), scale=(0.2, 4, 7.5), color=uc_color)
    create_wall(position=(2, 6, 5.25), scale=(0.2, 4, 19.5), color=uc_color)
    create_wall(position=(2, 6, -11.25), scale=(0.2, 4, 7.5), color=uc_color)
    create_wall(position=(0, 8, 0), scale=(4, 0.2, 30), color=uc_ceiling_color)
    create_wall(position=(0, 6, -15), scale=(4, 4, 0.2), color=uc_color) # End

    # Upper Floor Dark Rooms
    dark_wall_color = color.rgb(70, 70, 90)
    dark_floor_color = color.rgb(30, 30, 35)
    dark_ceiling_color = color.rgb(55, 55, 65)

    # Room 203 - Storage (left side)
    room203_center = Vec3(-8, 4, 6)
    room203_size = Vec3(6, 4, 6)
    create_floor(position=room203_center, scale=(room203_size.x, 1, room203_size.z), color_value=dark_floor_color, texture=None)
    create_wall(position=(room203_center.x - room203_size.x / 2, room203_center.y + 2, room203_center.z), scale=(0.2, room203_size.y, room203_size.z), color=dark_wall_color, texture=None)
    create_wall(position=(room203_center.x + room203_size.x / 2, room203_center.y + 2, room203_center.z), scale=(0.2, room203_size.y, room203_size.z), color=dark_wall_color, texture=None)
    create_wall(position=(room203_center.x, room203_center.y + 2, room203_center.z + room203_size.z / 2), scale=(room203_size.x, room203_size.y, 0.2), color=dark_wall_color, texture=None)
    create_wall(position=(room203_center.x, room203_center.y + 2, room203_center.z - room203_size.z / 2), scale=(room203_size.x, room203_size.y, 0.2), color=dark_wall_color, texture=None)
    create_wall(position=(room203_center.x, room203_center.y + room203_size.y, room203_center.z), scale=(room203_size.x, 0.2, room203_size.z), color=dark_ceiling_color, texture=None)

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
        door_color=color.rgb(110, 110, 140)
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
        door_color=color.rgb(100, 120, 150)
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
    
    # Master Bedroom (at z=-20, connected to corridor end)
    br_color = color.rgb(182, 180, 220)
    br_ceiling_color = color.rgb(218, 216, 240)
    create_floor(position=(0, 4, -20), scale=(10, 1, 10))
    create_wall(position=(0, 8, -20), scale=(10, 0.2, 10), color=br_ceiling_color) # Ceiling
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
    bedroom_door = Door(
        position=(-1.5, 5.85, -15),
        rotation=(0, 0, 0),
        width=3.4,
        height=3.8,
        door_color=color.rgb(150, 145, 200)
    )
    add_door_label(bedroom_door, '201')
    
    # Light for Bedroom
    br_light = PointLight(parent=scene, position=(0, 7, -20), color=color.cyan)
    LightSwitch(position=(1, 5.5, -15.2), rotation=(0, 180, 0), light_source=br_light)

    # Ambient light for base visibility
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
