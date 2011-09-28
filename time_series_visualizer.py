

# Author: Emmanuelle Gouillart <emmanuelle.gouillart@normalesup.org> 
# Copyright (c) 2010, Emmanuelle Gouillart
# License: BSD Style.


import numpy as np
from glob import glob
import tables as tb
from threading import Thread
from enthought.mayavi import mlab
from enthought.traits.api import HasTraits, Instance, Array, \
    File, Bool, Int, Range, Enum, Button, Tuple, List, on_trait_change
from enthought.traits.ui.api import View, Item, HGroup, Group, RangeEditor
from enthought.tvtk.pyface.scene_model import SceneModel
from enthought.tvtk.pyface.scene_editor import SceneEditor
from enthought.traits.ui.api import TupleEditor, Include
from enthought.mayavi.core.ui.mayavi_scene import MayaviScene
from enthought.mayavi.tools.mlab_scene_model import MlabSceneModel
from enthought.pyface.api import GUI

class ThreadedAction(Thread):
    def __init__(self, dataset, scalar_field):
        Thread.__init__(self)
        self.scalar_field = scalar_field
        self.dataset = dataset

    def run(self):
        new_data = self.dataset[self.dataset.time]
        GUI.invoke_later(setattr, self.scalar_field.mlab_source, 'scalars',
        new_data)

def h5_load(filename, name):
    f = tb.openFile(filename, 'r')
    data = getattr(f.root, name)[:]
    f.close()
    return data

def raw_load(filename, dtype, shape):
    tmp = np.fromfile(filename, dtype=dtype)
    tmp.shape = shape
    return tmp

class DataSet(HasTraits):

    time = Int(0)

    def __init__(self, filelist, mode='h5', name='data', dtype=None, 
                            shape=None):
        self.filelist = filelist 
        self.images = []
        self.slices = None
        for filename in self.filelist:
            self.images.append(filename)
        self.time = 0
        self.preloaded = False
        if mode == 'npy':
            self.load = np.load
        if mode == 'h5':
            self.load = lambda x: h5_load(x, name)
        if mode == 'raw':
            self.load = lambda x: raw_load(x, dtype, shape)

    def load_data(self, file_slice):
        self.data = []
        print("%d files to be loaded" % len(self.images[file_slice]))
        print("This might take some time...")
        for i, image in enumerate(self.images[file_slice]):
            print("loading file %d" % i)
            self.data.append(self.load(image)[self.slices])
        self.preloaded = True

    def __getitem__(self, i):
        if self.preloaded:
            return self.data[i]
        else:
            return np.squeeze(self.load(self.images[i])[self.slices])



