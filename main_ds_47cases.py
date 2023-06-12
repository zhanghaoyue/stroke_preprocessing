import lib.workflow_traditional as wt
from lib.dicom2nifti import dcm_to_dcm_compress, dcm_to_nifti, study_to_sequence
import lib.copy_files as copy_files
import lib.rapid_conversion as rc
import csv
import pandas as pd
import os
from joblib import Parallel, delayed
import lib.dwi_to_adc as da
import shutil
import pydicom
from pydicom.tag import Tag

if __name__ == '__main__':
    """main function to run the whole process
    3 major steps:
    step 1: dicom pulling
    step 2: convert to nifti and reformat
    step 3: registration
    
    note:
        for dicom pulling, go to DICOM_Retrieval_dcm4che2 or DICOM_Retrieval_dcm4che5
        this step is now handle by Shawn
        check if there is missing cases for dicom pulling
        go to lib.MissingCases
        if encoding error, run dcm_to_dcm_compress first:
        dcm_to_dcm_compress(dicom_split_dir, transcode_dicom_dir, 'series')
    """

    #### paths
    nifti_output_dir = "/media/ericyang/DATA1/Stroke_Images/UCLA_MR_nifti_renamed"
    output_folder = "/media/ericyang/DATA1/stroke_multicenter"
    atlas_folder = "/home/jennifer/Projects/Stroke/Data/Atlases/vascular_territory_template"

    modality_list = ['FLAIR']

    # modality_list = ['GRE']
    ##### DWI_500 post-hoc processing

    # modality_list = ['DWI_b500']
    # for patient in os.listdir(output_folder):
    #     if len(os.listdir(os.path.join(output_folder, patient))) !=0:
    #         for mo in modality_list:
    #             wt.coregister(nifti_output_dir, patient, mo, atlas_folder, output_folder)


    #generation
    # for patient in os.listdir(output_folder):
    #     print(patient)
    #     if os.path.exists(os.path.join(output_folder, patient, 'DWI_b500.nii.gz')):
    #         #TODO: move these (put in another part of the code) this was done incorrectly in copy_files.py
    #         if len(os.listdir(os.path.join(output_folder, patient))) != 0:
    #             shutil.copy2(os.path.join(nifti_output_dir, patient, 'DWI.bval'),
    #                          os.path.join(output_folder, patient, 'DWI.bval'))
    #             shutil.copy2(os.path.join(nifti_output_dir, patient, 'DWI.bvec'),
    #                          os.path.join(output_folder, patient, 'DWI.bvec'))
    #             da.generate_adc(output_folder, patient)
    #     else:
    #         print(patient)
    ##### combine the fsl
    # if test or check for error cases, don't use parallel
    parallel = False
    #
    def complete_reg_steps(p):
        if p.startswith('47'):
            if not os.path.isdir(os.path.join(output_folder, p)):
                os.makedirs(os.path.join(output_folder, p))

            wt.preprocess(nifti_output_dir, p, atlas_folder, output_folder)

            for mo in modality_list:
                wt.coregister(nifti_output_dir, p, mo, atlas_folder, output_folder)


    if not parallel:
        for patient in os.listdir(nifti_output_dir):
            print(patient)
            # if patient.startswith('54') or patient.startswith('57'):
            if patient != '470007':
                print('skipping')
                pass
            else:
                if not os.path.isdir(os.path.join(output_folder, patient)):
                    os.makedirs(os.path.join(output_folder, patient))

                wt.preprocess(nifti_output_dir, patient, atlas_folder, output_folder)

                for m in modality_list:
                    wt.coregister(nifti_output_dir, patient, m, atlas_folder, output_folder)
    else:
        results = Parallel(n_jobs=8)(delayed(complete_reg_steps)(i) for i in os.listdir(nifti_output_dir))