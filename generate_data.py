import numpy as np
import os, os.path
from glob import glob
import tables as tb

def generate_big_data(l=200, t=20, mode='npy'):
    """ 
    Generate synthetic data to test visualizer

    Parameters
    ----------

    l: int, optional
        Linear size of output data

    t: int, optional
        Number of samples to generate

    mode: string in {'npy', 'h5', 'raw'}, optional
        Format in which to save data. Can be
        * 'npy' (numpy binary format)
        * 'h5' (hdf5)
        * 'raw' (raw binary data)
    """
    x, y, z = np.mgrid[0:5:l*1j, 0:5:l*1j, 0:5:l*1j]
    if os.path.exists('data'):
        [os.remove(filename) for filename in glob('data/data*')]
    else:
        os.mkdir('data')
    for t in np.linspace(0, 1, t + 1):
        field = np.sin(2*np.pi * ((x % 1) * (y % 1) * (z % 1) + t))
        if mode=='npy':
            np.save(os.path.join('data', 'data_%.2f.npy' % t), field)
        if mode=='raw':
            field.tofile(os.path.join('data', 'data_%.2f.raw' % t))
        if mode=='h5':
            f = tb.openFile(os.path.join('data', 'data_%.2f.h5' % t), 'a')
            f.createArray(f.root, 'image', field)
            f.close()

def generate_quarters():
    if os.path.exists('data'):
        [os.remove(filename) for filename in glob('data/quarters*.npy')]
    else:
        os.mkdir('data')
    x, y, z = np.mgrid[0:1:100j, 0:1:100j, 0:1:100j]
    l_data = [y < 0.5,
              y > 0.5,
              z < 0.5,
              z > 0.5,
              np.logical_and(y < 0.5, z < 0.5),        
              np.logical_and(y < 0.5, z > 0.5),        
              np.logical_and(y > 0.5, z < 0.5),        
              np.logical_and(y > 0.5, z > 0.5)]        
    for t in np.arange(8):
        np.save(os.path.join('data', 'quarters_%i.npy' % t),\
                l_data[t].astype(np.float))
    

