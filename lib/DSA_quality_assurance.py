import os
from shutil import copyfile
import pydicom
from nipype.interfaces.dcm2nii import Dcm2niix, Dcm2nii
import subprocess
from lib.dicom2nifti import dcm_to_dcm_compress, dcm_to_nifti

#


if __name__ == '__main__':
    dicom_split_dir = "/media/harryzhang/DataWD/ir_pacs_0506"
    transcode_dicom_dir = "/media/harryzhang/DataWD/ir_dsa_transcoded"
    nifti_dir = "/media/harryzhang/DataWD/ir_dsa_nifti"
    # dcm_to_dcm_compress(dicom_split_dir, transcode_dicom_dir, 'series', "dcm2dcm")
    dcm_to_nifti(dicom_split_dir, nifti_dir, False, 'dcm2niix')
