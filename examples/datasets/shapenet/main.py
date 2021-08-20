from src.utility.SetupUtility import SetupUtility
SetupUtility.setup([])

from src.utility.Utility import Utility
from src.utility.MathUtility import MathUtility
from src.utility.CameraUtility import CameraUtility
from src.utility.WriterUtility import WriterUtility
from src.utility.Initializer import Initializer
from src.utility.loader.ShapeNetLoader import ShapeNetLoader
from src.utility.LightUtility import Light
from src.utility.PostProcessingUtility import PostProcessingUtility
from src.utility.RendererUtility import RendererUtility
from src.utility.sampler.Sphere import Sphere

import argparse

parser = argparse.ArgumentParser()
parser.add_argument('shapenet_path', help="Path to the downloaded shape net core v2 dataset, get it from http://www.shapenet.org/")
parser.add_argument('output_dir', nargs='?', default="examples/datasets/shapenet/output", help="Path to where the final files, will be saved")
args = parser.parse_args()

Initializer.init()

# load the ShapeNet object into the scene
shapenet_obj = ShapeNetLoader.load(args.shapenet_path, used_synset_id="02691156", used_source_id="10155655850468db78d106ce0a280f87")

# define a light and set its location and energy level
light = Light()
light.set_type("POINT")
light.set_location([5, -5, 5])
light.set_energy(1000)

# Sample five camera poses
for i in range(5):
    # Sample random camera location around the object
    location = Sphere.sample([0, 0, 0], radius=2, mode="SURFACE")
    # Compute rotation based on vector going from location towards the location of the ShapeNet object
    rotation_matrix = CameraUtility.rotation_from_forward_vec(shapenet_obj.get_location() - location)
    # Add homog cam pose based on location an rotation
    cam2world_matrix = MathUtility.build_transformation_mat(location, rotation_matrix)
    CameraUtility.add_camera_pose(cam2world_matrix)

# activate normal and distance rendering
RendererUtility.enable_normals_output()
RendererUtility.enable_distance_output()
# set the amount of samples, which should be used for the color rendering
RendererUtility.set_samples(350)

# render the whole pipeline
data = RendererUtility.render()

# Convert distance to depth data
data["depth"] = PostProcessingUtility.dist2depth(data["distance"])
del data["distance"]

# Collect the metadata of the shapenet object
shapenet_state = {
    "used_synset_id": shapenet_obj.get_cp("used_synset_id"),
    "used_source_id": shapenet_obj.get_cp("used_source_id")
}
# Add to the main data dict (its the same for all frames here)
data["shapenet_state"] = [shapenet_state] * Utility.num_frames()

# Collect state of the camera at all frames
cam_states = []
for frame in range(Utility.num_frames()):
    cam_states.append({
        "cam2world": CameraUtility.get_camera_pose(frame),
        "cam_K": CameraUtility.get_intrinsics_as_K_matrix()
    })
# Adds states to the data dict
data["cam_states"] = cam_states

# write the data to a .hdf5 container
WriterUtility.save_to_hdf5(args.output_dir, data)