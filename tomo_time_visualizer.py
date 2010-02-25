import numpy as np
import scipy
from glob import glob
from threading import Thread
from time import sleep
from enthought.mayavi import mlab
from enthought.traits.api import HasTraits, Instance, Array, \
    File, Bool, Int, Enum, Button, Tuple, on_trait_change
from enthought.traits.ui.api import View, Item, HGroup, Group
from enthought.tvtk.pyface.scene_model import SceneModel
from enthought.tvtk.pyface.scene_editor import SceneEditor
from enthought.traits.ui.api import TupleEditor, Include
from enthought.mayavi.core.ui.mayavi_scene import MayaviScene
from enthought.mayavi.tools.mlab_scene_model import MlabSceneModel
from process_tomo.process.tomoimage import TomoImage
from enthought.pyface.api import GUI

class ThreadedAction(Thread):
    def __init__(self, dataset, scalar_field):
        Thread.__init__(self)
        self.scalar_field = scalar_field
        self.dataset = dataset

    def run(self):
        if self.dataset.preloaded:
            new_data = self.dataset.data[self.dataset.time]
        else:
            slices = self.dataset.slices
            new_data = self.dataset.images[self.dataset.time].data[slices]
        GUI.invoke_later(setattr, self.scalar_field.mlab_source, 'scalars',
        new_data)
        print 'done.'

class DataSet(object):

    def __init__(self, filelist, preload=True):
        self.filelist = filelist 
        self.images = []
        for filename in self.filelist:
            self.images.append(TomoImage(filename))
        for image in self.images:
            image.open()
        self.time = 0
        self.preloaded = False
        
    def load_data(self, file_slice):
        self.data = []
        for i, image in enumerate(self.images[file_slice]):
            print i
            self.data.append(image.data[self.slices])
        self.preloaded = True

class TimeVisualizer(HasTraits):

    time = Int()
    tuped = TupleEditor(cols=1)
    slices_scene = Instance(MlabSceneModel, ())
    volume_scene = Instance(MlabSceneModel, ())
    next = Button()
    previous = Button()
    xslice = Tuple((1, 500, 2), desc='x slice', label='x slice')
    yslice = Tuple((1, 490, 2), desc='y slice', label='y slice')
    zslice = Tuple((1, 490, 2), desc='z slice', label='z slice')
    update_volume = Button()
    update_view = Button()
    step = Int(1, desc='time step used for loading next and previous states',
            label="step")
    preloaded = Bool(False)
    preload_range = Tuple((0, -1, 1), desc="files to preload", label='files')
    select_points = Bool(False, label='Point selection')

    panel_group =  Group(
                Group(
                    '_', Item('step'), Item('previous', show_label=False),
                         Item('next', show_label=False), Item('time'),
                         Item('preloaded'), 
                         Item('preload_range', editor=tuped),
                         Item('select_points'),
                         label='Evolution', dock='tab'),
                Group(
                         Item('xslice', editor=tuped),   
                         Item('yslice', editor=tuped),
                         Item('zslice', editor=tuped),
                         Item('update_volume', show_label=False),
                         Item('update_view', show_label=False),
                         label='Volume', dock='tab'),
                         layout = 'tabbed',
                         )
    view = View(HGroup(
                Item('slices_scene', height=550,
                    show_label=False,
                    editor=SceneEditor(scene_class=MayaviScene)),
                panel_group,
                ),                         
                resizable=True, title='Glass batch tomography'
                         )

    def __init__(self, file_pattern, preload=True):
        self.filelist = glob(file_pattern)
        self.filelist.sort()
        self.dataset = DataSet(self.filelist)
        self.dataset.slices = (slice(*self.xslice),
                                            slice(*self.yslice),
                                            slice(*self.zslice))
        #if preload:
        #    self.dataset.load_data()
            
    def plot(self):
        mlab.clf(figure=self.slices_scene.mayavi_scene)
        self.slices_scene.scene.background = (0, 0, 0)
        self.s = mlab.pipeline.scalar_field(
            self.dataset.images[self.dataset.time].data[slice(*self.xslice), 
                                            slice(*self.yslice),
                                            slice(*self.zslice)],

                    figure=self.slices_scene.mayavi_scene)
        self.ipw_x = mlab.pipeline.image_plane_widget(self.s,
                figure=self.slices_scene.mayavi_scene,
                plane_orientation = 'x_axes')
        self.ipw_y = mlab.pipeline.image_plane_widget(self.s,
                figure=self.slices_scene.mayavi_scene,
                plane_orientation = 'y_axes')
        self.ipw_x.parent.scalar_lut_manager.lut_mode = 'gist_gray'
        self.ipw_x.parent.scalar_lut_manager.data_range = np.array([-2,2])
        #filtered = 

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
        action = ThreadedAction(self.dataset, self.s)
        action.start()

    def _update_view_fired(self):
        self.plot()

    def _preloaded_changed(self):
        self.dataset.preloaded = not self.dataset.preloaded
        if self.dataset.preloaded:
            print self.preload_range
            self.dataset.load_data(slice(*self.preload_range))
        if not self.dataset.preloaded:
            del self.dataset.data

