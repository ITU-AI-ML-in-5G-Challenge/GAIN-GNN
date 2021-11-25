import os

# Uncomment this line in case you want to disable GPU execution
# Note you need to have CUDA installed to run de execution in GPU
os.environ["CUDA_VISIBLE_DEVICES"] = "1"

import tensorflow as tf
import numpy as np
from glob import iglob
import configparser
from itertools import zip_longest
import zipfile
import csv

from read_dataset import input_fn
from routenet_model import RouteNetModel


FILENAME = 'test_retrain_final_submission'

# Remember to change this path if you want to make predictions on the final
# test dataset -> './utils/paths_per_sample_test_dataset.txt'
PATHS_PER_SAMPLE = './utils/paths_per_sample_test_dataset.txt'

##########################
#### PREDICTING BLOCK ####
##########################
def transformation(x, y):
    """Apply an intial transformation on all the samples of the dataset (before feeding the model).
       Note that here you should use the same transformation used for the model training (e.g., in <path>/code/main.py)
           Args:
               x (dict): predictor variables.
               y (array): target variable.
           Returns:
               x,y: The modified predictor/target variables.
    """
    #min-max normalization for capacity, traffic, packets and pathLength predictor variables
    x['capacity'] = (x['capacity']-tf.reduce_min(x['capacity']))/(tf.reduce_max(x['capacity'])-tf.reduce_min(x['capacity']))
    x['traffic'] = (x['traffic']-tf.reduce_min(x['traffic']))/(tf.reduce_max(x['traffic'])-tf.reduce_min(x['traffic']))
    x['packets'] = (x['packets']-tf.reduce_min(x['packets']))/(tf.reduce_max(x['packets'])-tf.reduce_min(x['packets']))
    x['pathLength'] = (x['pathLength']-tf.reduce_min(x['pathLength']))/(tf.reduce_max(x['pathLength'])-tf.reduce_min(x['pathLength']))
    return x, y

# Read the config.ini file
config = configparser.ConfigParser()
config._interpolation = configparser.ExtendedInterpolation()
config.read('config_submission.ini')

# Load the model
model = RouteNetModel(config)

# Load the last model checkpoint. Note that here you may not want to load the last trained model,
# but the one that obtained better performance on the validation dataset
# The path to the model is expected to be in the 'config.ini' file, variable 'logs'
ckpt_dir = config['DIRECTORIES']['logs']
latest = tf.train.latest_checkpoint(ckpt_dir)
model.load_weights(latest)

# Ensure that directories are loaded in a given order. It is IMPORTANT to keep this, as it ensures that samples
# are loaded in the desired order
directories = [d for d in iglob(config['DIRECTORIES']['test'] + '/*/*')]
# First, sort by scenario and second, by topology size
directories.sort(key=lambda f: (os.path.dirname(f), int(os.path.basename(f))))

upload_file = open(FILENAME+'.txt', "w")

