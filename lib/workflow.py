#!/usr/bin/env python
# -*- coding: utf-8 -*-
# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:


import os.path as op
import os
import json
from os.path import join as opj
from nipype.interfaces import ants
from nipype.interfaces import fsl
from nipype.interfaces.spm import Smooth
from nipype.interfaces.utility import IdentityInterface
from nipype.interfaces.io import SelectFiles, DataSink
from nipype import Workflow, Node

# options
experiment_dir = 'output'
output_dir = 'datasink'
working_dir = '/media/harryzhang/VolumeWD/'

# list of subject identifiers
patient_list = ['540335']

# list of session identifiers
task_list = ['DWI', 'ADC', 'FLAIR','TTP']

# Smoothing widths to apply
fwhm = [2, 3, 4]



# main workflow

# Reorient
reorient = Node(fsl.Reorient2Std(output_type='NIFTI_GZ',ignore_exception=True), name='reorient')

# Bias Field Correction
N4_BFC = Node(ants.N4BiasFieldCorrection(dimension=3), name='N4_BFC')

# Smooth - image smoothing
smooth = Node(Smooth(), name="smooth")
smooth.iterables = ("fwhm", fwhm)


# coregistration Workflow
def coreg_workflow():

    # BET - Skull-stripping
    bet_anat = Node(fsl.BET(frac=0.2,
                       robust=True,
                       vertical_gradient=0.7,
                       output_type='NIFTI_GZ'),
               name="bet_anat")

    # FAST - tissue Segmentation
    segmentation = Node(fsl.FAST(no_bias=True, probability_maps=True, output_type='NIFTI_GZ'), name='segmentation')

    # Select WM segmentation file from segmentation output
    def get_wm(files):
        return files[-1]

    # Threshold - Threshold WM probability image
    threshold = Node(fsl.Threshold(thresh=0.5,
                                   args='-bin',
                                   output_type='NIFTI_GZ'),
                    name="threshold")

    # FLIRT - pre-alignment of all other images to anatomical images
    coreg_pre = Node(fsl.FLIRT(dof=6, output_type='NIFTI_GZ'),
                     name="coreg_pre")

    # FLIRT - coregistration with mutual information
    coreg_mi = Node(fsl.FLIRT(bins=640,
                              cost_func='mutualinfo',
                              interp='spline',
                              searchr_x=[-180, 180],
                              searchr_y=[-180, 180],
                              searchr_z=[-180,180],
                              dof=6,
                              output_type='NIFTI_GZ'),
                     name="coreg_mi")

    # Apply coregistration warp to other images
    applywarp = Node(fsl.FLIRT(interp='spline',
                               apply_xfm=True,
                               output_type='NIFTI'),
                     name="applywarp")

    # Create a coregistration workflow
    coregwf = Workflow(name='coregwf')
    coregwf.base_dir = opj(experiment_dir, working_dir)

    # Connect all components of the coregistration workflow
    coregwf.connect([(bet_anat, segmentation, [('out_file', 'in_files')]),
                     (segmentation, threshold, [(('partial_volume_files', get_wm),
                                                 'in_file')]),
                     (bet_anat, coreg_pre, [('out_file', 'reference')]),
                     (threshold, coreg_mi, [('out_file', 'wm_seg')]),
                     (coreg_pre, coreg_mi, [('out_matrix_file', 'in_matrix_file')]),
                     (coreg_mi, applywarp, [('out_matrix_file', 'in_matrix_file')]),
                     (bet_anat, applywarp, [('out_file', 'reference')]),
                     ])
    return coregwf


# specify input and output stream

# Infosource - a function free node to iterate over the list of subject names

infosource = Node(IdentityInterface(fields=['subject_id', 'task_name']),
                  name="infosource")
infosource.iterables = [('subject_id', patient_list),
                        ('task_name', task_list)]

# SelectFiles - to grab the data
anat_file = opj('NIFTI_Renamed_test', '{subject_id}', 'T1.nii.gz')
extra_file = opj('NIFTI_Renamed_test', '{subject_id}',
                '{task_name}.nii.gz')

templates = {'anat': anat_file,
             'extra': extra_file}

selectfiles = Node(SelectFiles(templates,
                               base_directory=working_dir),
                   name="selectfiles")

# Datasink - creates output folder for important outputs
datasink = Node(DataSink(base_directory=experiment_dir,
                         container=output_dir),
                name="datasink")


## Use the following DataSink output substitutions
substitutions = [('_subject_id_', 'sub-'),
                 ('_task_name_', '/task-'),
                 ('_fwhm_', 'fwhm-'),
                 ('_roi', ''),
                 ('_mcf', ''),
                 ('_st', ''),
                 ('_flirt', ''),
                 ('.nii.par', '.par'),
                 ]
subjFolders = [('fwhm-%s/' % f, 'fwhm-%s_' % f) for f in fwhm]
substitutions.extend(subjFolders)
datasink.inputs.substitutions = substitutions


# build Workflow

coregwf = coreg_workflow()

# Create a preprocessing workflow
preproc = Workflow(name='preproc')
preproc.base_dir = opj(experiment_dir, working_dir)

# Connect all components of the preprocessing workflow
preproc.connect([(infosource, selectfiles, [('subject_id', 'subject_id'),
                                            ('task_name', 'task_name')]),
                 (selectfiles, reorient, [('func', 'in_file')]),
                 (reorient, N4_BFC, [('roi_file', 'in_file')]),

                 (selectfiles, coregwf, [('anat', 'bet_anat.in_file'),
                                         ('anat', 'coreg_mi.reference')]),
                 (N4_BFC, coregwf, [('anat', 'bet_anat.in_file'),
                                    ('anat', 'coreg_mi.reference')]),

                 (coregwf, smooth, [('applywarp.out_file', 'in_files')]),

                 (N4_BFC, datasink, [('par_file', 'preproc.@par')]),
                 (smooth, datasink, [('smoothed_files', 'preproc.@smooth')]),
                 (coregwf, datasink, [('applywarp.out_file', 'preproc.@mat_file')]),
                 (coregwf, datasink, [('coreg_mi.out_matrix_file', 'preproc.@mat_file'),
                                      ('bet_anat.out_file', 'preproc.@brain')]),
                 ])