class TimeVisualizer(HasTraits):
    """
    A GUI for 3-D visualization and exploration of a time series of 3-D images.
   
    Different formats are possible for the images: hdf5, npy, raw data. 
    Depending on the format, additional information may have to be
    provided.

    The current image is visualized with two perpendicular image plane widgets,
    and it is possible to navigate in the time series by clicking on the next 
    and previous buttons of the GUI, that update the data source in the Mayavi
    pipeline with the corresponding image of the time series. 

    In order to have a smooth transition when the visualization is updated, 
    we update the date source in a separate thread, using the 
    GUI.invoke_later method. See 
    http://code.enthought.com/projects/mayavi/docs/development/html/mayavi/auto/example_compute_in_thread.html
    for an example of how to use threads to update the Mayavi pipeline.

    For faster loading and updating of images, it is possible to preload 
    the 3-D images (which are initially stored in files) as numpy arrays
    in memory, which are accessed faster.

    The volume of interest can be defined in the volume tab of the GUI
    by defining slices through the 3-D volumes.
    """

    #----------- Components of the GUI -----------------
    slices_scene = Instance(MlabSceneModel, ()) 

    # Time evolution tab
    time = Int
    tuped = TupleEditor(cols=1)
    low = Int(0)
    high = Int(10)
    next = Button()
    previous = Button()
    step = Int(1, desc='time step used for loading next and previous states',
            label="step")
    preloaded = Bool(False)
    preload_range = List((0, -1, 1), desc="files to preload", label='files')
    
    # Volume selection tab
    xslice = Tuple((1, 500, 2), desc='x slice', label='x slice')
    yslice = Tuple((1, 490, 2), desc='y slice', label='y slice')
    zslice = Tuple((1, 490, 2), desc='z slice', label='z slice')
    update_volume = Button()

    #------------ Layout of the GUI -----------------
    panel_group =  Group(
                Group(
                    '_', Item('step'), Item('previous', show_label=False),
                         Item('next', show_label=False), 
                         Item('time',
                             editor = RangeEditor(low_name='low',
                                                high_name='high',
                                                format='%i',
                                                mode='spinner')),
                         Item('preloaded'), 
                         Item('preload_range'),
                         label='Evolution', dock='tab'),
                Group(
                         Item('xslice', editor=tuped),   
                         Item('yslice', editor=tuped),
                         Item('zslice', editor=tuped),
                         Item('update_volume', show_label=False),
                         label='Volume', dock='tab'),
                         layout = 'tabbed',
                         )
    view = View(HGroup(
                Item('slices_scene', height=550,
                    show_label=False,
                    editor=SceneEditor(scene_class=MayaviScene)),
                panel_group,
                ),                         
                resizable=True, title='Time evolution'
                         )


    def __init__(self, file_pattern, **kwargs):
        """
        Load a timeseries of 3-D volumes. 

        Parameters
        ----------

        file_pattern: string
            Pathname pattern corresponding to the timeseries to be
            visualized

        dataset: class name
            Name of a class that manipulates the timeseries data. 
            dataset must have a _getitem_ method in order to be indexed, 
            and a _load_data method in order to preload numpy arrays in 
            memory.
        """
        self.filelist = glob(file_pattern)
        self.filelist.sort()
        self.dataset =  DataSet(self.filelist, **kwargs)
        self.high = len(self.filelist)
        self.preload_range[1] = len(self.filelist) - 1
        src = self.dataset[0]
        if max(src.shape) > 200:
            step = 2
        else:
            step = 1
        self.xslice, self.yslice, self.zslice = (0, src.shape[0], step), \
                    (0, src.shape[1], step), (0, src.shape[2], step)
        self.dataset.slices = (slice(*self.xslice),
                                            slice(*self.yslice),
                                            slice(*self.zslice))
        self.sync_trait('time', self.dataset)
            
    def plot(self):
        """
        Visualize the current data volume with two perpendicular
        image plane widgets.
        """
        mlab.clf(figure=self.slices_scene.mayavi_scene)
        self.slices_scene.scene.background = (0, 0, 0)

        self.s = mlab.pipeline.scalar_field(\
            self.dataset[self.dataset.time].astype(np.float),
                    figure=self.slices_scene.mayavi_scene)
        self.ipw_x = mlab.pipeline.image_plane_widget(self.s,
                figure=self.slices_scene.mayavi_scene,
                plane_orientation = 'x_axes')
        self.ipw_y = mlab.pipeline.image_plane_widget(self.s,
                figure=self.slices_scene.mayavi_scene,
                plane_orientation = 'y_axes')
        self.ipw_x.parent.scalar_lut_manager.lut_mode = 'gist_gray'

    def _next_fired(self):
        """
            Update the visualization with the next volume in the dataset.
        """
        self.time += self.step
        self.time = self.dataset.time
        action = ThreadedAction(self.dataset, self.s) 
        action.start()


    def _previous_fired(self):
        """
            Update the visualization with the previous volume in the dataset.
        """
        self.time -= self.step
        action = ThreadedAction(self.dataset, self.s) 
        action.start()

    def _update_volume_fired(self):
        """
            Resample the volume with user-defined slices.
        """
        self.dataset.slices = (slice(*self.xslice),
                                            slice(*self.yslice),
                                            slice(*self.zslice))
        self.plot()

    def _preloaded_changed(self):
        self.dataset.preloaded = not self.dataset.preloaded
        if self.dataset.preloaded:
            _tmp_list = self.preload_range[:]
            _tmp_list[1] += 1
            self.dataset.load_data(slice(*_tmp_list))
        if not self.dataset.preloaded:
            del self.dataset.data



