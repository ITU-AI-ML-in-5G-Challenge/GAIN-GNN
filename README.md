# GAIN Solution: RouteNet - Graph Neural Networking challenge 2021

#### Organized as part of "ITU AI/ML in 5G challenge"

#### Challenge website: https://bnn.upc.edu/challenge/gnnet2021

[RouteNet](https://arxiv.org/abs/1901.08113) is a Graph Neural Network (GNN) model that estimates per-source-destination performance metrics (e.g., delay, jitter, loss) in networks. Thanks to its GNN architecture that operates over graph-structured data, RouteNet revealed an unprecedented ability to learn and model the complex relationships among topology, routing and input traffic in networks. As a result, it was able to make performance predictions with similar accuracy than costly packet-level simulators even in network scenarios unseen during training. This provides network operators with a functional tool able to make accurate predictions of end-to-end Key Performance Indicators (e.g., delay, jitter, loss).

<p align="center"> 
  <img src="/assets/routenet_scheme.png" width="600" alt>
</p>

## Quick Start
### Requirements
We strongly recommend use Python 3.7, since lower versions of Python may cause problems to define all the PATH environment variables.
The following packages are required:
* Tensorflow >= 2.4. You can install it following the official [Tensorflow 2 installation guide.](https://www.tensorflow.org/install)
* NetworkX >= 2.5. You can install it using *pip* following the official [NetworkX installation guide.](https://networkx.github.io/documentation/stable/install.html)
* Pandas >= 0.24. You can install it using *pip* following the official [Pandas installation guide.](https://pandas.pydata.org/pandas-docs/stable/getting_started/install.html)

### Testing the installation
In order to test the installation, we provide a toy dataset that contains some random samples. You can simply verify your installation by executing the [main.py](/code/main.py) file.
```
python main.py
```

You should see something like this:
```
4000/4000 [==============================] - 314s 76ms/step - loss: 67.8137 - MAPE: 67.8137 - val_loss: 150.7025 - val_MAPE: 150.7025

Epoch 00001: saving model to ../trained_modelsGNNetworkingChallenge\01-150.70-150.70
```
