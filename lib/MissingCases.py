import os
import pydicom
import pandas as pd
import numpy as np

out_base_dir = '/media/harryzhang/VolumeWD/DataDump_MRN_series'
out_query_dir = '/media/harryzhang/VolumeWD/QueryUID'
dcm_file = pd.read_csv('/home/harryzhang/PACS_QUERY/DICOM_Query_0806.csv', dtype=str)
dcm_array = np.array(dcm_file)


missing_cases = pd.DataFrame(columns=['patient', 'series', 'series_UID'])

for patient in os.listdir(out_base_dir):
    patient_dir = os.path.join(out_base_dir, patient)
    for series_folder in os.listdir(patient_dir):
        series_dir = os.path.join(patient_dir, series_folder)
        for series_file in os.listdir(series_dir):
            if series_file.endswith('.log'):
                series_file_path = os.path.join(series_dir, series_file)
                os.remove(series_file_path)
        if not os.listdir(series_dir):
            accession = dcm_array[np.where(dcm_array == patient)[0][0]][2]
            if accession == '44086115':
                accession = '44086408'
            patient_query_series = os.path.join(out_query_dir, patient, 'AccessionNumber-' + accession, series_folder)
            series = pydicom.dcmread(patient_query_series, force=True)
            missing_cases = missing_cases.append({'patient': patient, 'series': series_folder, 'accession': accession,
                                                  'series_UID': series.SeriesInstanceUID}, ignore_index=True)


missing_cases.to_csv('/home/harryzhang/Desktop/missing_cases.csv', index=False)
