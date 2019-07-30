import os
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

"""
Step 0
Read Dicom header and re-orgnize data

"""


def file_loader(patients_dir):
    """Explore patient dicom folders and store dcm filenames
    in a dictionary of patient.

    Args:
        patients_dir (str): directory that contains patients folder

    Returns:
        dictDCM (dict): patient as key, list of dicom files for each patients

    example:
    dicom_dir = '/home/harryzhang/Desktop/DICOM_Images/'
    test_dict = file_loader(dicom_dir)
    """

    # create an empty dictionary
    # for each patient, it contains list of all dicom files
    dict_dcm = {}

    for patient in os.listdir(patients_dir):
        path_dicom = os.path.join(patients_dir, patient)
        lst_files_dcm = []  # create an empty list
        for dirName, subdirList, fileList in os.walk(path_dicom):
            for filename in fileList:
                lst_files_dcm.append(os.path.join(dirName, filename))
        dict_dcm[patient] = lst_files_dcm

    return dict_dcm


def study_to_sequence(patients_dir, output_dir):
    """Create subfolder of patient by sequence, then copy to the new subfolder

    Args:
        patients_dir (str): directory that contains patients folder
        output_dir (str): output big folder
    Returns:
        NA

    example:
    dicom_dir = '/home/harryzhang/Desktop/DICOM_Images/'
    dicom_split_dir = '/home/harryzhang/Desktop/DICOM_split/'
    study_to_sequence(dicom_dir, dicom_split_dir)
    """

    for patient in os.listdir(patients_dir):
        # make the directory in clean directory if it doesnt work.
        pt_dir = os.path.join(patients_dir, patient)
        out_dir = os.path.join(output_dir, patient)
        if not os.path.exists(out_dir):
            os.makedirs(out_dir)
        for f in os.listdir(pt_dir):

            ds = pydicom.dcmread(pt_dir + '/' + f)
            series_name = ds['SeriesDescription'].value
            series_dir = os.path.join(out_dir, series_name)

            if not os.path.exists(series_dir):
                os.makedirs(series_dir)
            os.rename(pt_dir + '/' + f, os.path.join(series_dir, f))


"""
Step 1
Dicom to Nifti format conversion

Tool used: Dcm2niix (https://github.com/rordenlab/dcm2niix)
install dcm2niix first, then use nipype wrapper instead of cmd

sample code here shows only T2, DWI and Perfusion conversion
adjust source_dir for other modalities
@param:
compression: Gz compression level, 1=fastest, 9=smallest
generated cmd line:
'dcm2niix -b y -z y -5 -x n -t n -m n -o -s n -v n source_dir' 
"""


def dcm_to_nifti(dicom_dir, nifti_dir, split=True, tool_used='dcm2niix'):

    for patient in os.listdir(dicom_dir):

        path_dicom = os.path.join(dicom_dir, patient)
        path_nifti = os.path.join(nifti_dir, patient)
        # make subfolder for each patient
        if not os.path.exists(path_nifti):
            os.makedirs(path_nifti)
        if not split:
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