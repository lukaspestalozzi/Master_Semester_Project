

python -O run_experiments.py dqn_untrained_vs_random_agent --target 100000 &
python -O run_experiments.py dqn_random_vs_learned --target 100000 &
python -O run_experiments.py dqn_random_vs_learning --target 100000 &
python -O run_experiments.py dqn_learned_vs_learning --target 100000 &
python -O run_experiments.py dqn_random_vs_dqnismcts --target 100000 &
python -O run_experiments.py dqn_learned_vs_dqnismcts --target 100000 &
python -O run_experiments.py dqn_learning_vs_dqnismcts --target 100000 &
python -O run_experiments.py dqn_untrained_vs_dqnismcts --target 100000 &