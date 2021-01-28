import os
import shutil
import tempfile
from joblib import Parallel, delayed
import multiprocessing
import nibabel as nib
from lib.zscore_norm import zscore_normalize
from nipype.interfaces import fsl
from nipype.interfaces.ants import N4BiasFieldCorrection
import subprocess


def preprocess(data_dir, subject, atlas_dir, output_dir):
    with tempfile.TemporaryDirectory() as temp_dir:
        if not os.path.exists(os.path.join(output_dir, subject, 'DWI_b0.nii.gz')):
            if os.path.exists(os.path.join(data_dir, subject, 'DWI_b0.nii.gz')):
                # reorient to MNI standard direction
                reorient = fsl.utils.Reorient2Std()
                reorient.inputs.in_file = os.path.join(data_dir, subject, 'DWI_b0.nii.gz')
                reorient.inputs.out_file = os.path.join(temp_dir, 'DWI_b0_reorient.nii.gz')
                res = reorient.run()

                # robust fov to remove neck and lower head automatically
                rf = fsl.utils.RobustFOV()
                rf.inputs.in_file = os.path.join(temp_dir, 'DWI_b0_reorient.nii.gz')
                rf.inputs.out_roi = os.path.join(temp_dir, 'DWI_b0_RF.nii.gz')
                res = rf.run()

                # skull stripping first run
                btr1 = fsl.BET()
                btr1.inputs.in_file = os.path.join(temp_dir, 'DWI_b0_RF.nii.gz')
                btr1.inputs.robust = True
                btr1.inputs.frac = 0.5
                btr1.inputs.out_file = os.path.join(temp_dir, 'BET_b0_first_run.nii.gz')
                res = btr1.run()
                print('BET pre-stripping...')

                # N4 bias field correction
                n4 = N4BiasFieldCorrection()
                n4.inputs.dimension = 3
                n4.inputs.input_image = os.path.join(temp_dir, 'BET_b0_first_run.nii.gz')
                n4.inputs.bspline_fitting_distance = 300
                n4.inputs.shrink_factor = 3
                n4.inputs.n_iterations = [50, 50, 30, 20]
                n4.inputs.output_image = os.path.join(temp_dir, 'BET_b0_first_run_n4.nii.gz')
                res = n4.run()
                print('N4 Bias Field Correction running...')

                # registration of T2(DWI_b0) to MNI152
                flt = fsl.FLIRT(bins=640, cost_func='mutualinfo', interp='spline',
                                searchr_x=[-180, 180], searchr_y=[-180, 180], searchr_z=[-180, 180], dof=12)
                flt.inputs.in_file = os.path.join(temp_dir, 'BET_b0_first_run_n4.nii.gz')
                flt.inputs.reference = atlas_dir + '/mni152_downsample.nii.gz'
                flt.inputs.out_file = os.path.join(temp_dir, 'BET_b0_first_run_r.nii.gz')
                flt.inputs.out_matrix_file = os.path.join(output_dir, subject, 'B0_r_transform.mat')
                res = flt.run()
                print('FSL registration...')

                # second pass of BET skull stripping
                btr2 = fsl.BET()
                btr2.inputs.in_file = os.path.join(temp_dir, 'BET_b0_first_run_r.nii.gz')
                btr2.inputs.robust = True
                btr2.inputs.frac = 0.35
                btr2.inputs.mask = True
                btr2.inputs.out_file = os.path.join(output_dir, subject, 'DWI_b0.nii.gz')
                res = btr2.run()
                print('BET skull stripping...')

                # copy mask file to output folder
                shutil.copy2(os.path.join(output_dir, subject, 'DWI_b0_mask.nii.gz'),
                             os.path.join(temp_dir, 'DWI_b0_mask.nii.gz'))

                # z score normalization
                DWI_b0_path = os.path.join(output_dir, subject, 'DWI_b0.nii.gz')
                DWI_b0_final = nib.load(DWI_b0_path)
                DWI_b0_mask_path = os.path.join(temp_dir, 'DWI_b0_mask.nii.gz')
                mask = nib.load(DWI_b0_mask_path)
                DWI_b0_norm = zscore_normalize(DWI_b0_final, mask)
                nib.save(DWI_b0_norm, DWI_b0_path)

                print('.........................')
                print('patient %s registration done' % subject)
            else:
                pass
        else:
            pass

