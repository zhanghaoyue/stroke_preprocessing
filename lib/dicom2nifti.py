import os
from shutil import copyfile
import pydicom
from nipype.interfaces.dcm2nii import Dcm2niix, Dcm2nii
import subprocess

"""
Step 0
Read Dicom folder and store info in dictionary for future use

"""


def file_loader(patients_dir):
    """Explore patient dicom folders and store dcm filenames
    in a dictionary of patient.

    Args:
        patients_dir (str): directory that contains patients folder

    Returns:
        dictDCM (dict): patient as key, list of dicom files for each patients

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


# test_dict = file_loader(dicom_dir)


def study_to_sequence(patient_dir, output_dir):
    for patient in os.listdir(patient_dir):

        pt_dir = os.path.join(patient_dir, patient)
        out_dir = os.path.join(output_dir, patient)
        if not os.path.exists(out_dir):
            os.makedirs(out_dir)
        for f in os.listdir(pt_dir):

            ds = pydicom.dcmread(pt_dir + '/' + f)
            series_name = ds['SeriesDescription'].value.replace(" ", "_").replace("<", "").replace(">", "")
            series_dir = os.path.join(out_dir, series_name)

            if not os.path.exists(series_dir):
                os.makedirs(series_dir)
            if not os.path.exists(os.path.join(series_dir, f)):
                copyfile(pt_dir + '/' + f, os.path.join(series_dir, f))

# study_to_sequence(dicom_dir, dicom_split_dir)


"""
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
                    try:
                        subprocess.call('/home/harryzhang/toolbox/dcm2niix/console/dcm2niix -m y -5 -f %%d -o %s %s' %
                                        (path_nifti, path_dicom + '/'+s), shell=True)
                    except:
                        pass
                elif tool_used == 'dcm2nii':
                    converter = Dcm2nii()
                    converter.inputs.source_dir = path_dicom + '/' + s
                    converter.inputs.gzip_output = True
                    converter.inputs.output_dir = path_nifti
                    converter.run()
                else:
                    raise Warning("tool used does not exist, please enter dcm2nii or dcm2niix")


'''
Convert dicom to different compression so that dcm2niix can be used
note that our data from GE use transfer syntax '2.16.840.1.113709.1.2.2' which is a non-standard one, most tools
do not work with this compression
'''


def dcm_to_dcm_compress(dicom_dir, dicom_out_dir, level='series'):
    for patient in os.listdir(dicom_dir):
        path_dicom = os.path.join(dicom_dir, patient)
        path_out = os.path.join(dicom_out_dir, patient)
        if not os.path.exists(path_out):
            os.makedirs(path_out)
        for s in os.listdir(path_dicom):
            path_series = os.path.join(path_dicom, s)
            path_series_out = os.path.join(path_out, s)
            if level == 'series':
                if not os.path.exists(path_series_out):
                    os.makedirs(path_series_out)
                for i in os.listdir(path_series):
                    dcm_in = os.path.join(path_series, i)
                    dcm_out = os.path.join(path_series_out, i)
                    subprocess.call('dcmdjpeg -v %s %s' % (dcm_in, dcm_out), shell=True)
            elif level == 'study':
                subprocess.call('dcmdjpeg -v %s %s' % (path_series, path_series_out), shell=True)
        print('patient %s finished' % patient)


if __name__ == '__main__':
    dicom_split_dir = "/media/harryzhang/VolumeWD/DataDump_MRN_series"
    nifti_dir = "/media/harryzhang/VolumeWD/NIFTI_Images"
    transcode_dicom_dir = "/media/harryzhang/VolumeWD/Dicom_transcoded"
    dcm_to_dcm_compress(dicom_split_dir, transcode_dicom_dir, 'series')
    dcm_to_nifti(transcode_dicom_dir, nifti_dir, True, 'dcm2niix')