class CompareVisualizer(TimeVisualizer):

    reference_scene = Instance(MlabSceneModel, ())

    view = View(
            HGroup(
            Item('reference_scene', height=550, show_label=False,
                editor=SceneEditor(scene_class=MayaviScene)),
            Item('slices_scene', height=550, show_label=False,
                editor=SceneEditor(scene_class=MayaviScene)),
                Include('panel_group'),
            ),
            resizable=True, title='Glass batch tomography'
        )

    def __init__(self, file_pattern, reference_file, preload=True):
        TimeVisualizer.__init__(self, file_pattern, preload)
        self.reference_file = reference_file
        self.configure_traits()
        self.plot()
        self.plot_reference()


    def plot_reference(self):
        self.im_ref = TomoImage(self.reference_file)
        self.im_ref.open()
        self.reference_scene.scene.background = (0, 0, 0)
        self.s_ref = mlab.pipeline.scalar_field(
            self.im_ref.data[slice(*self.xslice),
                                slice(*self.yslice),
                                slice(*self.zslice)],
            figure=self.reference_scene.mayavi_scene)
        self.ipw_ref_x = mlab.pipeline.image_plane_widget(self.s_ref,
                figure=self.reference_scene.mayavi_scene,
                plane_orientation = 'x_axes')
        self.ipw_ref_y = mlab.pipeline.image_plane_widget(self.s_ref,
                figure=self.reference_scene.mayavi_scene,
                plane_orientation = 'y_axes')
        self.ipw_ref_x.parent.scalar_lut_manager.lut_mode = 'gist_gray'
        self.ipw_ref_x.parent.scalar_lut_manager.data_range = np.array([-2,2])

    def _select_points_changed(self):
        for ipw in [self.ipw_x, self.ipw_y, self.ipw_ref_x, self.ipw_ref_y]:
            ipw.ipw.interaction = not ipw.ipw.interaction  

def picker_callback(picker_obj):
    position = picker_obj.pick_position
    grains.append(position)
    gg = np.array(grains).T
    del tv.pts
    tv.pts = mlab.points3d(gg[0], gg[1], gg[2], scale_factor=10, color=(1,0,0))    


class ClickVisualizer(CompareVisualizer):

    rt_grains = []
    ht_grains = []

    def __init__(self, file_pattern, reference_file, preload=True):
        CompareVisualizer.__init__(self, file_pattern, reference_file, preload=True)
        self.reference_scene.mayavi_scene.on_mouse_pick(picker_callback, button='Middle', type='world')
        self.slices_scene.mayavi_scene.on_mouse_pick(picker_callback, button='Middle', type='world')
        self.pts = mlab.points3d(1, 1, 1, scale_factor=0, figure=self.reference_scene.mayavi_scene)

grains = []
tv = ClickVisualizer('/media/data_linux/tomography/090228/volumes/heated_sample/glass_00[0, 1, 2]_smooth.h5', '/media/data_linux/tomography/090228/volumes/room_temperature/rt_smooth.h5')
