

python -O run_experiments.py best_vs_random --target 10000 --pool_size 1 &
python -O run_experiments.py best_vs_plain_ismcts --target 10000 --pool_size 1 &
python -O run_experiments.py best_vs_random_det --target 10000 --pool_size 1 &
python -O run_experiments.py best_vs_random_rollout --target 10000 --pool_size 1 &
python -O run_experiments.py best_vs_epic --target 10000 --pool_size 1 &
python -O run_experiments.py best_vs_epic_no_rollout --target 10000 --pool_size 1 &