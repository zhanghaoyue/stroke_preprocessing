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
        if not os.path.exists(os.path.join(output_dir, subject, 'FLAIR_r.nii.gz')):
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
                btr1.inputs.frac = 0.1
                btr1.inputs.out_file = os.path.join(temp_dir, 'FLAIR_RF.nii.gz')
                btr1.run()

                # N4 bias field correction
                print('N4 Bias Field Correction running...')
                input_image = os.path.join(temp_dir, 'FLAIR_RF.nii.gz')
                output_image = os.path.join(temp_dir, 'FLAIR_RF.nii.gz')
                subprocess.call('/opt/ANTs/bin/N4BiasFieldCorrection --bspline-fitting [ 300 ] -d 3 '
                                '--input-image %s --convergence [ 50x50x30x20 ] --output %s --shrink-factor 3'
                                % (input_image, output_image), shell=True)

                # registration of FLAIR to MNI152 FLAIR template
                print('ANTs registration...')
                fixed_image = atlas_dir + '/flair_test.nii.gz'
                moving_image = os.path.join(temp_dir, 'FLAIR_RF.nii.gz')
                output_transform_prefix = 'transform_'
                output_warped_image = os.path.join(output_dir, subject, 'ANTS_FLAIR_r.nii.gz')
                subprocess.call('/opt/ANTs/bin/antsRegistration --collapse-output-transforms 0 --dimensionality 3 '
                                '--initialize-transforms-per-stage 0 -n 8'
                                '--interpolation Linear --output [%s, %s] '
                                '--transform Affine[ 2.0 ] --metric Mattes[%s, %s, 1, 64, Random, 0.05 ] '
                                '--metric CC[ %s, %s, 1, 32 ] '
                                '--convergence [ 1500x200, 1e-08, 20 ] --smoothing-sigmas 1.0x0.0vox '
                                '--shrink-factors 2x1 --use-estimate-learning-rate-once 1 --use-histogram-matching 1 '
                                '--winsorize-image-intensities [ 0.0, 1.0 ] --write-composite-transform 1 -v 1'
                                % (output_transform_prefix, output_warped_image, fixed_image, moving_image, fixed_image
                                   , moving_image),
                                shell=True)
                import pdb
                pdb.set_trace()
                # second pass of BET skull stripping
                print('BET skull stripping...')
                btr2 = fsl.BET()
                btr2.inputs.in_file = os.path.join(output_dir, subject, 'ANTS_FLAIR_r.nii.gz')
                btr2.inputs.robust = True
                btr2.inputs.frac = 0.2
                btr2.inputs.mask = True
                btr2.inputs.out_file = os.path.join(output_dir, subject, 'ANTS_FLAIR_r.nii.gz')
                btr2.run()

                # copy mask file to output folder
                shutil.copy2(os.path.join(output_dir, subject, 'FLAIR_r_mask.nii.gz'),
                             os.path.join(temp_dir, 'FLAIR_r_mask.nii.gz'))

                # z score normalization
                FLAIR_path = os.path.join(output_dir, subject, 'ANTS_FLAIR_r.nii.gz')
                FLAIR_final = nib.load(FLAIR_path)
                FLAIR_mask_path = os.path.join(temp_dir, 'FLAIR_r_mask.nii.gz')
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
            if not os.path.exists(os.path.join(output_dir, subject, 'PWI.nii.gz')):
                if os.path.exists(os.path.join(data_dir, subject, 'PWI.nii.gz')) and os.path.exists(os.path.join(
                        output_dir, subject, 'FLAIR_r_transform.mat')):
                    print('PWI coregistration starts...')
                    reorient = fsl.utils.Reorient2Std()
                    reorient.inputs.in_file = os.path.join(data_dir, subject, 'PWI.nii.gz')
                    reorient.inputs.out_file = os.path.join(temp_dir, 'PWI_reorient.nii.gz')
                    res = reorient.run()

                    # apply registration transformation on PWI
                    input_image = os.path.join(data_dir, subject, 'PWI.nii.gz')
                    reference_image = os.path.join(output_dir, subject, 'ANTS_FLAIR_r.nii.gz')
                    output_image = os.path.join(output_dir, subject, 'ANTS_PWI_r.nii.gz')
                    transforms = os.path.join(output_dir, subject, 'FLAIR_r_transform.matComposite.h5')
                    subprocess.call("/opt/ANTs/bin/antsApplyTransforms --default-value 0 --interpolation Linear "
                                    "--dimensionality 3 --input-image-type 3 --input %s --reference-image %s "
                                    "--output %s --transform [%s, 0 ]"
                                    % (input_image, reference_image, output_image, transforms), shell=True)

                    # apply skull stripping mask
                    am = fsl.maths.ApplyMask()
                    am.inputs.in_file = os.path.join(output_dir, subject, 'ANTS_PWI_r.nii.gz')
                    am.inputs.mask_file = os.path.join(output_dir, subject, 'FLAIR_r_mask.nii.gz')
                    am.inputs.out_file = os.path.join(output_dir, subject, 'ANTS_PWI_r_final.nii.gz')
                    am.run()
                else:
                    pass
            else:
                pass


if __name__ == '__main__':
    atlas_folder = "/media/bitlockermount/StrokeResearch/vascular_territory_template"
    data_folder = '/media/bitlockermount/StrokeResearch/stroke_MRI/stroke_MRI/Original_nifti'
    output_folder = '/media/bitlockermount/StrokeResearch/stroke_MRI/stroke_MRI/stroke_perfusion'
    reference_dir = '/media/bitlockermount/StrokeResearch/stroke_MRI/stroke_MRI/Registered_output_histmatch/570244/'
    in_histmatch_folder = '/media/bitlockermount/StrokeResearch/stroke_MRI/stroke_MRI/Registered_output'
    out_histmatch_folder = '/media/bitlockermount/StrokeResearch/stroke_MRI/stroke_MRI/Registered_output_histmatch'

    modality_list = ['FLAIR', 'PWI']
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