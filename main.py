import lib.workflow_traditional as wt
from lib.dicom2nifti import dcm_to_dcm_compress, dcm_to_nifti
import lib.copy_files as copy_files
import lib.rapid_conversion as rc
import csv
import pandas as pd
import os
from joblib import Parallel, delayed
import lib.dwi_to_adc as da
import shutil


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

    # paths
    # maps sequence names dictionary
    ids = pd.read_csv('/home/jennifer/Projects/Stroke/Data/image_dict.csv', header=None)
    # original 461 patients, data in series level (each patient folder contains series folder)
    # dicom_split_dir = "/mnt/sharedJH/DataDump_MRN_series"
    # new cases added in this folder, data in study level (each patient folder contains all series)
    # if decompress first, use this dicom folder
    transcode_dicom_dir = "/mnt/sharedfolder/data_process_May2020/DataDump_NewCases_Batch2"
    nifti_input_dir = "/mnt/sharedfolder/data_process_May2020/NIFTI_Images"
    nifti_output_dir = '/mnt/sharedfolder/NIFTI_Renamed'
    atlas_folder = "/mnt/sharedfolder/atlas"
    output_folder = '/mnt/sharedfolder/Registered_output_ds'

    # # transcode first or if rapid map has issue, do dcm2dcm from dcm4che first, choose between dcm2dcm or dcmdjpeg
    # dcm_to_dcm_compress(dicom_new_dir, transcode_dicom_dir, 'study', 'dcm2dcm')
    #
    # # if true, series level, if false, study level
    # dcm_to_nifti(transcode_dicom_dir, nifti_input_dir, False, 'dcm2niix')
    #
    # copy_files.rename_and_copy(ids, nifti_input_dir, nifti_output_dir)
    #
    # # unique_cases = copy_files.check_unique_cases(nifti_output_dir_new)
    # #
    # # with open('/home/harryzhang/Desktop/unique_cases.csv', 'w') as myfile:
    # #     wr = csv.writer(myfile, quoting=csv.QUOTE_ALL)
    # #     wr.writerow(unique_cases)
    #
    # rc.rapid_map_conversion(nifti_output_dir)

    # modality_list = ['DWI_b1000', 'FLAIR', 'ADC', 'TMAX', 'TTP', 'CBF', 'CBV', 'MTT']

    ##### DWI_500 post-hoc processing

    # modality_list = ['DWI_b500']
    # for patient in os.listdir(output_folder):
    #     if len(os.listdir(os.path.join(output_folder, patient))) !=0:
    #         for mo in modality_list:
    #             wt.coregister(nifti_output_dir, patient, mo, atlas_folder, output_folder)

    ##### ADC generation - merging
    # dwi_list = ['DWI_b0.nii.gz','DWI_b500.nii.gz','DWI_b1000.nii.gz']
    #
    # for patient in os.listdir(output_folder):
    #     if os.path.exists(os.path.join(output_folder, patient, 'DWI_b500.nii.gz')):
    #         if len(os.listdir(os.path.join(output_folder, patient))) != 0:
    #             da.merge_files(output_folder, patient, dwi_list)
    #     else:
    #         print(patient)
    #generation
    for patient in os.listdir(output_folder):
        print(patient)
        if os.path.exists(os.path.join(output_folder, patient, 'DWI_b500.nii.gz')):
            #TODO: move these (put in another part of the code) this was done incorrectly in copy_files.py
            if len(os.listdir(os.path.join(output_folder, patient))) != 0:
                shutil.copy2(os.path.join(nifti_output_dir, patient, 'DWI.bval'),
                             os.path.join(output_folder, patient, 'DWI.bval'))
                shutil.copy2(os.path.join(nifti_output_dir, patient, 'DWI.bvec'),
                             os.path.join(output_folder, patient, 'DWI.bvec'))
                da.generate_adc(output_folder, patient)
        else:
            print(patient)
    ##### combine the fsl
    # # if test or check for error cases, don't use parallel
    # parallel = True
    #
    # def complete_reg_steps(p):
    #     if not os.path.isdir(os.path.join(output_folder, p)):
    #         os.makedirs(os.path.join(output_folder, p))
    #
    #     wt.preprocess(nifti_output_dir, p, atlas_folder, output_folder)
    #
    #     for mo in modality_list:
    #         wt.coregister(nifti_output_dir, p, mo, atlas_folder, output_folder)
    #
    #
    # if not parallel:
    #     for patient in os.listdir(nifti_output_dir):
    #         if patient == '570251':
    #             pass
    #         else:
    #             if not os.path.isdir(os.path.join(output_folder, patient)):
    #                 os.makedirs(os.path.join(output_folder, patient))
    #
    #             wt.preprocess(nifti_output_dir, patient, atlas_folder, output_folder)
    #
    #             for m in modality_list:
    #                 wt.coregister(nifti_output_dir, patient, m, atlas_folder, output_folder)
    # else:
    #     results = Parallel(n_jobs=8)(delayed(complete_reg_steps)(i) for i in os.listdir(nifti_output_dir))