pred = []
first = True
sum_mape = 0
n_results = 0
print('Starting predictions...')
with open("delays_test.csv", "w", newline='') as csvFile:
    writer = csv.writer(csvFile, delimiter=';')
    for d in directories:
        print('Current directory: ' + d)

        # It is NECESSARY to keep shuffle as 'False', as samples have to be read always in the same order
        ds_test = input_fn(d, shuffle=False)
        ds_test = ds_test.map(lambda x, y: transformation(x, y))
        ds_test = ds_test.prefetch(tf.data.experimental.AUTOTUNE)

        # Generate predictions
        pred = model.predict(ds_test)

        # If you need to denormalize or process the model predictions do it here
        # E.g.:
        # y = np.exp(pred)
        
        # Here, we apply the process of the occupancy to translate it into delay per path.

        from datanetAPI import DatanetAPI
        tool = DatanetAPI(d, shuffle=False)
        it = iter(tool)
        results = []
        for sample in it:
            P = sample.get_performance_matrix()
            G = sample.get_topology_object().copy()
            T = sample.get_traffic_matrix()
            R = sample.get_routing_matrix()
            D = sample.get_performance_matrix()
            it_results = iter(pred)

            #create src, dst occupancy list
            occupancy = np.zeros((len(G.nodes),len(G.nodes)))

            for edge in G.edges:
                src, dst, t = edge
                occupancy[src][dst] = next(it_results)

            for src in range(G.number_of_nodes()):
                for dst in range(G.number_of_nodes()):
                    if src != dst:
                        for f_id in range(len(T[src, dst]['Flows'])):
                            if T[src, dst]['Flows'][f_id]['AvgBw'] != 0 and T[src, dst]['Flows'][f_id]['PktsGen'] != 0:
                                route = R[src,dst]
                                delay_route = 0
                                for index, node in enumerate(route):
                                    next_node_index = index + 1
                                    if next_node_index < len(route):
                                        #for each step in route (node, next node) find occupancy
                                        if occupancy[node][route[next_node_index]] < 0:
                                            occupancy[node][route[next_node_index]] = 0
                                        elif occupancy[node][route[next_node_index]] > 1:
                                            occupancy[node][route[next_node_index]] = 1
                                        #compute delay
                                        delay = occupancy[node][route[next_node_index]]*G.nodes[node]['queueSizes']*T[src, dst]['Flows'][f_id]['SizeDistParams']['AvgPktSize']/G[node][route[next_node_index]][0]['bandwidth']
                                        #sum results per path
                                        delay_route += delay
                                # save to results array
                                delay = P[src, dst]['Flows'][f_id]['AvgDelay']
                                error = delay_route-delay
                                abs_error = abs((delay_route-delay)/delay)
                                # delay, delay_calculat, error, abs_error, pkts_drop, avglndelay, avgbw, pktsgen, path_length
                                resultDelay = [
                                    str(delay),
                                    str(delay_route),
                                    str(error),
                                    str(abs_error),
                                    D[src,dst]["AggInfo"]["PktsDrop"],
                                    D[src,dst]["AggInfo"]["AvgLnDelay"],
                                    T[src,dst]["AggInfo"]["AvgBw"],
                                    T[src,dst]["AggInfo"]["PktsGen"],
                                    len(R[src,dst])
                                ]
                                writer.writerow(resultDelay)
                                sum_mape += abs((delay_route-delay)/delay)
                                results.append(delay_route)
        # Separate predictions of each sample; each line contains all the per-path predictions of that sample
        # excluding those paths with no traffic (i.e., flow['AvgBw'] != 0 and flow['PktsGen'] != 0)
        idx = 0
        n_results += len(results)
        for x, y in ds_test:
            top_pred = results[idx: idx+int(x['n_paths'])]
            idx += int(x['n_paths'])
            if not first:
                upload_file.write("\n")
            upload_file.write("{}".format(';'.join([format(i,'.6f') for i in np.squeeze(top_pred)])))
            first = False

upload_file.close()

mape = 100/n_results*sum_mape
print("MAPE: "+str(mape)+" %")
"""
zipfile.ZipFile(FILENAME+'.zip', mode='w').write(FILENAME+'.txt')

########################################################
###### CHECKING THE FORMAT OF THE SUBMISSION FILE ######
########################################################
sample_num = 0
error = False
print("Checking the file...")

with open(FILENAME + '.txt', "r") as uploaded_file, open(PATHS_PER_SAMPLE, "r") as path_per_sample:
    # Load all files line by line (not at once)
    for prediction, n_paths in zip_longest(uploaded_file, path_per_sample):
        # Case 1: Line Count does not match.
        if n_paths is None or prediction is None:
            print("WARNING: File must contain 1560 lines in total for the final test datset (90 for the toy dataset). "
                  "Looks like the uploaded file has {} lines".format(sample_num))
            error = True

        # Remove the \n at the end of lines
        prediction = prediction.rstrip()
        n_paths = n_paths.rstrip()

        # Split the line, convert to float and then, to list
        prediction = list(map(float, prediction.split(";")))

        # Case 2: Wrong number of predictions in a sample
        if len(prediction) != int(n_paths):
            print("WARNING in line {}: This sample should have {} path delay predictions, "
                  "but it has {} predictions".format(sample_num, n_paths, len(prediction)))
            error = True

        sample_num += 1

if not error:
    print("Congratulations! The submission file has passed all the tests! "
          "You can now submit it to the evaluation platform")"""