# SOURCE: keras-rl/experiments

import argparse
import json
import numpy as np

import matplotlib.pyplot as plt


def movingaverage(values, window):
    weights = np.repeat(1.0, window)/window
    sma = np.convolve(values, weights, 'valid')
    return sma


def visualize_log(filename, figsize=None, output=None, save=False):
    with open(filename, 'r') as f:
        data = json.load(f)
    if 'episode' not in data:
        raise ValueError('Log file "{}" does not contain the "episode" key.'.format(filename))
    episodes = data['episode']

    # Get value keys. The x axis is shared and is the number of episodes.
    keys = sorted(list(set(data.keys()).difference(set(['episode']))))

    if figsize is None:
        figsize = (15., 5. * len(keys))
    f, axarr = plt.subplots(len(keys), sharex=True, figsize=figsize)
    f.suptitle(filename)
    for idx, key in enumerate(keys):
        axarr[idx].plot(episodes, data[key], 'b.')
        axarr[idx].plot(episodes[4:-5], movingaverage(data[key], 10), 'r-')
        axarr[idx].set_ylabel(key)
    plt.xlabel('episodes')
    plt.tight_layout()
    if save:
        figfilename = ''.join(filename.split('.')[:-1])+'.jpg'  # filename but with jpg ending
        plt.savefig(figfilename)
    elif output is None:
        plt.show()
    else:
        plt.savefig(output)


parser = argparse.ArgumentParser()
parser.add_argument('filename', type=str, nargs='+', help='The filename of the JSON log generated during training.')
parser.add_argument('--output', type=str, default=None, help='The output file. If not specified, the log will only be displayed.')
parser.add_argument('--figsize', nargs=2, type=float, default=None, help='The size of the figure in `width height` format specified in points.')
parser.add_argument('--save', dest='save', required=False, action='store_true',
                        help='If this flag is given, then stores the figure with the same name of the log file.')
args = parser.parse_args()

print("got args: ", args)

# You can use visualize_log to easily view the stats that were recorded during training. Simply
# provide the filename of the `FileLogger` that was used in `FileLogger`.
for filename in args.filename:
    visualize_log(filename, output=args.output, figsize=args.figsize, save=args.save)
