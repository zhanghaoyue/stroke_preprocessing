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
        self.bet_anat = None
        self.segmentation = None
        self.threshold = None
        self.coreg_pre = None
        self.coreg_mi = None
        self.applywarp = None
        self.applywarp_mean = None

    @staticmethod
    def get_wm(files):
        return files[-1]

    def build_nodes(self):
        # BET - Skullstrip anatomical Image
        self.bet_anat = Node(fsl.BET(frac=0.5,
                                     robust=True,
                                     output_type='NIFTI_GZ'),
                             name="bet_anat")
        # image segmentation
        self.segmentation = Node(fsl.FAST(output_type='NIFTI_GZ'), name='segmentation')

        # threshold WM probability image
        self.threshold = Node(fsl.Threshold(thresh=0.5,
                                            args='-bin',
                                            output_type='NIFTI_GZ'),
                              name='threshold')

        # flirt - pre-alignment of images
        self.coreg_pre = Node(fsl.FLIRT(dof=6, output_type='NIFTI_GZ'), name='coreg_pre')
        # co-reg
        self.coreg_mi = Node(fsl.FLIRT(bins=640, cost_func='bbr', interp='spline', searchr_x=[-180, 180],
                                        searchr_y=[-180, 180], searchr_z=[-180, 180], dof=6, output_type='NIFTI_GZ'),
                              name='coreg_mi')

        # apply warp map to images
        self.applywarp = Node(fsl.preprocess.ApplyXFM(apply_xfm=True,
                                                      output_type='NIFTI_GZ'),
                              name='applywarp')

        # Apply coregistration warp to mean file
        self.applywarp_mean = Node(fsl.FLIRT(interp='spline',output_type='NIFTI_GZ'), name="applywarp_mean")

    def build_workflow(self, exp_dir, work_dir):
        coregwf = Workflow(name='coregwf')
        coregwf.base_dir = os.path.join(exp_dir, work_dir)
        coregwf.connect([(self.bet_anat, self.segmentation, [('out_file', 'in_files')]),
                         (self.segmentation, self.threshold, [(('partial_volume_files', get_wm),
                                                     'in_file')]),
                         (self.bet_anat, self.coreg_pre, [('out_file', 'reference')]),
                         (self.threshold, self.coreg_mi, [('out_file', 'wm_seg')]),
                         (self.coreg_pre, self.coreg_mi, [('out_matrix_file', 'in_matrix_file')]),
                         (self.coreg_mi, self.applywarp, [('out_matrix_file', 'in_matrix_file')]),
                         (self.bet_anat, self.applywarp, [('out_file', 'reference')]),
                         (self.coreg_mi, self.applywarp_mean, [('out_matrix_file', 'in_matrix_file')]),
                         (self.bet_anat, self.applywarp_mean, [('out_file', 'reference')]),
                         ])

        return coregwf
