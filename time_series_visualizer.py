import numpy as np
import scipy
from glob import glob
from threading import Thread
from enthought.mayavi import mlab
from enthought.traits.api import HasTraits, Instance, Array, \
    File, Bool, Int, Enum, Button, Tuple, on_trait_change
from enthought.traits.ui.api import View, Item, HGroup, Group
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

class DataSet(object):

    def __init__(self, filelist):
        self.filelist = filelist 
        self.images = []
        self.slices = None
        for filename in self.filelist:
            self.images.append(filename)
        self.time = 0
        self.preloaded = False
        
    def load_data(self, file_slice):
        self.data = []
        for i, image in enumerate(self.images[file_slice]):
            self.data.append(np.load(image)[self.slices])
        self.preloaded = True

    def __getitem__(self, i):
        if self.preloaded:
            return self.data[i]
        else:
            return np.squeeze(np.load(self.images[i])[self.slices])

class DataSetDeque(DataSet):

    item_nb = 5
    deque_time = 0

    def load_data(self, file_slice):
        from collections import deque
        self.data = deque(maxlen=self.item_nb)
        self.file_slice = file_slice
        for i, image in enumerate(self.images[file_slice]\
            [maximum(0, self.time - self.item_nb/2):\
                            self.time + self.item_nb/2 + 1]):
            self.data.append(np.load(image)[self.slices])
        self.preloaded = True
        self.deque_time = self.time
        self.nmax = len(self.images[self.file_slice])

    def refresh(self):
        if self.time > self.deque_time:
            new_index = (self.time + self.item_nb/2) % self.nmax
            image = self.images[self.file_slice][new_index]
            self.data.append(np.load(image)[self.slices])
            self.deque_time = self.time
        else:
            new_index = (self.time - self.item_nb/2) % self.nmax
            image = self.images[self.file_slice][new_index]
            self.data.appendleft(np.load(image)[self.slices])
            self.deque_time = self.time
        
    def __getitem__(self, i):
        print self.time, self.deque_time
        if self.preloaded:
            if self.time < self.nmax/2:
                if self.time > self.deque_time:
                    index = - (self.item_nb/2)
                else:
                    index = - (self.item_nb/2 + 2)
            else:
                if self.time > self.deque_time:
                    index = self.item_nb/2 + 1
                else:
                    index = self.item_nb/2 - 1
            data = self.data[index]
            self.refresh()
            return data
        else:
            return np.squeeze(np.load(self.images[i])[self.slices]) 

class TimeVisualizer(HasTraits):

    #----------- Components of the GUI -----------------
    slices_scene = Instance(MlabSceneModel, ())

    # Time evolution tab
    time = Int()
    tuped = TupleEditor(cols=1)
    next = Button()
    previous = Button()
    step = Int(1, desc='time step used for loading next and previous states',
            label="step")
    preloaded = Bool(False)
    preload_range = Tuple((0, -1, 1), desc="files to preload", label='files')
    
    # Volume selection tab
    xslice = Tuple((1, 500, 2), desc='x slice', label='x slice')
    yslice = Tuple((1, 490, 2), desc='y slice', label='y slice')
    zslice = Tuple((1, 490, 2), desc='z slice', label='z slice')
    update_volume = Button()

    #------------ Arrangement of the GUI -----------------
    panel_group =  Group(
                Group(
                    '_', Item('step'), Item('previous', show_label=False),
                         Item('next', show_label=False), Item('time'),
                         Item('preloaded'), 
                         Item('preload_range', editor=tuped),
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

    def __init__(self, file_pattern):
        self.filelist = glob(file_pattern)
        self.filelist.sort()
        self.dataset = DataSetDeque(self.filelist)
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
        self.configure_traits()
        self.plot()
            
    def plot(self):
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
        self.dataset.time += self.step
        self.time = self.dataset.time
        action = ThreadedAction(self.dataset, self.s) 
        action.start()


    def _previous_fired(self):
        self.dataset.time -= self.step
        self.time = self.dataset.time
        action = ThreadedAction(self.dataset, self.s) 
        action.start()

    def _update_volume_fired(self):
        self.dataset.slices = (slice(*self.xslice),
                                            slice(*self.yslice),
                                            slice(*self.zslice))
        self.plot()

    def _preloaded_changed(self):
        self.dataset.preloaded = not self.dataset.preloaded
        if self.dataset.preloaded:
            self.dataset.load_data(slice(*self.preload_range))
        if not self.dataset.preloaded:
            del self.dataset.data


if __name__ == '__main__':
    """
    from glob import glob
    if glob('data/data*.npy') == []:
        print "generating some synthetic data..."
        from generate_data import generate_big_data
        generate_big_data(l=60, t=10)
    """
    tv = TimeVisualizer('data/data*.npy')


