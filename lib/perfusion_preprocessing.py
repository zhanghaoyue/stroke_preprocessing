import os
import shutil
import tempfile
from joblib import Parallel, delayed
import nibabel as nib
from lib.zscore_norm import zscore_normalize
from nipype.interfaces import fsl
from nipype.interfaces.ants import N4BiasFieldCorrection, ApplyTransforms, Registration
import subprocess


def preprocess(data_dir, subject, atlas_dir, output_dir):
    with tempfile.TemporaryDirectory() as temp_dir:
        if not os.path.exists(os.path.join(output_dir, subject, 'ANTS_FLAIR_r.nii.gz')):
            if os.path.exists(os.path.join(data_dir, subject, 'FLAIR.nii.gz')):
                # reorient to MNI standard direction
                reorient = fsl.utils.Reorient2Std()
                reorient.inputs.in_file = os.path.join(data_dir, subject, 'FLAIR.nii.gz')
                reorient.inputs.out_file = os.path.join(temp_dir, 'FLAIR_reorient.nii.gz')
                reorient.run()

                # robust fov to remove neck and lower head automatically
                rf = fsl.utils.RobustFOV()
                rf.inputs.in_file = os.path.join(temp_dir, 'FLAIR_reorient.nii.gz')
                rf.inputs.out_roi = os.path.join(temp_dir, 'FLAIR_RF.nii.gz')
                rf.run()

                # skull stripping first run
                print('BET pre-stripping...')
                btr1 = fsl.BET()
                btr1.inputs.in_file = os.path.join(temp_dir, 'FLAIR_RF.nii.gz')
                btr1.inputs.robust = True
                btr1.inputs.frac = 0.2
                btr1.inputs.out_file = os.path.join(temp_dir, 'FLAIR_RF.nii.gz')
                btr1.run()

                # N4 bias field correction
                print('N4 Bias Field Correction running...')
                input_image = os.path.join(temp_dir, 'FLAIR_RF.nii.gz')
                output_image = os.path.join(temp_dir, 'FLAIR_RF.nii.gz')
                subprocess.call('N4BiasFieldCorrection --bspline-fitting [ 300 ] -d 3 '
                                '--input-image %s --convergence [ 50x50x30x20 ] --output %s --shrink-factor 3'
                                % (input_image, output_image), shell=True)

                # registration of FLAIR to MNI152 FLAIR template
                print('ANTs registration...')
                reg = Registration()
                reg.inputs.fixed_image = atlas_dir + '/flair_test.nii.gz'
                reg.inputs.moving_image = os.path.join(temp_dir, 'FLAIR_RF.nii.gz')
                reg.inputs.output_transform_prefix = os.path.join(output_dir, subject, 'FLAIR_r_transform.mat')
                reg.inputs.winsorize_upper_quantile = 0.995
                reg.inputs.winsorize_lower_quantile = 0.005
                reg.inputs.transforms = ['Rigid', 'Affine', 'SyN']
                reg.inputs.transform_parameters = [(0.1,), (0.1,), (0.1, 3.0, 0.0)]
                reg.inputs.number_of_iterations = [[1000, 500, 250, 100], [1000, 500, 250, 100], [100, 70, 50, 20]]
                reg.inputs.dimension = 3
                reg.inputs.initial_moving_transform_com = 0
                reg.inputs.write_composite_transform = True
                reg.inputs.collapse_output_transforms = False
                reg.inputs.initialize_transforms_per_stage = False
                reg.inputs.metric = ['Mattes', 'Mattes', ['Mattes', 'CC']]
                reg.inputs.metric_weight = [1, 1, [.5, .5]]  # Default (value ignored currently by ANTs)
                reg.inputs.radius_or_number_of_bins = [32, 32, [32, 4]]
                reg.inputs.sampling_strategy = ['Random', 'Random', None]
                reg.inputs.sampling_percentage = [0.25, 0.25, [0.05, 0.10]]
                reg.inputs.convergence_threshold = [1e-6, 1.e-6, 1.e-6]
                reg.inputs.convergence_window_size = [10] * 3
                reg.inputs.smoothing_sigmas = [[3, 2, 1, 0], [3, 2, 1, 0], [3, 2, 1, 0]]
                reg.inputs.sigma_units = ['vox'] * 3
                reg.inputs.shrink_factors = [[8, 4, 2, 1], [8, 4, 2, 1], [8, 4, 2, 1]]
                reg.inputs.use_estimate_learning_rate_once = [True, True, True]
                reg.inputs.use_histogram_matching = [True, True, True]  # This is the default
                reg.inputs.output_warped_image = os.path.join(output_dir, subject, 'ANTS_FLAIR_r.nii.gz')
                reg.inputs.verbose = True
                reg.run()

                # second pass of BET skull stripping
                print('BET skull stripping...')
                btr2 = fsl.BET()
                btr2.inputs.in_file = os.path.join(output_dir, subject, 'ANTS_FLAIR_r.nii.gz')
                btr2.inputs.robust = True
                btr2.inputs.frac = 0.1
                btr2.inputs.mask = True
                btr2.inputs.out_file = os.path.join(output_dir, subject, 'ANTS_FLAIR_r.nii.gz')
                btr2.run()

                # copy mask file to output folder
                shutil.copy2(os.path.join(output_dir, subject, 'ANTS_FLAIR_r_mask.nii.gz'),
                             os.path.join(temp_dir, 'ANTS_FLAIR_r_mask.nii.gz'))

                # z score normalization
                FLAIR_path = os.path.join(output_dir, subject, 'ANTS_FLAIR_r.nii.gz')
                FLAIR_final = nib.load(FLAIR_path)
                FLAIR_mask_path = os.path.join(temp_dir, 'ANTS_FLAIR_r_mask.nii.gz')
                mask = nib.load(FLAIR_mask_path)
                FLAIR_norm = zscore_normalize(FLAIR_final, mask)
                nib.save(FLAIR_norm, FLAIR_path)

                print('.........................')
                print('patient %s registration done' % subject)
            else:
                pass
        else:
            pass


