import os
import logging
import logging.handlers
from os.path import dirname, join
from shutil import copyfile
import numpy as np
import pydicom
import SimpleITK as sitk
import nibabel as nib
from nipype.interfaces import fsl
from nipype.interfaces.dcm2nii import Dcm2niix,Dcm2nii

dicom_dir = '/home/harryzhang/Desktop/DICOM_Images/'
dicom_split_dir = '/home/harryzhang/Desktop/DICOM_split/'
nifti_dir = '/home/harryzhang/Desktop/NIFTI_Images/'


def dcm_to_nifti(dicom_dir, nifti_dir, split=True, tool_used='dcm2niix'):
    for patient in os.listdir(dicom_dir):

        path_dicom = os.path.join(dicom_dir, patient)
        path_nifti = os.path.join(nifti_dir, patient)
        # make subfolder for each patient
        if not os.path.exists(path_nifti):
            os.makedirs(path_nifti)
        if split == False:
            if tool_used == 'dcm2niix':
                converter = Dcm2niix()
                converter.inputs.source_dir = path_dicom
                converter.inputs.compression = 5
                converter.inputs.merge_imgs = True
                converter.inputs.out_filename = '%d'
                converter.inputs.output_dir = path_nifti
                converter.run()
            elif tool_used == 'dcm2nii':
                converter = Dcm2nii()
                converter.inputs.source_dir = path_dicom
                converter.inputs.gzip_output = True
                converter.inputs.output_dir = path_nifti
                converter.run()
            else:
                raise Warning("tool used does not exist, please enter dcm2nii or dcm2niix")

        else:
            for s in os.listdir(path_dicom):
                if tool_used == 'dcm2niix':
                    converter = Dcm2niix()
                    converter.inputs.source_dir = path_dicom + '/' + s
                    converter.inputs.compression = 5
                    converter.inputs.merge_imgs = True
                    converter.inputs.out_filename = 'x_%d'
                    converter.inputs.output_dir = path_nifti
                    converter.run()
                elif tool_used == 'dcm2nii':
                    converter = Dcm2nii()
                    converter.inputs.source_dir = path_dicom + '/' + s
                    converter.inputs.gzip_output = True
                    converter.inputs.output_dir = path_nifti
                    converter.run()
                else:
                    raise Warning("tool used does not exist, please enter dcm2nii or dcm2niix")


#dcm_to_nifti(dicom_split_dir, nifti_dir, True, 'dcm2nii')
#dcm_to_nifti(dicom_split_dir, nifti_dir, True, 'dcm2niix')