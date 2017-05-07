from gym.envs.registration import register

register(
    id='tichu_multiplayer-v0',
    entry_point='gym_tichu.envs:TichuMultiplayerEnv',
    reward_threshold=200.0,
    nondeterministic=True,
)
