import argparse
import os, sys, inspect
import torch
from torch.autograd import Variable
import pybullet as bullet

import gym
from kuka.env import KukaPoseEnv
import numpy as np

sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'pytorch_a2c_ppo_acktr'))


parser = argparse.ArgumentParser(description='Record a taught KUKA agent movement')

parser.add_argument('--env-name', default='KukaPoseEnv-v0',
                    help='environment to train on (default: KukaTrainPoseEnv-v0.pt)')
parser.add_argument('--model-name', default='KukaPoseEnv-v0',
                    help='environment to train on (default: KukaPoseEnv-v0)')
parser.add_argument('--model-dir', default='./pytorch_a2c_ppo_acktr/trained_models/ppo/', help='load model from directory')
parser.add_argument('--num-stack', type=int, default=4,
                    help='number of frames to stack (default: 4) Needs to be the same when the model was trained')
parser.add_argument('--video-dir', default='./tmp/video/',
                    help='')
args = parser.parse_args()

def repeat_trajectory(env, human_pos, actions, camera_position, file_name):

    # Camera position
    bullet.resetDebugVisualizerCamera(camera_position['distance'], camera_position['yaw'], camera_position['pitch'], human_pos)

    bullet.startStateLogging(bullet.STATE_LOGGING_VIDEO_MP4, args.video_dir + file_name)

    for step, action in enumerate(actions):

        state, reward, done, _ = env.step(action)

def record_trajectory(camera_positions):

    env = gym.make(args.model_name)
    # model
    actor_critic = torch.load(os.path.join(args.model_dir, args.model_name+ ".pt"))
    actor_critic.eval()

    obs_shape = (env.observation_space.shape[0] * args.num_stack,)
    current_state = torch.zeros(1, *obs_shape)

    def update_current_state(state):
        shape_dim0 = env.observation_space.shape[0]
        state = torch.from_numpy(state).float()
        if args.num_stack > 1:
            current_state[:, :-shape_dim0] = current_state[:, shape_dim0:]
        current_state[:, -shape_dim0:] = state

    # building the environment
    env.render('human')
    state = env.reset()
    update_current_state(state)

    # identifying robot first link frame id 

    FRAME_ID = -1
    for i in range(bullet.getNumBodies()):
        if (bullet.getBodyInfo(i)[0].decode() == "lbr_iiwa_link_0"):
            FRAME_ID = i

    assert(FRAME_ID > -1)

    human_pos, humanOrn = bullet.getBasePositionAndOrientation(FRAME_ID)

    for trajectory_index in range(0,3):

        done = False

        distance = 5
        yaw = 0
        pitch = -20
        file_name = "trajectory-{}_position-{}.mp4".format(trajectory_index, 0)

        bullet.resetDebugVisualizerCamera(distance, yaw, pitch, human_pos)
        bullet.startStateLogging(bullet.STATE_LOGGING_VIDEO_MP4, args.video_dir + file_name)

        actions = []
        total_reward = 0.

        while not(done):

            value, action = actor_critic.act(Variable(current_state, volatile=True),deterministic=True)

            action = action.data.cpu().numpy()[0]
            state, reward, done, _ = env.step(action)
            total_reward += reward 

            # save action: repeat_trajectory 
            actions.append(action)
                
            update_current_state(state)

            
        print("---NEW TRAJECTORY BUILT---")
        print("Lastreward", reward)
        print("Total reward", total_reward)

        # camera positions
        
        for position_index, position in enumerate(camera_positions):

            state = env.reset()

            file_name = "trajectory-{}_position-{}.mp4".format(trajectory_index, position_index + 1) 

            repeat_accuracy = repeat_trajectory(env, human_pos, actions, position, file_name)
            print("Repeat Accuracy: ", repeat_accuracy)
        
        state = env.reset()

def main():
    camera_positions = [{
                'distance': 3,
                'pitch': -20,
                'yaw': 3,
            }, {
                'distance': 3,
                'pitch': -2,
                'yaw': 10,
            }]
    record_trajectory(camera_positions)
    

if __name__ == "__main__":
    main()