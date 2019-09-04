import os
from nipype.interfaces import ants
from nipype.interfaces import freesurfer as fs
from nipype.interfaces import fsl
from nipype.interfaces import utility as niu
from nipype import Workflow, Node
import nipype.pipeline.engine as pe


# specify nodes for main workflow
class ImageCoregistration:

    def __init__(self):
        self.segmentation = None
        self.threshold = None
        self.coreg_pre = None
        self.applywarp = None
        self.applywarp_mean = None

    @staticmethod
    def get_wm(files):
        return files[-1]

    def build_nodes(self):

        # image segmentation
        self.segmentation = Node(fsl.FAST(output_type='NIFTI_GZ'), name='segmentation')
        # threshold WM probability image
        self.threshold = Node(fsl.Threshold(thresh=0.5,
                                            args='-bin',
                                            output_type='NIFTI_GZ'),
                              name='threshold')

        # flirt - pre-alignment of images
        self.coreg_pre = Node(fsl.FLIRT(dof=6, interp='spline', output_type='NIFTI_GZ'), name='coreg_pre')

        # apply warp map to images
        self.applywarp = Node(fsl.preprocess.ApplyXFM(apply_xfm=True,
                                                      output_type='NIFTI_GZ'),
                              name='applywarp')

    def build_workflow(self, exp_dir, work_dir):
        coregwf = Workflow(name='coregwf')
        coregwf.base_dir = os.path.join(exp_dir, work_dir)

        coregwf.connect([(self.segmentation, self.threshold, [(('partial_volume_files', self.get_wm), 'in_file')]),
                         (self.coreg_pre, self.applywarp, [('out_matrix_file', 'in_matrix_file')]),
                         (self.applywarp, self.applywarp_mean, [('out_matrix_file', 'in_matrix_file')]),
                         ])
