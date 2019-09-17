from nipype.interfaces import fsl
from nipype.interfaces.ants import N4BiasFieldCorrection
import os


def preprocess(data_dir, subject, atlas_dir, output_dir):
    btr1 = fsl.BET()
    btr1.inputs.in_file = os.path.join(data_dir, subject, 'DWI_b0.nii.gz')
    btr1.inputs.robust = True
    btr1.inputs.out_file = 'BET_B0_first_run.nii.gz'
    res = btr1.run()
    print('BET pre-stripping...')

    flt = fsl.FLIRT(bins=640, cost_func='mutualinfo', interp='spline',
                    searchr_x=[-180, 180], searchr_y=[-180, 180], searchr_z=[-180, 180], dof=6)
    flt.inputs.in_file = 'BET_B0_first_run.nii.gz'
    flt.inputs.reference = atlas_dir + '/mni_icbm152_nlin_asym_09a/mni_icbm152_t2_tal_nlin_asym_09a.nii'
    flt.inputs.out_file = 'BET_B0_first_run_r.nii.gz'
    flt.inputs.out_matrix_file = 'B0_r_transform.mat'
    res = flt.run()
    print('FSL registration...')

    btr2 = fsl.BET()
    btr2.inputs.in_file = 'BET_B0_first_run_r.nii.gz'
    btr2.inputs.robust = True
    btr2.inputs.frac = 0.5
    btr2.inputs.mask = True
    btr2.inputs.out_file = 'BET_B0_second_run_r.nii.gz'
    res = btr2.run()
    print('BET skull stripping...')

    n4 = N4BiasFieldCorrection()
    n4.inputs.dimension = 3
    n4.inputs.input_image = 'BET_B0_second_run_r.nii.gz'
    n4.inputs.bspline_fitting_distance = 300
    n4.inputs.shrink_factor = 3
    n4.inputs.n_iterations = [50, 50, 30, 20]
    n4.inputs.output_image = os.path.join(output_dir, subject, 'B0_BET_ANTS.nii.gz')
    res = n4.run()
    print('N4 bias field correction done...')
    print('.........................')
    print('patient %s done' % subject)


def coregister(data_dir, subject, modality, output_dir):
    # register first with the modality
    applyxfm = fsl.preprocess.ApplyXFM()
    applyxfm.inputs.in_file = os.path.join(data_dir, subject, modality + '.nii.gz')
    applyxfm.inputs.in_matrix_file = 'B0_r_transform.mat'
    applyxfm.inputs.out_file = modality + '_r.nii.gz'
    applyxfm.inputs.reference = os.path.join(output_dir, subject, 'B0_BET_ANTS.nii.gz')
    applyxfm.inputs.apply_xfm = True
    result = applyxfm.run()
    print('co-registration done...')

    # apply skull stripping map
    am = fsl.maths.ApplyMask()
    am.inputs.in_file = modality + '_r.nii.gz'
    am.inputs.mask_file = 'BET_B0_second_run_r_mask.nii.gz'
    am.inputs.out_file = os.path.join(output_dir, subject, modality + '_r.nii.gz')
    res = am.run()
    print('apply skull stripping mask done...')


if __name__ == '__main__':
    atlas_folder = "/mnt/sharedJH/atlas"
    data_test_folder = '/media/harryzhang/VolumeWD/NIFTI_Renamed_test'
    output_folder = '/media/harryzhang/VolumeWD/output_test'

    subject_list = ['540335', '540410', '540449', '570143', '570252', '570255', '570364']

    modality_list = ['DWI_b1000', 'FLAIR', 'ADC', 'RAPID_CBF', 'RAPID_CBV', 'RAPID_MTT', 'RAPID_TMAX', 'TTP']

    for patient in os.listdir(data_test_folder):

        preprocess(data_test_folder, patient, atlas_folder, output_folder)

        for m in modality_list:
            coregister(data_test_folder, patient, m, output_folder)


