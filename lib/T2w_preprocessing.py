#!/usr/bin/env python
# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:


import os.path as op

from nipype.interfaces import ants
from nipype.interfaces import freesurfer as fs
from nipype.interfaces import fsl
from nipype.interfaces import utility as niu
from nipype import Workflow, Node
import nipype.pipeline.engine as pe

from niworkflows.interfaces.mni import RobustMNINormalization
from niworkflows.anat.skullstrip import afni_wf as skullstrip_wf

test_dir = '/home/harryzhang/Desktop/test_registration/'


#  pylint: disable=R0914
def t2w_preprocessing(name='t2w_preprocessing', skull_stripping='BET', registration='fsl'):
    """T2w images preprocessing pipeline"""

    workflow = Workflow(name=name)

    input_node = Node(niu.IdentityInterface(fields=['t2w']), name='input_node')
    output_node = Node(niu.IdentityInterface(
        fields=['t2_seg', 'bias_corrected_t2', 't2_brain', 't2_2_mni',
                't2_2_mni_forward_transform', 't2_2_mni_reverse_transform',
                't2_segmentation']), name='output_node')

    # 1. Reorient T2
    arw = Node(fs.MRIConvert(out_type='niigz', out_orientation='LAS'), name='Reorient')

    # 2. T2 Bias Field Correction
    inu_n4 = Node(ants.N4BiasFieldCorrection(dimension=3), name='CorrectINU')

    # 3. Skull-stripping
    if skull_stripping == 'ANTS':
        asw = skullstrip_wf()
    elif skull_stripping == 'BET':
        asw = Node(fsl.BET(frac=0.2,
                           robust=True,
                           vertical_gradient=0.7,
                           output_type='NIFTI_GZ'),
                   name="asw")

    # 4. Segmentation
    t2_seg = Node(fsl.FAST(no_bias=True, probability_maps=True), name='Segmentation')

    # 5. Spatial normalization (T2w to MNI registration), only rigid body transformation
    if registration == "freesurfer":
        t2_2_mni = Node(RobustMNINormalization(num_threads=4, testing=False), name='T2_2_MNI_Registration')
    elif registration =='fsl':
        t2_2_mni = Node(fsl.FLIRT(bins=640, cost_func='mutualinfo', interp='spline',
                searchr_x=[-180, 180], searchr_y=[-180, 180], searchr_z=[-180, 180], dof=6))

    # Resample the brain mask and the tissue probability maps into mni space
    bmask_mni = Node(ants.ApplyTransforms(
        dimension=3, default_value=0, interpolation='NearestNeighbor'), name='brain_mni_warp')
    bmask_mni.inputs.reference_image = test_dir+'baseanat.nii.gz'
    tpms_mni = pe.MapNode(ants.ApplyTransforms(dimension=3, default_value=0, interpolation='Linear'),
                          iterfield=['input_image'], name='tpms_mni_warp')
    tpms_mni.inputs.reference_image =test_dir+'baseanat.nii.gz'

    workflow.connect([
        (input_node, inu_n4, [('out_file', 'input_image')]),
        (inu_n4, asw, [('output_image', 'input_node.in_file')]),
        (asw, t2_seg, [('output_node.out_file', 'in_files')]),
        (inu_n4, t2_2_mni, [('output_image', 'moving_image')]),
        (asw, t2_2_mni, [('output_node.out_mask', 'moving_mask')]),
        (t2_seg, output_node, [('tissue_class_map', 't2_seg')]),
        (inu_n4, output_node, [('output_image', 'bias_corrected_t2')]),
        (t2_seg, output_node, [('tissue_class_map', 't2_segmentation')]),
        (t2_2_mni, output_node, [
            ('warped_image', 't2_2_mni'),
            ('forward_transforms', 't2_2_mni_forward_transform'),
            ('reverse_transforms', 't2_2_mni_reverse_transform')
        ]),
        (asw, bmask_mni, [('output_node.out_mask', 'input_image')]),
        (t2_2_mni, bmask_mni, [('forward_transforms', 'transforms'),
                               ('forward_invert_flags', 'invert_transform_flags')]),
        (t2_seg, tpms_mni, [('probability_maps', 'input_image')]),
        (t2_2_mni, tpms_mni, [('forward_transforms', 'transforms'),
                              ('forward_invert_flags', 'invert_transform_flags')]),
        (asw, output_node, [
            ('output_node.out_file', 't2_brain')]),
    ])

    return workflow


