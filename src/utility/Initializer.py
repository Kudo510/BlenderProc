import os
import random
from numpy import random as np_random
from sys import platform
import multiprocessing

import bpy
from src.utility.CameraUtility import CameraUtility
from src.utility.DefaultConfig import DefaultConfig

import addon_utils

class Initializer:

    @staticmethod
    def init(horizon_color: list = [0.05, 0.05, 0.05], clean_up_scene: bool = True):
        """ Initializes basic blender settings, the world and the camera.

        Also cleans up the whole scene at first.

        :param horizon_color: The color to use for the world background.
        :param clean_up_scene: Set to False, if you want to keep all scene data.
        """
        if clean_up_scene:
            Initializer.cleanup()

        # Set language if necessary
        if bpy.context.preferences.view.language != "en_US":
            print("Setting blender language settings to english during this run")
            bpy.context.preferences.view.language = "en_US"

        prefs = bpy.context.preferences.addons['cycles'].preferences
        # Use cycles
        bpy.context.scene.render.engine = 'CYCLES'

        if platform == "darwin":
            # there is no gpu support in mac os so use the cpu with maximum power
            bpy.context.scene.cycles.device = "CPU"
            bpy.context.scene.render.threads = multiprocessing.cpu_count()
        else:
            bpy.context.scene.cycles.device = "GPU"
            preferences = bpy.context.preferences.addons['cycles'].preferences
            for device_type in preferences.get_device_types(bpy.context):
                preferences.get_devices_for_type(device_type[0])
            for gpu_type in ["OPTIX", "CUDA"]:
                found = False
                for device in preferences.devices:
                    if device.type == gpu_type:
                        bpy.context.preferences.addons['cycles'].preferences.compute_device_type = gpu_type
                        print('Device {} of type {} found and used.'.format(device.name, device.type))
                        found = True
                        break
                if found:
                    break
            # make sure that all visible GPUs are used
            for group in prefs.get_devices():
                for d in group:
                    d.use = True

        # setting the frame end, will be changed by the camera loader modules
        bpy.context.scene.frame_end = 0

        # Sets background color
        world = bpy.data.worlds['World']
        world.use_nodes = True
        world.node_tree.nodes["Background"].inputs[0].default_value[:3] = horizon_color

        # Create the camera
        cam = bpy.data.cameras.new("Camera")
        cam_ob = bpy.data.objects.new("Camera", cam)
        bpy.context.scene.collection.objects.link(cam_ob)
        bpy.context.scene.camera = cam_ob

        # Set default intrinsics
        CameraUtility.set_intrinsics_from_blender_params(DefaultConfig.fov, DefaultConfig.resolution_x, DefaultConfig.resolution_y, DefaultConfig.clip_start, DefaultConfig.clip_end, DefaultConfig.pixel_aspect_x, DefaultConfig.pixel_aspect_y, DefaultConfig.shift_x, DefaultConfig.shift_y, "FOV")
        CameraUtility.set_stereo_parameters(DefaultConfig.stereo_convergence_mode, DefaultConfig.stereo_convergence_distance, DefaultConfig.stereo_interocular_distance)

        random_seed = os.getenv("BLENDER_PROC_RANDOM_SEED")
        if random_seed:
            print("Got random seed: {}".format(random_seed))
            try:
                random_seed = int(random_seed)
            except ValueError as e:
                raise e
            random.seed(random_seed)
            np_random.seed(random_seed)

        addon_utils.enable("render_auto_tile_size")

    @staticmethod
    def cleanup():
        """ Resets the scene to its clean state, but keeping the UI as it is """
        # Switch to right context
        if bpy.context.object is not None and bpy.context.object.mode != "OBJECT":
            bpy.ops.object.mode_set(mode='OBJECT')

        # Clean up
        Initializer._remove_all_data()
        Initializer._remove_custom_properties()

        # Create new world
        new_world = bpy.data.worlds.new("World")
        bpy.context.scene.world = new_world

    @staticmethod
    def _remove_all_data():
        """ Remove all data blocks except opened scripts and the default scene. """
        # Go through all attributes of bpy.data
        for collection in dir(bpy.data):
            data_structure = getattr(bpy.data, collection)
            # Check that it is a data collection
            if isinstance(data_structure, bpy.types.bpy_prop_collection) and hasattr(data_structure, "remove") and collection not in ["texts"]:
                # Go over all entities in that collection
                for block in data_structure:
                    # Remove everything besides the default scene
                    if not isinstance(block, bpy.types.Scene) or block.name != "Scene":
                        data_structure.remove(block)

    @staticmethod
    def _remove_custom_properties():
        """ Remove all custom properties registered at global entities like the scene. """
        for key in bpy.context.scene.keys():
            del bpy.context.scene[key]