def coregister(data_dir, subject, modality, output_dir):
    print(subject)
    with tempfile.TemporaryDirectory() as temp_dir:
        # register with different modality
        if modality == 'PWI':
            if not os.path.exists(os.path.join(output_dir, subject, 'ANTS_PWI_r_final.nii.gz')):
                if os.path.exists(os.path.join(data_dir, subject, 'PWI.nii.gz')) and os.path.exists(os.path.join(
                        output_dir, subject, 'FLAIR_r_transform.matComposite.h5')):
                    print('PWI coregistration starts...')
                    reorient = fsl.utils.Reorient2Std()
                    reorient.inputs.in_file = os.path.join(data_dir, subject, 'PWI.nii.gz')
                    reorient.inputs.out_file = os.path.join(temp_dir, 'PWI_reorient.nii.gz')
                    res = reorient.run()

                    # apply registration transformation on PWI
                    at = ApplyTransforms()
                    at.inputs.dimension = 3
                    at.inputs.input_image_type = 3
                    at.inputs.input_image = os.path.join(data_dir, subject, 'PWI.nii.gz')
                    at.inputs.reference_image = os.path.join(output_dir, subject, 'ANTS_FLAIR_r.nii.gz')
                    at.inputs.output_image = os.path.join(output_dir, subject, 'ANTS_PWI_r.nii.gz')
                    at.inputs.interpolation = 'Linear'
                    at.inputs.default_value = 0
                    at.inputs.transforms = os.path.join(output_dir, subject, 'FLAIR_r_transform.matComposite.h5')
                    at.run()

                    # apply skull stripping mask
                    am = fsl.maths.ApplyMask()
                    am.inputs.in_file = os.path.join(output_dir, subject, 'ANTS_PWI_r.nii.gz')
                    am.inputs.mask_file = os.path.join(output_dir, subject, 'ANTS_FLAIR_r_mask.nii.gz')
                    am.inputs.out_file = os.path.join(output_dir, subject, 'ANTS_PWI_r_final.nii.gz')
                    am.run()
                else:
                    pass
            else:
                pass


if __name__ == '__main__':
    atlas_folder = "/data/haoyuezhang/data/vascular_territory_template"
    data_folder = '/data/haoyuezhang/data/stroke_MRI/stroke_MRI/Original_nifti'
    output_folder = '/data/haoyuezhang/data/stroke_MRI/stroke_perfusion'
    reference_dir = '/data/haoyuezhang/data/stroke_MRI/stroke_MRI/Registered_output_histmatch/570244/'
    in_histmatch_folder = '/data/haoyuezhang/data/stroke_MRI/stroke_MRI/Registered_output'
    out_histmatch_folder = '/data/haoyuezhang/data/stroke_MRI/stroke_MRI/Registered_output_histmatch'

    modality_list = ['PWI']
    modality_list_histmatch = ['FLAIR', 'PWI']

    parallel = False

    def complete_reg_steps(p):
        if not os.path.isdir(os.path.join(output_folder, p)):
            os.makedirs(os.path.join(output_folder, p))

        preprocess(data_folder, p, atlas_folder, output_folder)

        for mo in modality_list:
            coregister(data_folder, p, mo, output_folder)


    if not parallel:
        for patient in os.listdir(data_folder):

            if not os.path.isdir(os.path.join(output_folder, patient)):
                os.makedirs(os.path.join(output_folder, patient))

            preprocess(data_folder, patient, atlas_folder, output_folder)

            for m in modality_list:
                coregister(data_folder, patient, m, output_folder)
    else:
        results = Parallel(n_jobs=8)(delayed(complete_reg_steps)(i) for i in os.listdir(data_folder))