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
from enthought.traits.ui.api import TupleEditor
from enthought.mayavi.core.ui.mayavi_scene import MayaviScene
from enthought.mayavi.tools.mlab_scene_model import MlabSceneModel
from process_tomo.process.tomoimage import TomoImage
from enthought.pyface.api import GUI

class ThreadedAction(Thread):
    def __init__(self, scalar_field, new_data):
        Thread.__init__(self)
        self.scalar_field = scalar_field
        self.new_data = new_data

    def run(self):
        #self.scalar_field.mlab_source.scalars[:] = self.new_data[:]
        GUI.invoke_later(setattr, self.scalar_field.mlab_source, 'scalars',
        self.new_data)
        print 'done.'

class TimeVisualizer(HasTraits):

    tuped = TupleEditor(cols=3)
    scene = Instance(MlabSceneModel, ())
    next = Button()
    previous = Button()
    xslice = Tuple((0, 150, 1), desc='x slice', label='x slice')
    yslice = Tuple((0, 150, 1), desc='y slice', label='y slice')
    zslice = Tuple((0, 150, 1), desc='z slice', label='z slice')
    step = Int(1, desc='time step used for loading next and previous states',
            label="step")

    view = View(HGroup(Item('scene', height=550, show_label=False,
                    editor=SceneEditor(scene_class=MayaviScene)),
                Group(
                Group(
                    '_', Item('step'), Item('previous', show_label=False),
                         Item('next', show_label=False),
                         label='Evolution', dock='tab'),
                Group(
                         Item('xslice', editor=tuped),   
                         Item('yslice', editor=tuped),
                         Item('zslice', editor=tuped),
                         label='Volume', dock='tab'),
                         layout = 'tabbed',
                         )))

    def __init__(self, file_pattern, beg=0, end=10):
        self.filelist = glob(file_pattern)
        self.filelist.sort()
        self.images = []
        for filename in self.filelist[beg:end]:
            self.images.append(TomoImage(filename))
        for image in self.images:
            image.open()
        self.time = 0
            
    def plot(self):
        mlab.clf(figure=self.scene.mayavi_scene)
        self.s = mlab.pipeline.scalar_field(
                self.images[self.time].data[slice(*self.xslice), 
                                            slice(*self.yslice),
                                            slice(*self.zslice)])
        self.ipw = mlab.pipeline.image_plane_widget(self.s)
        mlab.show()

    def _next_fired(self):
        self.time += self.step
        action = ThreadedAction(self.s, 
            self.images[self.time].data[slice(*self.xslice),
                                        slice(*self.yslice),                                                            slice(*self.zslice)]
            )
        action.start()


    def _previous_fired(self):
        self.time -= self.step
        action = ThreadedAction(self.s, 
            self.images[self.time].data[slice(*self.xslice),
                                        slice(*self.yslice),                                                            slice(*self.zslice)]
            )
        action.start()

