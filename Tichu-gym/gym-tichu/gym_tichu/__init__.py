from gym.envs.registration import register

register(
    id='tichu_multiplayer-v0',
    entry_point='gym_tichu.envs:TichuMultiplayerEnv',
    reward_threshold=200.0,
    nondeterministic=True,
)

register(
    id='tichu_singleplayer_random-v0',
    entry_point='gym_tichu.envs:TichuSinglePlayerAgainstRandomEnv',
    reward_threshold=200.0,
    nondeterministic=True,
)

register(
    id='tichu_singleplayer_learned-v0',
    entry_point='gym_tichu.envs:TichuSinglePlayerAgainstLatestQAgentEnv',
    reward_threshold=200.0,
    nondeterministic=True,
)

register(
    id='tichu_singleplayer_learning-v0',
    entry_point='gym_tichu.envs:TichuSinglePlayerAgainstTheTrainingQAgentEnv',
    reward_threshold=200.0,
    nondeterministic=True,
)
