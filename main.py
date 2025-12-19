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

class WallLight(Entity):
    def __init__(self, position, rotation=(0,0,0), light_color=color.rgb(255, 220, 150), flicker=False, interval_range=(0.08, 0.25), intensity_range=(0.35, 1.0), **kwargs):
        super().__init__(
            model='cube',
            scale=(0.5, 0.8, 0.1), # Tall rectangular light like in image
            position=position,
            rotation=rotation,
            color=color.dark_gray,
            **kwargs
        )
        self.emissive = Entity(
            parent=self,
            model='quad',
            scale=(0.8, 0.9),
            z=-0.51,
            color=light_color,
            unlit=True
        )
        self.light = PointLight(
            parent=self,
            position=(0, 0, -2),
            color=light_color,
            shadows=True
        )
        self.light.attenuation = (0.5, 0, 0.05)
        self.flicker_controller = None

        if flicker:
            # Register a flicker controller so the hallway lighting stays unsettled
            controller = FlickeringLight(self.light, interval_range=interval_range, intensity_range=intensity_range)
            flickering_lights.append(controller)
            self.flicker_controller = controller

class Door(Entity):
    def __init__(self, position, rotation=(0,0,0), width=3.2, height=3.5, thickness=0.12, door_color=color.white, texture='assets/wood1.jpg', **kwargs):
        super().__init__(
            model='cube',
            color=door_color,
            texture=texture,
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

def create_wall(position, scale, color=color.white, texture='assets/wall.jpg', texture_scale=None):
    e = Entity(
        model='cube', 
        position=position, 
        scale=scale, 
        color=color, 
        texture=texture, 
        collider='box'
    )
    if texture_scale:
        e.texture_scale = texture_scale
    else:
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
        speed=6,
        mouse_sensitivity=Vec2(40, 40),
        position=(0, 1, -40)
    )

    # -------------------
    # CONSTANTS
    # -------------------
    CORRIDOR_WIDTH = 10
    CORRIDOR_HEIGHT = 6
    ROOM_HEIGHT = 6
    DOOR_WIDTH = 2.0
    DOOR_HEIGHT = 3.5
    
    theme_wall = color.rgb(212, 195, 178)
    theme_ceiling = color.rgb(245, 237, 224)
    theme_door = color.white
    
    # -------------------
    # HELPERS
    # -------------------
    def make_room(pos, size, door_dir, light_color=color.rgb(80, 70, 10), flicker=False, decorator=None):
        # pos: (x, z) center of room
        # size: (width, depth)
        # door_dir: 'north', 'south', 'east', 'west' (direction pointing INTO the room from corridor)
        w, d = size
        x, z = pos

        # Floor and ceiling
        create_floor(position=(x, 0, z), scale=(w, 1, d))
        create_wall(position=(x, ROOM_HEIGHT, z), scale=(w, 0.2, d), color=theme_ceiling, texture='assets/rustytiles01_spec.png', texture_scale=(max(1, w/3), max(1, d/3)))

        t = 0.2
        half_w = w / 2
        half_d = d / 2

        light_switch_position = None
        light_switch_rotation = (0, 0, 0)

        if door_dir == 'west':
            create_wall(position=(x - half_w, ROOM_HEIGHT/2, z), scale=(t, ROOM_HEIGHT, d), color=theme_wall)  # Back
            create_wall(position=(x, ROOM_HEIGHT/2, z + half_d), scale=(w, ROOM_HEIGHT, t), color=theme_wall)  # Top
            create_wall(position=(x, ROOM_HEIGHT/2, z - half_d), scale=(w, ROOM_HEIGHT, t), color=theme_wall)  # Bottom
            light_switch_position = (x + half_w + 0.2, 1.5, z + 2)
            light_switch_rotation = (0, -90, 0)

        elif door_dir == 'east':
            create_wall(position=(x + half_w, ROOM_HEIGHT/2, z), scale=(t, ROOM_HEIGHT, d), color=theme_wall)  # Front
            create_wall(position=(x, ROOM_HEIGHT/2, z + half_d), scale=(w, ROOM_HEIGHT, t), color=theme_wall)  # Top
            create_wall(position=(x, ROOM_HEIGHT/2, z - half_d), scale=(w, ROOM_HEIGHT, t), color=theme_wall)  # Bottom
            light_switch_position = (x - half_w - 0.2, 1.5, z + 2)
            light_switch_rotation = (0, 90, 0)

        elif door_dir == 'north':
            create_wall(position=(x, ROOM_HEIGHT/2, z + half_d), scale=(w, ROOM_HEIGHT, t), color=theme_wall)  # Top
            create_wall(position=(x - half_w, ROOM_HEIGHT/2, z), scale=(t, ROOM_HEIGHT, d), color=theme_wall)  # Left
            create_wall(position=(x + half_w, ROOM_HEIGHT/2, z), scale=(t, ROOM_HEIGHT, d), color=theme_wall)  # Right
            light_switch_position = (x + 2, 1.5, z - half_d - 0.2)
            light_switch_rotation = (0, 0, 0)

        elif door_dir == 'south':
            create_wall(position=(x, ROOM_HEIGHT/2, z - half_d), scale=(w, ROOM_HEIGHT, t), color=theme_wall)  # Bottom
            create_wall(position=(x - half_w, ROOM_HEIGHT/2, z), scale=(t, ROOM_HEIGHT, d), color=theme_wall)  # Left
            create_wall(position=(x + half_w, ROOM_HEIGHT/2, z), scale=(t, ROOM_HEIGHT, d), color=theme_wall)  # Right
            light_switch_position = (x - 2, 1.5, z + half_d + 0.2)
            light_switch_rotation = (0, 180, 0)

        else:
            raise ValueError(f'Unsupported door_dir {door_dir}')

        def add_bathroom():
            bath_w = min(max(2.4, w * 0.45), max(2.4, w - 1.2))
            bath_d = min(max(2.4, d * 0.45), max(2.4, d - 1.2))
            if bath_w <= 1.5 or bath_d <= 1.5:
                return

            wall_thickness = 0.18
            inset = 0.4
            bath_height = ROOM_HEIGHT - 0.4
            wall_center_y = bath_height / 2
            bath_wall_color = color.rgb(228, 230, 236)

            if door_dir == 'west':
                bath_cx = x - half_w + bath_w / 2 + inset
                bath_cz = z + half_d - bath_d / 2 - inset
                door_axis = 'south'
            elif door_dir == 'east':
                bath_cx = x + half_w - bath_w / 2 - inset
                bath_cz = z + half_d - bath_d / 2 - inset
                door_axis = 'south'
            elif door_dir == 'north':
                bath_cx = x + half_w - bath_w / 2 - inset
                bath_cz = z + half_d - bath_d / 2 - inset
                door_axis = 'west'
            elif door_dir == 'south':
                bath_cx = x + half_w - bath_w / 2 - inset
                bath_cz = z - half_d + bath_d / 2 + inset
                door_axis = 'north'
            else:
                return

            door_span = bath_w if door_axis in ('north', 'south') else bath_d
            door_width = max(0.8, min(1.2, door_span - 0.6))
            if door_width >= door_span:
                door_width = max(0.6, door_span - 0.4)

            create_floor(position=(bath_cx, 0.02, bath_cz), scale=(bath_w, 1, bath_d))
            create_wall(position=(bath_cx, ROOM_HEIGHT - 0.1, bath_cz), scale=(bath_w, 0.12, bath_d), color=theme_ceiling, texture='assets/wood.jpg', texture_scale=(max(1, bath_w / 2), max(1, bath_d / 2)))

            def wall(position, scale):
                create_wall(position=position, scale=scale, color=bath_wall_color, texture='assets/wall.png')

            def full_wall(axis):
                if axis == 'north':
                    wall(position=(bath_cx, wall_center_y, bath_cz + bath_d / 2), scale=(bath_w, bath_height, wall_thickness))
                elif axis == 'south':
                    wall(position=(bath_cx, wall_center_y, bath_cz - bath_d / 2), scale=(bath_w, bath_height, wall_thickness))
                elif axis == 'east':
                    wall(position=(bath_cx + bath_w / 2, wall_center_y, bath_cz), scale=(wall_thickness, bath_height, bath_d))
                else:
                    wall(position=(bath_cx - bath_w / 2, wall_center_y, bath_cz), scale=(wall_thickness, bath_height, bath_d))

            for axis in ('north', 'south', 'east', 'west'):
                if axis != door_axis:
                    full_wall(axis)

            side_total = bath_w - door_width if door_axis in ('north', 'south') else bath_d - door_width
            if door_axis in ('south', 'north') and side_total > 0.2:
                left = max(0.2, side_total / 2)
                right = max(0.2, side_total - left)
                if door_axis == 'south':
                    wall(position=(bath_cx - (door_width / 2 + left / 2), wall_center_y, bath_cz - bath_d / 2), scale=(left, bath_height, wall_thickness))
                    wall(position=(bath_cx + (door_width / 2 + right / 2), wall_center_y, bath_cz - bath_d / 2), scale=(right, bath_height, wall_thickness))
                else:
                    wall(position=(bath_cx - (door_width / 2 + left / 2), wall_center_y, bath_cz + bath_d / 2), scale=(left, bath_height, wall_thickness))
                    wall(position=(bath_cx + (door_width / 2 + right / 2), wall_center_y, bath_cz + bath_d / 2), scale=(right, bath_height, wall_thickness))
            elif door_axis in ('east', 'west') and side_total > 0.2:
                near = max(0.2, side_total / 2)
                far_segment = max(0.2, side_total - near)
                if door_axis == 'east':
                    wall(position=(bath_cx + bath_w / 2, wall_center_y, bath_cz - (door_width / 2 + near / 2)), scale=(wall_thickness, bath_height, near))
                    wall(position=(bath_cx + bath_w / 2, wall_center_y, bath_cz + (door_width / 2 + far_segment / 2)), scale=(wall_thickness, bath_height, far_segment))
                else:
                    wall(position=(bath_cx - bath_w / 2, wall_center_y, bath_cz - (door_width / 2 + near / 2)), scale=(wall_thickness, bath_height, near))
                    wall(position=(bath_cx - bath_w / 2, wall_center_y, bath_cz + (door_width / 2 + far_segment / 2)), scale=(wall_thickness, bath_height, far_segment))

            # Door frame visuals
            frame_color = color.rgb(120, 100, 80)
            frame_height = 3.0
            frame_thickness = 0.12
            frame_depth = 0.18
            if door_axis == 'south':
                door_z = bath_cz - bath_d / 2
                Entity(model='cube', color=frame_color, position=(bath_cx - door_width / 2 + frame_thickness / 2, frame_height / 2, door_z - frame_depth / 2), scale=(frame_thickness, frame_height, frame_depth))
                Entity(model='cube', color=frame_color, position=(bath_cx + door_width / 2 - frame_thickness / 2, frame_height / 2, door_z - frame_depth / 2), scale=(frame_thickness, frame_height, frame_depth))
                Entity(model='cube', color=frame_color, position=(bath_cx, frame_height - 1.2, door_z - frame_depth / 2), scale=(door_width, frame_thickness, frame_depth))
                switch_pos = (bath_cx + door_width / 2 + 0.25, 1.3, door_z + 0.3)
                switch_rot = (0, -90, 0)
            elif door_axis == 'north':
                door_z = bath_cz + bath_d / 2
                Entity(model='cube', color=frame_color, position=(bath_cx - door_width / 2 + frame_thickness / 2, frame_height / 2, door_z + frame_depth / 2), scale=(frame_thickness, frame_height, frame_depth))
                Entity(model='cube', color=frame_color, position=(bath_cx + door_width / 2 - frame_thickness / 2, frame_height / 2, door_z + frame_depth / 2), scale=(frame_thickness, frame_height, frame_depth))
                Entity(model='cube', color=frame_color, position=(bath_cx, frame_height - 1.2, door_z + frame_depth / 2), scale=(door_width, frame_thickness, frame_depth))
                switch_pos = (bath_cx + door_width / 2 + 0.25, 1.3, door_z - 0.3)
                switch_rot = (0, -90, 0)
            elif door_axis == 'east':
                door_x = bath_cx + bath_w / 2
                Entity(model='cube', color=frame_color, position=(door_x + frame_depth / 2, frame_height / 2, bath_cz - door_width / 2 + frame_thickness / 2), scale=(frame_depth, frame_height, frame_thickness))
                Entity(model='cube', color=frame_color, position=(door_x + frame_depth / 2, frame_height / 2, bath_cz + door_width / 2 - frame_thickness / 2), scale=(frame_depth, frame_height, frame_thickness))
                Entity(model='cube', color=frame_color, position=(door_x + frame_depth / 2, frame_height - 1.2, bath_cz, ), scale=(frame_depth, frame_thickness, door_width))
                switch_pos = (door_x - 0.3, 1.3, bath_cz + door_width / 2 + 0.25)
                switch_rot = (0, 0, 0)
            else:
                door_x = bath_cx - bath_w / 2
                Entity(model='cube', color=frame_color, position=(door_x - frame_depth / 2, frame_height / 2, bath_cz - door_width / 2 + frame_thickness / 2), scale=(frame_depth, frame_height, frame_thickness))
                Entity(model='cube', color=frame_color, position=(door_x - frame_depth / 2, frame_height / 2, bath_cz + door_width / 2 - frame_thickness / 2), scale=(frame_depth, frame_height, frame_thickness))
                Entity(model='cube', color=frame_color, position=(door_x - frame_depth / 2, frame_height - 1.2, bath_cz), scale=(frame_depth, frame_thickness, door_width))
                switch_pos = (door_x + 0.3, 1.3, bath_cz + door_width / 2 + 0.25)
                switch_rot = (0, 180, 0)

            bath_light = PointLight(parent=scene, position=(bath_cx, ROOM_HEIGHT - 1.2, bath_cz), color=color.rgb(190, 205, 220))
            LightSwitch(position=switch_pos, rotation=switch_rot, light_source=bath_light)

            # Simple fixtures for mood
            Entity(model='cube', color=color.rgb(235, 235, 240), position=(bath_cx - bath_w / 2 + 0.6, 0.45, bath_cz + bath_d / 2 - 0.5), scale=(0.9, 0.9, 0.5))
            Entity(model='sphere', color=color.rgb(255, 255, 255), position=(bath_cx - bath_w / 2 + 0.6, 1.0, bath_cz + bath_d / 2 - 0.4), scale=0.35, unlit=True)
            Entity(model='cube', color=color.rgb(200, 200, 205), position=(bath_cx + bath_w / 2 - 0.6, 0.35, bath_cz + bath_d / 2 - 0.6), scale=(0.7, 0.6, 0.7))

        add_bathroom()

        room_light = PointLight(parent=scene, position=(x, ROOM_HEIGHT - 1, z), color=light_color)

        if flicker:
            flickering_lights.append(FlickeringLight(room_light, interval_range=(0.05, 0.3), intensity_range=(0.15, 1.0)))

        if light_switch_position:
            LightSwitch(position=light_switch_position, rotation=light_switch_rotation, light_source=room_light)

        if decorator:
            decorator(center=(x, z), size=(w, d))

    painting_textures = [
        'assets/wood.jpg',
    ]
    painting_index = 0

    def place_painting(position, rotation=(0, 0, 0), scale=(3, 2.4)):
        nonlocal painting_index
        if not painting_textures:
            return
        texture_path = painting_textures[painting_index % len(painting_textures)]
        painting_index += 1
        painting = Entity(
            model='quad',
            texture=texture_path,
            position=position,
            rotation=rotation,
            scale=scale,
            unlit=True,
            double_sided=False
        )
        # Pull the painting slightly off the wall so the texture is visible head-on.
        painting.position += painting.forward * 0.03

    def add_occult_circle(center, size):
        cx, cz = center
        Entity(
            model='quad',
            color=color.rgb(120, 0, 0),
            position=(cx, 0.04, cz),
            rotation_x=90,
            scale=(size[0] * 0.7, size[1] * 0.7),
            unlit=True
        )
        Entity(
            model='quad',
            color=color.rgb(200, 40, 40),
            position=(cx, 2.4, cz + size[1] * 0.18),
            scale=(2.4, 1.2),
            unlit=True
        )
        Entity(
            model='cube',
            color=color.rgb(30, 30, 30),
            position=(cx, 0.6, cz - size[1] * 0.25),
            scale=(size[0] * 0.5, 1.1, 0.6)
        )
        for offset in (-1.2, 0, 1.2):
            Entity(
                model='cube',
                color=color.rgb(200, 160, 90),
                position=(cx + offset, 0.6, cz + size[1] * 0.18),
                scale=(0.14, 0.6, 0.14)
            )
            Entity(
                model='sphere',
                color=color.rgb(255, 210, 120),
                position=(cx + offset, 1.0, cz + size[1] * 0.18),
                scale=0.2,
                unlit=True
            )

    def add_storage_abattoir(center, size):
        cx, cz = center
        Entity(
            model='quad',
            color=color.rgb(140, 0, 0),
            position=(cx - size[0] * 0.2, 0.04, cz + size[1] * 0.15),
            rotation_x=90,
            scale=(size[0] * 0.5, size[1] * 0.4),
            unlit=True
        )
        Entity(
            model='cube',
            color=color.rgb(45, 45, 45),
            position=(cx + size[0] * 0.25, 1.2, cz - size[1] * 0.1),
            scale=(size[0] * 0.4, 2.5, size[1] * 0.2)
        )
        for n in range(3):
            Entity(
                model='cube',
                color=color.rgb(25, 20, 20),
                position=(cx - size[0] * 0.25 + n * 1.2, 2.0, cz - size[1] * 0.2),
                scale=(0.4, 1.6, 0.4)
            )
        Entity(
            model='quad',
            color=color.rgb(255, 120, 120),
            position=(cx, 3.5, cz + size[1] * 0.4),
            rotation=(90, 0, 0),
            scale=(size[0] * 0.6, size[1] * 0.2),
            unlit=True
        )

    # -------------------
    # LAYOUT GENERATION
    # -------------------
    
    # --- SEGMENT A (Entrance) ---
    # From Z=-50 to Z=0
    # Floor & Ceiling
    create_floor(position=(0, 0, -25), scale=(CORRIDOR_WIDTH, 1, 50))
    create_wall(position=(0, CORRIDOR_HEIGHT, -25), scale=(CORRIDOR_WIDTH, 0.2, 50), color=theme_ceiling, texture='assets/rustytiles01_spec.png', texture_scale=(3, 15))
    
    # Entrance Wall
    create_wall(position=(0, CORRIDOR_HEIGHT/2, -50), scale=(CORRIDOR_WIDTH, CORRIDOR_HEIGHT, 0.2), color=theme_wall)

    # Left Wall (X=-5)
    # Room 1 (Small) at Z=-40
    create_wall(position=(-5, CORRIDOR_HEIGHT/2, -45.5), scale=(0.2, CORRIDOR_HEIGHT, 9), color=theme_wall)
    create_wall(position=(-5, CORRIDOR_HEIGHT - 1.2, -40), scale=(0.2, 2.4, DOOR_WIDTH), color=theme_wall) # Header
    Door(position=(-5, DOOR_HEIGHT/2, -40 + DOOR_WIDTH/2), rotation=(0, -90, 0), width=DOOR_WIDTH, height=DOOR_HEIGHT, door_color=theme_door)
    create_wall(position=(-5, CORRIDOR_HEIGHT/2, -17), scale=(0.2, CORRIDOR_HEIGHT, 44), color=theme_wall)
    
    make_room((-9, -40), (8, 8), 'west')

    # Right Wall (X=5)
    # Room 2 (Big) at Z=-15
    create_wall(position=(5, CORRIDOR_HEIGHT/2, -33), scale=(0.2, CORRIDOR_HEIGHT, 34), color=theme_wall)
    create_wall(position=(5, CORRIDOR_HEIGHT - 1.2, -15), scale=(0.2, 2.4, DOOR_WIDTH), color=theme_wall) # Header
    Door(position=(5, DOOR_HEIGHT/2, -15 - DOOR_WIDTH/2), rotation=(0, 90, 0), width=DOOR_WIDTH, height=DOOR_HEIGHT, door_color=theme_door)
    create_wall(position=(5, CORRIDOR_HEIGHT/2, -9.5), scale=(0.2, CORRIDOR_HEIGHT, 9), color=theme_wall)
    
    make_room((12, -15), (14, 14), 'east')

    # Lights Segment A
    for z in range(-40, -5, 15):
        WallLight(position=(-4.8, 4, z), rotation=(0, 90, 0), flicker=(z % 30 == 0))
        WallLight(position=(4.8, 4, z), rotation=(0, -90, 0), flicker=(z % 20 == 0), intensity_range=(0.1, 0.85))

    place_painting(position=(-4.6, 3.2, -32), rotation=(0, 90, 0))
    place_painting(position=(4.6, 3.2, -18), rotation=(0, -90, 0))

    # --- INTERSECTION 1 (A -> B) ---
    # Fill missing corner (-5 to 0, 0 to 5)
    create_floor(position=(-2.5, 0, 2.5), scale=(5, 1, 5))
    create_wall(position=(-2.5, CORRIDOR_HEIGHT, 2.5), scale=(5, 0.2, 5), color=theme_ceiling, texture='assets/wood.jpg', texture_scale=(1.5, 1.5))
    create_wall(position=(-5, CORRIDOR_HEIGHT/2, 2.5), scale=(0.2, CORRIDOR_HEIGHT, 5), color=theme_wall)
    create_wall(position=(-2.5, CORRIDOR_HEIGHT/2, 5), scale=(5, CORRIDOR_HEIGHT, 0.2), color=theme_wall)

    # --- SEGMENT B (The Turn) ---
    # From X=0 to X=30 (at Z=0)
    # Floor & Ceiling
    create_floor(position=(15, 0, 0), scale=(30, 1, CORRIDOR_WIDTH))
    create_wall(position=(15, CORRIDOR_HEIGHT, 0), scale=(30, 0.2, CORRIDOR_WIDTH), color=theme_ceiling, texture='assets/wood.jpg', texture_scale=(10, 3))
    
    # Top Wall (Z=5)
    # Room 3 (Small) at X=15
    create_wall(position=(4.5, CORRIDOR_HEIGHT/2, 5), scale=(19, CORRIDOR_HEIGHT, 0.2), color=theme_wall)
    create_wall(position=(15, CORRIDOR_HEIGHT - 1.2, 5), scale=(DOOR_WIDTH, 2.4, 0.2), color=theme_wall) # Header
    Door(position=(15 - DOOR_WIDTH/2, DOOR_HEIGHT/2, 5), rotation=(0, 0, 0), width=DOOR_WIDTH, height=DOOR_HEIGHT, door_color=theme_door)
    create_wall(position=(20.5, CORRIDOR_HEIGHT/2, 5), scale=(9, CORRIDOR_HEIGHT, 0.2), color=theme_wall)
    
    make_room((15, 10), (10, 10), 'north')
    
    # Bottom Wall (Z=-5)
    create_wall(position=(20, CORRIDOR_HEIGHT/2, -5), scale=(30, CORRIDOR_HEIGHT, 0.2), color=theme_wall)

    # Lights Segment B
    for x in range(5, 30, 15):
        WallLight(position=(x, 4, 4.8), rotation=(0, 180, 0), flicker=(x == 20), intensity_range=(1.8, 5))
        WallLight(position=(x, 4, -4.8), rotation=(0, 0, 0), flicker=(x == 5))

    # --- INTERSECTION 2 (B -> C) ---
    # Fill missing corner (30 to 35, -5 to 0)
    create_floor(position=(32.5, 0, -2.5), scale=(5, 1, 5))
    create_wall(position=(32.5, CORRIDOR_HEIGHT, -2.5), scale=(5, 0.2, 5), color=theme_ceiling, texture='assets/wood.jpg', texture_scale=(1.5, 1.5))
    create_wall(position=(35, CORRIDOR_HEIGHT/2, -2.5), scale=(0.2, CORRIDOR_HEIGHT, 5), color=theme_wall)
    create_wall(position=(32.5, CORRIDOR_HEIGHT/2, -5), scale=(5, CORRIDOR_HEIGHT, 0.2), color=theme_wall)

    # --- SEGMENT C (To Stairs) ---
    # From Z=0 to Z=40 (at X=30)
    # Floor & Ceiling
    create_floor(position=(30, 0, 20), scale=(CORRIDOR_WIDTH, 1, 40))
    create_wall(position=(30, CORRIDOR_HEIGHT, 20), scale=(CORRIDOR_WIDTH, 0.2, 40), color=theme_ceiling, texture='assets/wood.jpg', texture_scale=(3, 12))
    
    # Left Wall (X=25)
    create_wall(position=(25, CORRIDOR_HEIGHT/2, 22.5), scale=(0.2, CORRIDOR_HEIGHT, 35), color=theme_wall)
    
    # Right Wall (X=35)
    # Room 4 (Big) at Z=25
    create_wall(position=(35, CORRIDOR_HEIGHT/2, 9.5), scale=(0.2, CORRIDOR_HEIGHT, 29), color=theme_wall)
    create_wall(position=(35, CORRIDOR_HEIGHT - 1.2, 25), scale=(0.2, 2.4, DOOR_WIDTH), color=theme_wall) # Header
    Door(position=(35, DOOR_HEIGHT/2, 25 - DOOR_WIDTH/2), rotation=(0, 90, 0), width=DOOR_WIDTH, height=DOOR_HEIGHT, door_color=theme_door)
    create_wall(position=(35, CORRIDOR_HEIGHT/2, 33), scale=(0.2, CORRIDOR_HEIGHT, 14), color=theme_wall)
    
    make_room((42, 25), (12, 12), 'east')

    # Lights Segment C
    for z in range(10, 35, 15):
        WallLight(position=(25.2, 4, z), rotation=(0, 90, 0), flicker=(z == 25), intensity_range=(0.08, 0.9))
        WallLight(position=(34.8, 4, z), rotation=(0, -90, 0), flicker=(z != 10))

    place_painting(position=(12, 3, 4.6), rotation=(0, 180, 0))
    place_painting(position=(24, 3, -4.6), rotation=(0, 0, 0))

    place_painting(position=(25.4, 3.1, 18), rotation=(0, 90, 0))
    place_painting(position=(34.6, 3.1, 30), rotation=(0, -90, 0))

    # -------------------
    # STAIRCASE
    # -------------------
    stair_z_start = 40
    stair_x = 30
    
    # Floor for stair area
    create_floor(position=(stair_x, 0, stair_z_start + 10), scale=(CORRIDOR_WIDTH, 1, 20))
    create_wall(position=(stair_x, CORRIDOR_HEIGHT + 4, stair_z_start + 10), scale=(CORRIDOR_WIDTH, 0.2, 20), color=theme_ceiling, texture='assets/wood.jpg', texture_scale=(3, 6))
    
    # Walls around stairwell
    create_wall(position=(stair_x - 5, CORRIDOR_HEIGHT/2 + 2, stair_z_start + 10), scale=(0.2, CORRIDOR_HEIGHT+4, 20), color=theme_wall)
    create_wall(position=(stair_x + 5, CORRIDOR_HEIGHT/2 + 2, stair_z_start + 10), scale=(0.2, CORRIDOR_HEIGHT+4, 20), color=theme_wall)
    create_wall(position=(stair_x, CORRIDOR_HEIGHT/2 + 2, stair_z_start + 20), scale=(CORRIDOR_WIDTH, CORRIDOR_HEIGHT+4, 0.2), color=theme_wall)

    # Steps
    for i in range(20):
        Entity(
            model='cube',
            color=color.rgb(100, 100, 100),
            texture='assets/wood1.jpg',
            position=(stair_x, i*0.3, stair_z_start + i*0.5),
            scale=(6, 0.3, 0.5),
            collider='box'
        )
    
    # Landing at top
    landing_z = stair_z_start + 10
    landing_height = 6
    create_floor(position=(stair_x, landing_height, landing_z + 5), scale=(CORRIDOR_WIDTH, 1, 10))

    # Upper level corridor extension
    upper_length = 40
    upper_start = landing_z + 5
    upper_end = upper_start + upper_length
    upper_center = upper_start + upper_length / 2
    upper_wall_y = landing_height + CORRIDOR_HEIGHT / 2

    create_floor(position=(stair_x, landing_height, upper_center), scale=(CORRIDOR_WIDTH, 1, upper_length))
    create_wall(
        position=(stair_x, landing_height + CORRIDOR_HEIGHT, upper_center),
        scale=(CORRIDOR_WIDTH, 0.2, upper_length),
        color=theme_ceiling,
        texture='assets/wood.jpg',
        texture_scale=(3, max(3, upper_length / 6))
    )

    left_wall_start = upper_start + 6
    left_door_flush = upper_start + 12
    right_wall_start = upper_start + 6
    right_door_flush = upper_start + 22

    # Left wall segments (west side)
    create_wall(
        position=(stair_x - CORRIDOR_WIDTH / 2, upper_wall_y, (left_wall_start + left_door_flush) / 2),
        scale=(0.2, CORRIDOR_HEIGHT, max(0.2, left_door_flush - left_wall_start)),
        color=theme_wall
    )
    create_wall(
        position=(stair_x - CORRIDOR_WIDTH / 2, upper_wall_y, (left_door_flush + DOOR_WIDTH + upper_end) / 2),
        scale=(0.2, CORRIDOR_HEIGHT, max(0.2, upper_end - (left_door_flush + DOOR_WIDTH))),
        color=theme_wall
    )

    # Right wall segments (east side)
    create_wall(
        position=(stair_x + CORRIDOR_WIDTH / 2, upper_wall_y, (right_wall_start + right_door_flush) / 2),
        scale=(0.2, CORRIDOR_HEIGHT, max(0.2, right_door_flush - right_wall_start)),
        color=theme_wall
    )
    create_wall(
        position=(stair_x + CORRIDOR_WIDTH / 2, upper_wall_y, (right_door_flush + DOOR_WIDTH + upper_end) / 2),
        scale=(0.2, CORRIDOR_HEIGHT, max(0.2, upper_end - (right_door_flush + DOOR_WIDTH))),
        color=theme_wall
    )

    # Corridor end cap
    create_wall(
        position=(stair_x, upper_wall_y, upper_end),
        scale=(CORRIDOR_WIDTH, CORRIDOR_HEIGHT, 0.2),
        color=theme_wall
    )

    # Doors to upper rooms
    Door(position=(stair_x - CORRIDOR_WIDTH / 2, DOOR_HEIGHT/2 + landing_height, left_door_flush + DOOR_WIDTH/2), rotation=(0, -90, 0), width=DOOR_WIDTH, height=DOOR_HEIGHT, door_color=theme_door)
    Door(position=(stair_x + CORRIDOR_WIDTH / 2, DOOR_HEIGHT/2 + landing_height, right_door_flush + DOOR_WIDTH/2), rotation=(0, 90, 0), width=DOOR_WIDTH, height=DOOR_HEIGHT, door_color=theme_door)

    # Upper rooms
    left_room_center = (stair_x - CORRIDOR_WIDTH / 2 - 6, left_door_flush + DOOR_WIDTH)
    right_room_center = (stair_x + CORRIDOR_WIDTH / 2 + 6, right_door_flush + DOOR_WIDTH)
    make_room(left_room_center, (12, 14), 'west', light_color=color.rgb(140, 50, 20), flicker=True, decorator=add_occult_circle)
    make_room(right_room_center, (10, 12), 'east', light_color=color.rgb(90, 20, 20), flicker=True, decorator=add_storage_abattoir)

    # Upper hallway lighting and props
    for z in range(int(upper_start + 8), int(upper_end), 12):
        WallLight(position=(stair_x - CORRIDOR_WIDTH / 2 + 0.2, landing_height + 4, z), rotation=(0, 90, 0), flicker=True, intensity_range=(0.1, 0.9))
        WallLight(position=(stair_x + CORRIDOR_WIDTH / 2 - 0.2, landing_height + 4, z), rotation=(0, -90, 0), flicker=(z % 24 == 0), intensity_range=(0.05, 0.8))

    place_painting(position=(stair_x - CORRIDOR_WIDTH / 2 + 0.3, landing_height + 2.8, upper_start + 14), rotation=(0, 90, 0), scale=(2.6, 2.2))
    place_painting(position=(stair_x + CORRIDOR_WIDTH / 2 - 0.3, landing_height + 2.8, upper_start + 26), rotation=(0, -90, 0), scale=(2.6, 2.2))

    dread_light = PointLight(parent=scene, position=(stair_x, landing_height + 3.5, upper_end - 3), color=color.rgb(180, 20, 20), shadows=True)
    flickering_lights.append(FlickeringLight(dread_light, interval_range=(0.02, 0.15), intensity_range=(0.03, 0.7)))

    Entity(
        model='quad',
        color=color.rgb(150, 0, 0),
        position=(stair_x, landing_height + 0.05, upper_end - 3),
        rotation_x=90,
        scale=(4, 2),
        unlit=True
    )

    Entity(
        model='quad',
        color=color.rgb(20, 20, 20),
        position=(stair_x, landing_height + 2.4, upper_end - 2),
        scale=(1.6, 3.6),
        billboard=True
    )

    # Ambient light
    AmbientLight(color=color.rgba(6, 6, 6, 255))

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
