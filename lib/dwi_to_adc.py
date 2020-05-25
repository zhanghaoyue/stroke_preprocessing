import os
from nipype.interfaces.fsl import Merge, DTIFit
from nipype.interfaces import fsl
import shutil
import nibabel as nib
import numpy as np

def merge_files(output_dir, subject, file_list):
    merger = Merge()
    merger.inputs.in_files = [os.path.join(output_dir, subject, f) for f in file_list]
    merger.inputs.dimension = 't'
    merger.inputs.output_type = 'NIFTI_GZ'
    merger.inputs.merged_file = os.path.join(output_dir, subject, 'DWI_concat.nii.gz')
    result = merger.run()
    print('Merging complete')
    return None

def generate_adc(output_dir, subject):
    pt_dir = os.path.join(output_dir, subject)
    dti = DTIFit()
    dti.inputs.dwi = os.path.join(pt_dir, 'DWI_concat.nii.gz')
    dti.inputs.bvecs = os.path.join(pt_dir, 'DWI.bvec')
    dti.inputs.bvals = os.path.join(pt_dir, 'DWI.bval')
    dti.inputs.base_name = 'testTP'
    dti.inputs.mask = os.path.join(pt_dir, 'DWI_b0_mask.nii.gz')
    dti.run()
    #to run this, has to be in project directory
    file = nib.load('/home/jennifer/PycharmProjects/stroke_preprocessing/testTP_MD.nii.gz')
    file_array = file.get_data()
    #normalize the data
    normalized = (file_array - np.min(file_array)) / (np.max(file_array) - np.min(file_array))
    #load the mask
    mask = nib.load(os.path.join(pt_dir,'DWI_b0_mask.nii.gz'))
    mask_array = mask.get_data()
    #apply the mask
    masked_adc = normalized * mask_array
    #generate adc image and save
    adc_img = nib.Nifti1Image(masked_adc, file.affine, file.header)
    nib.save(adc_img, os.path.join(pt_dir, 'ADC_masked.nii.gz'))



    print(subject)
    return None
