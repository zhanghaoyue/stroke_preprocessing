import lib.workflow_traditional as wt
from lib.dicom2nifti import dcm_to_dcm_compress, dcm_to_nifti
import lib.copy_files as copy_files
import lib.rapid_conversion as rc
import csv
import pandas as pd
import os
from joblib import Parallel, delayed


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
    ids = pd.read_csv('/home/harryzhang/PACS_QUERY/image_dict.csv', header=None)
    # original 461 patients, data in series level (each patient folder contains series folder)
    # dicom_split_dir = "/mnt/sharedJH/DataDump_MRN_series"
    # new cases added in this folder, data in study level (each patient folder contains all series)
    dicom_new_dir = "/mnt/sharedJH/DataDump_NewCases_Batch2"
    # if decompress first, use this dicom folder
    transcode_dicom_dir = "/mnt/sharedJH/Dicom_transcoded"
    nifti_input_dir = "/mnt/sharedJH/NIFTI_Images"
    nifti_output_dir = '/mnt/sharedJH/NIFTI_Renamed'
    nifti_output_dir_new = '/mnt/sharedJH/NIFTI_Renamed_NewCases_Batch2'
    atlas_folder = "/mnt/sharedJH/atlas"
    output_folder = '/mnt/sharedJH/Registered_output'
    output_folder_new = '/mnt/sharedJH/Registered_output_NewCases_Batch2'

    # # transcode first or if rapid map has issue, do dcm2dcm from dcm4che first, choose between dcm2dcm or dcmdjpeg
    # dcm_to_dcm_compress(dicom_new_dir, transcode_dicom_dir, 'study', 'dcm2dcm')
    #
    # # if true, series level, if false, study level
    # dcm_to_nifti(transcode_dicom_dir, nifti_input_dir, False, 'dcm2niix')
    #
    # copy_files.rename_and_copy(ids, nifti_input_dir, nifti_output_dir_new)
    #
    # # unique_cases = copy_files.check_unique_cases(nifti_output_dir_new)
    # #
    # # with open('/home/harryzhang/Desktop/unique_cases.csv', 'w') as myfile:
    # #     wr = csv.writer(myfile, quoting=csv.QUOTE_ALL)
    # #     wr.writerow(unique_cases)
    #
    # rc.rapid_map_conversion(nifti_output_dir_new)

    modality_list = ['DWI_b1000', 'FLAIR', 'ADC', 'TMAX', 'TTP', 'CBF', 'CBV', 'MTT']

    # if test or check for error cases, don't use parallel
    parallel = True

    def complete_reg_steps(p):
        if not os.path.isdir(os.path.join(output_folder_new, p)):
            os.makedirs(os.path.join(output_folder_new, p))

        wt.preprocess(nifti_output_dir_new, p, atlas_folder, output_folder_new)

        for mo in modality_list:
            wt.coregister(nifti_output_dir_new, p, mo, atlas_folder, output_folder_new)


    if not parallel:
        for patient in os.listdir(nifti_output_dir_new):

            if not os.path.isdir(os.path.join(output_folder_new, patient)):
                os.makedirs(os.path.join(output_folder_new, patient))

            wt.preprocess(nifti_output_dir_new, patient, atlas_folder, output_folder_new)

            for m in modality_list:
                wt.coregister(nifti_output_dir_new, patient, m, atlas_folder, output_folder_new)
    else:
        results = Parallel(n_jobs=8)(delayed(complete_reg_steps)(i) for i in os.listdir(nifti_output_dir_new))
