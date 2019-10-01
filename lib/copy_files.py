# create dictionary
import shutil
import os
import numpy as np
import pandas as pd
import csv


def rename_and_copy(new_ids, input_dir, output_dir):

    new_dict = {}
    feature_list = ['patient', 'DWI', 'FLAIR', 'ADC', 'TTP', 'PWI', 'ADC_BS', 'ADC_Cor', 'DWI_BS', 'DWI_Cor',
                    'FLAIR', 'GBP', 'GRE', 'PBP', 'RAPID_All', 'RAPID_CBF', 'RAPID_CBF_C', 'RAPID_CBV', 'RAPID_CBV_C',
                    'RAPID_DWI', 'RAPID_MTT', 'RAPID_MTT_C', 'RAPID_PWI', 'RAPID_Summary', 'RAPID_TMAX', 'RAPID_TMAX_C',
                    'T1_Blade', 'T1_Cor', 'T1_Post', 'T1_Pre', 'T1_Post_Cor', 'T1_Pre_AuditoryCanal', 'T1_Pre_Cor',
                    'T2', 'T2_Cor', 'T2_Cor_AuditoryCanal', 'T2_Sag', 'T2_Sag_AuditoryCanal', 'TTP']
    patient_series_info = pd.DataFrame(columns=feature_list)

    new_ids = np.array(new_ids)
    for row in new_ids:
        new_dict[row[0]] = row[1]

    for patient in os.listdir(input_dir):
        print(patient)
        # make the directory in clean directory if it doesnt work.
        pt_dir = os.path.join(input_dir, patient)
        nii_output = os.path.join(output_dir, patient)
        if not os.path.isdir(nii_output):
            os.makedirs(nii_output)
        a = np.zeros(shape=(1, 39))
        patient_row = pd.DataFrame(a, columns=feature_list)
        patient_row.iloc[0, patient_row.columns.get_loc('patient')] = patient
        for nifti_file in os.listdir(pt_dir):
            # if file is the first version AND nifti
            if nifti_file.endswith('_i00001.nii.gz'):
                nifti_name = nifti_file[:-14]
                if nifti_name in new_dict.keys():
                    patient_row.iloc[0, patient_row.columns.get_loc(new_dict[nifti_name])] = 1
                    shutil.copy(os.path.join(pt_dir, nifti_file), os.path.join(nii_output,
                                                                               new_dict[nifti_name]+'.nii.gz'))
            elif nifti_file.endswith('.nii.gz'):
                nifti_name = nifti_file[:-7]
                if nifti_name in new_dict.keys():
                    patient_row.iloc[0, patient_row.columns.get_loc(new_dict[nifti_name])] = 1
                    shutil.copy(os.path.join(pt_dir, nifti_file), os.path.join(nii_output,
                                                                               new_dict[nifti_name]+'.nii.gz'))
            print(patient_row)
        patient_series_info = patient_series_info.append(patient_row, ignore_index=True)

    patient_series_info.to_csv('/home/harryzhang/Desktop/patient_series_info.csv', index=False)


# check unique cases
def check_unique_cases(clean_dir):
    list_of_series = []
    for p in os.listdir(clean_dir):
        pt_dir = os.path.join(clean_dir, p)
        for nifti_file in os.listdir(pt_dir):
            if nifti_file.endswith('_i00001.nii.gz'):
                if nifti_file[:-14] not in list_of_series:
                    list_of_series.append(nifti_file[:-14])
            elif nifti_file.endswith('.nii.gz'):
                if nifti_file[:-7] not in list_of_series:
                    list_of_series.append(nifti_file[:-7])
    return list_of_series


if __name__ == '__main__':
    ids = pd.read_csv('/home/harryzhang/PACS_QUERY/image_dict.csv', header=None)
    nifti_input_dir = '/media/harryzhang/VolumeWD/NIFTI_Images'
    nifti_output_dir = '/media/harryzhang/VolumeWD/NIFTI_Renamed'

    rename_and_copy(ids, nifti_input_dir, nifti_output_dir)
    unique_cases = check_unique_cases(nifti_input_dir)
    with open('/home/harryzhang/Desktop/unique_cases.csv', 'w') as myfile:
        wr = csv.writer(myfile, quoting=csv.QUOTE_ALL)
        wr.writerow(unique_cases)


