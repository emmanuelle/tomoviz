import numpy as np
from time_series_visualizer import TimeVisualizer
from generate_data import generate_big_data
from glob import glob

# Data in format 'h5'

print("Visualizing data stored in hdf5 format")
generate_big_data(l=60, t=10, mode='h5')
tv_h5 = TimeVisualizer('data/data*.h5', mode='h5', name='image')
tv_h5.configure_traits()
tv_h5.plot()

# Data in format 'npy'

print("Visualizing data stored in npy format")
generate_big_data(l=60, t=10, mode='npy')
tv_npy = TimeVisualizer('data/data*.npy', mode='npy')
tv_npy.configure_traits()
tv_npy.plot()

# Data in format 'raw'

print("Visualizing data stored in raw format")
generate_big_data(l=60, t=10, mode='raw')
tv_raw = TimeVisualizer('data/data*.raw', mode='raw', dtype=np.float, 
                        shape=(60, 60, 60))
tv_raw.configure_traits()
tv_raw.plot()

