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
                flt.inputs.reference = atlas_dir + '/mni152_2009_256.nii.gz'
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


def coregister(data_dir, subject, modality, atlas_dir, output_dir):
    with tempfile.TemporaryDirectory() as temp_dir:

        # register with different modality
        if modality == 'DWI_b1000':
            if not os.path.exists(os.path.join(output_dir, subject, 'DWI_b1000.nii.gz')):
                if os.path.exists(os.path.join(data_dir, subject, 'DWI_b1000.nii.gz')):

                    reorient = fsl.utils.Reorient2Std()
                    reorient.inputs.in_file = os.path.join(data_dir, subject, 'DWI_b1000.nii.gz')
                    reorient.inputs.out_file = os.path.join(temp_dir, 'DWI_reorient.nii.gz')
                    res = reorient.run()

                    applyxfm = fsl.preprocess.ApplyXFM()
                    applyxfm.inputs.in_file = os.path.join(temp_dir, 'DWI_reorient.nii.gz')
                    applyxfm.inputs.in_matrix_file = os.path.join(output_dir, subject, 'B0_r_transform.mat')
                    applyxfm.inputs.out_file = os.path.join(temp_dir, 'DWI_r.nii.gz')
                    applyxfm.inputs.reference = os.path.join(output_dir, subject, 'DWI_b0.nii.gz')
                    applyxfm.inputs.apply_xfm = True
                    result = applyxfm.run()

                    # apply skull stripping mask
                    am = fsl.maths.ApplyMask()
                    am.inputs.in_file = os.path.join(temp_dir, 'DWI_r.nii.gz')
                    am.inputs.mask_file = os.path.join(output_dir, subject, 'DWI_b0_mask.nii.gz')
                    am.inputs.out_file = os.path.join(output_dir, subject, 'DWI_b1000.nii.gz')
                    res = am.run()

                    # z score normalization
                    DWI_b1000_path = os.path.join(output_dir, subject, 'DWI_b1000.nii.gz')
                    DWI_b1000_final = nib.load(DWI_b1000_path)
                    DWI_b0_mask_path = os.path.join(output_dir, subject, 'DWI_b0_mask.nii.gz')
                    mask = nib.load(DWI_b0_mask_path)
                    DWI_b1000_norm = zscore_normalize(DWI_b1000_final, mask)
                    nib.save(DWI_b1000_norm, DWI_b1000_path)

                    print('DWI coregistration done...')
                else:
                    pass
            else:
                pass
        elif modality == 'FLAIR':
            if not os.path.exists(os.path.join(output_dir, subject, 'FLAIR.nii.gz')):
                if os.path.exists(os.path.join(data_dir, subject, 'FLAIR.nii.gz')) and os.path.exists(os.path.join(
                        output_dir, subject, 'B0_r_transform.mat')):

                    reorient = fsl.utils.Reorient2Std()
                    reorient.inputs.in_file = os.path.join(data_dir, subject, 'FLAIR.nii.gz')
                    reorient.inputs.out_file = os.path.join(temp_dir, 'FLAIR_reorient.nii.gz')
                    res = reorient.run()

                    # register with FLAIR
                    flt = fsl.FLIRT(cost_func='mutualinfo', interp='spline',
                                    searchr_x=[-180, 180], searchr_y=[-180, 180], searchr_z=[-180, 180])
                    flt.inputs.in_file = os.path.join(temp_dir, 'FLAIR_reorient.nii.gz')
                    flt.inputs.reference = atlas_dir + '/mni152_2009_256.nii.gz'
                    flt.inputs.out_file = os.path.join(temp_dir, 'FLAIR_r.nii.gz')
                    flt.inputs.in_matrix_file = os.path.join(output_dir, subject, 'B0_r_transform.mat')
                    res = flt.run()

                    # apply skull stripping mask
                    am = fsl.maths.ApplyMask()
                    am.inputs.in_file = os.path.join(temp_dir, 'FLAIR_r.nii.gz')
                    am.inputs.mask_file = os.path.join(output_dir, subject, 'DWI_b0_mask.nii.gz')
                    am.inputs.out_file = os.path.join(output_dir, subject, 'FLAIR.nii.gz')
                    res = am.run()

                    # z score normalization
                    FLAIR_path = os.path.join(output_dir, subject, 'FLAIR.nii.gz')
                    FLAIR_final = nib.load(FLAIR_path)
                    DWI_b0_mask_path = os.path.join(output_dir, subject, 'DWI_b0_mask.nii.gz')
                    mask = nib.load(DWI_b0_mask_path)
                    FLAIR_norm = zscore_normalize(FLAIR_final, mask)
                    nib.save(FLAIR_norm, FLAIR_path)

                    print('FLAIR coregistration done...')
                else:
                    pass
            else:
                pass
        elif modality == 'ADC':
            if not os.path.exists(os.path.join(output_dir, subject, 'ADC.nii.gz')):
                if os.path.exists(os.path.join(data_dir, subject, 'ADC.nii.gz')) and os.path.exists(os.path.join(
                        output_dir, subject, 'B0_r_transform.mat')):
                    reorient = fsl.utils.Reorient2Std()
                    reorient.inputs.in_file = os.path.join(data_dir, subject, 'ADC.nii.gz')

                    reorient.inputs.out_file = os.path.join(output_dir, subject, 'ADC_reorient.nii.gz')
                    res = reorient.run()

                    # register with ADC
                    flt = fsl.FLIRT(cost_func='mutualinfo', interp='spline',
                                    searchr_x=[-180, 180], searchr_y=[-180, 180], searchr_z=[-180, 180], dof=6)
                    flt.inputs.in_file = os.path.join(output_dir, subject, 'ADC_reorient.nii.gz')
                    if os.path.exists(os.path.join(data_dir, subject, 'FLAIR.nii.gz')):
                        flt.inputs.reference = os.path.join(output_dir, subject, 'FLAIR.nii.gz')
                    else:
                        flt.inputs.reference = os.path.join(output_dir, subject, 'DWI_b0.nii.gz')
                    flt.inputs.out_file = os.path.join(temp_dir, 'ADC_r.nii.gz')
                    flt.inputs.in_matrix_file = os.path.join(output_dir, subject, 'B0_r_transform.mat')
                    res = flt.run()

                    # apply skull stripping mask
                    am = fsl.maths.ApplyMask()
                    am.inputs.in_file = os.path.join(temp_dir, 'ADC_r.nii.gz')
                    am.inputs.mask_file = os.path.join(output_dir, subject, 'DWI_b0_mask.nii.gz')
                    am.inputs.out_file = os.path.join(output_dir, subject, 'ADC.nii.gz')
                    res = am.run()

                    # z score normalization
                    ADC_path = os.path.join(output_dir, subject, 'ADC.nii.gz')
                    ADC_final = nib.load(ADC_path)
                    DWI_b0_mask_path = os.path.join(output_dir, subject, 'DWI_b0_mask.nii.gz')
                    mask = nib.load(DWI_b0_mask_path)
                    ADC_norm = zscore_normalize(ADC_final, mask)
                    nib.save(ADC_norm, ADC_path)

                    print('ADC coregistration done...')
                else:
                    pass
            else:
                pass
        elif modality == 'TMAX':
            if not os.path.exists(os.path.join(output_dir, subject, 'TMAX.nii.gz')):
                if os.path.exists(os.path.join(data_dir, subject, 'TMAX.nii.gz')) and os.path.exists(os.path.join(
                        output_dir, subject, 'B0_r_transform.mat')):
                    reorient = fsl.utils.Reorient2Std()
                    reorient.inputs.in_file = os.path.join(data_dir, subject, 'TMAX.nii.gz')
                    reorient.inputs.out_file = os.path.join(temp_dir, 'TMAX_reorient.nii.gz')
                    res = reorient.run()

                    # register with TMAX
                    flt = fsl.FLIRT(cost_func='mutualinfo', interp='spline', bins=640,
                                    searchr_x=[-180, 180], searchr_y=[-180, 180], searchr_z=[-180, 180], dof=6)
                    flt.inputs.in_file = os.path.join(temp_dir, 'TMAX_reorient.nii.gz')
                    if os.path.exists(os.path.join(data_dir, subject, 'FLAIR.nii.gz')):
                        flt.inputs.reference = os.path.join(output_dir, subject, 'FLAIR.nii.gz')
                    else:
                        flt.inputs.reference = os.path.join(output_dir, subject, 'DWI_b0.nii.gz')
                    flt.inputs.out_file = os.path.join(temp_dir, 'TMAX_r.nii.gz')
                    flt.inputs.in_matrix_file = os.path.join(output_dir, subject, 'B0_r_transform.mat')
                    res = flt.run()

                    # apply skull stripping mask
                    am = fsl.maths.ApplyMask()
                    am.inputs.in_file = os.path.join(temp_dir, 'TMAX_r.nii.gz')
                    am.inputs.mask_file = os.path.join(output_dir, subject, 'DWI_b0_mask.nii.gz')
                    am.inputs.out_file = os.path.join(output_dir, subject, 'TMAX.nii.gz')
                    res = am.run()

                    # z score normalization
                    TMAX_path = os.path.join(output_dir, subject, 'TMAX.nii.gz')
                    TMAX_final = nib.load(TMAX_path)
                    DWI_b0_mask_path = os.path.join(output_dir, subject, 'DWI_b0_mask.nii.gz')
                    mask = nib.load(DWI_b0_mask_path)
                    TMAX_norm = zscore_normalize(TMAX_final, mask)
                    nib.save(TMAX_norm, TMAX_path)

                    print('TMAX coregistration done...')
                else:
                    pass
            else:
                pass
        elif modality == 'TTP':
            if not os.path.exists(os.path.join(output_dir, subject, 'TTP.nii.gz')):
                if os.path.exists(os.path.join(data_dir, subject, 'TTP.nii.gz')) and os.path.exists(os.path.join(
                        output_dir, subject, 'B0_r_transform.mat')):
                    reorient = fsl.utils.Reorient2Std()
                    reorient.inputs.in_file = os.path.join(data_dir, subject, 'TTP.nii.gz')
                    reorient.inputs.out_file = os.path.join(temp_dir, 'TTP_reorient.nii.gz')
                    res = reorient.run()

                    # register with TTP
                    flt = fsl.FLIRT(cost_func='mutualinfo', interp='spline',
                                    searchr_x=[-180, 180], searchr_y=[-180, 180], searchr_z=[-180, 180], dof=6)
                    flt.inputs.in_file = os.path.join(temp_dir, 'TTP_reorient.nii.gz')
                    if os.path.exists(os.path.join(data_dir, subject, 'FLAIR.nii.gz')):
                        flt.inputs.reference = os.path.join(output_dir, subject, 'FLAIR.nii.gz')
                    else:
                        flt.inputs.reference = os.path.join(output_dir, subject, 'DWI_b0.nii.gz')
                    flt.inputs.out_file = os.path.join(temp_dir, 'TTP_r.nii.gz')
                    flt.inputs.in_matrix_file = os.path.join(output_dir, subject, 'B0_r_transform.mat')
                    res = flt.run()

                    # apply skull stripping mask
                    am = fsl.maths.ApplyMask()
                    am.inputs.in_file = os.path.join(temp_dir, 'TTP_r.nii.gz')
                    am.inputs.mask_file = os.path.join(output_dir, subject, 'DWI_b0_mask.nii.gz')
                    am.inputs.out_file = os.path.join(output_dir, subject, 'TTP.nii.gz')
                    res = am.run()

                    # z score normalization
                    TTP_path = os.path.join(output_dir, subject, 'TTP.nii.gz')
                    TTP_final = nib.load(TTP_path)
                    DWI_b0_mask_path = os.path.join(output_dir, subject, 'DWI_b0_mask.nii.gz')
                    mask = nib.load(DWI_b0_mask_path)
                    TTP_norm = zscore_normalize(TTP_final, mask)
                    nib.save(TTP_norm, TTP_path)

                    print('TTP coregistration done...')
                else:
                    pass
            else:
                pass
        elif modality == 'CBF':
            if not os.path.exists(os.path.join(output_dir, subject, 'CBF.nii.gz')):
                if os.path.exists(os.path.join(data_dir, subject, 'CBF.nii.gz')) and os.path.exists(os.path.join(
                        output_dir, subject, 'B0_r_transform.mat')):
                    reorient = fsl.utils.Reorient2Std()
                    reorient.inputs.in_file = os.path.join(data_dir, subject, 'CBF.nii.gz')
                    reorient.inputs.out_file = os.path.join(temp_dir, 'CBF_reorient.nii.gz')
                    res = reorient.run()

                    # register with CBF
                    flt = fsl.FLIRT(cost_func='mutualinfo', interp='spline',
                                    searchr_x=[-180, 180], searchr_y=[-180, 180], searchr_z=[-180, 180], dof=6)
                    flt.inputs.in_file = os.path.join(temp_dir, 'CBF_reorient.nii.gz')
                    if os.path.exists(os.path.join(data_dir, subject, 'FLAIR.nii.gz')):
                        flt.inputs.reference = os.path.join(output_dir, subject, 'FLAIR.nii.gz')
                    else:
                        flt.inputs.reference = os.path.join(output_dir, subject, 'DWI_b0.nii.gz')
                    flt.inputs.out_file = os.path.join(temp_dir, 'CBF_r.nii.gz')
                    flt.inputs.in_matrix_file = os.path.join(output_dir, subject, 'B0_r_transform.mat')
                    res = flt.run()

                    # apply skull stripping mask
                    am = fsl.maths.ApplyMask()
                    am.inputs.in_file = os.path.join(temp_dir, 'CBF_r.nii.gz')
                    am.inputs.mask_file = os.path.join(output_dir, subject, 'DWI_b0_mask.nii.gz')
                    am.inputs.out_file = os.path.join(output_dir, subject, 'CBF.nii.gz')
                    res = am.run()

                    # z score normalization
                    CBF_path = os.path.join(output_dir, subject, 'CBF.nii.gz')
                    CBF_final = nib.load(CBF_path)
                    DWI_b0_mask_path = os.path.join(output_dir, subject, 'DWI_b0_mask.nii.gz')
                    mask = nib.load(DWI_b0_mask_path)
                    CBF_norm = zscore_normalize(CBF_final, mask)
                    nib.save(CBF_norm, CBF_path)

                    print('CBF coregistration done...')
                else:
                    pass
            else:
                pass
        elif modality == 'CBV':
            if not os.path.exists(os.path.join(output_dir, subject, 'CBV.nii.gz')):
                if os.path.exists(os.path.join(data_dir, subject, 'CBV.nii.gz')) and os.path.exists(os.path.join(
                        output_dir, subject, 'B0_r_transform.mat')):
                    reorient = fsl.utils.Reorient2Std()
                    reorient.inputs.in_file = os.path.join(data_dir, subject, 'CBV.nii.gz')
                    reorient.inputs.out_file = os.path.join(temp_dir, 'CBV_reorient.nii.gz')
                    res = reorient.run()

                    # register with CBV
                    flt = fsl.FLIRT(cost_func='mutualinfo', interp='spline',
                                    searchr_x=[-180, 180], searchr_y=[-180, 180], searchr_z=[-180, 180], dof=6)
                    flt.inputs.in_file = os.path.join(temp_dir, 'CBV_reorient.nii.gz')
                    if os.path.exists(os.path.join(data_dir, subject, 'FLAIR.nii.gz')):
                        flt.inputs.reference = os.path.join(output_dir, subject, 'FLAIR.nii.gz')
                    else:
                        flt.inputs.reference = os.path.join(output_dir, subject, 'DWI_b0.nii.gz')
                    flt.inputs.out_file = os.path.join(temp_dir, 'CBV_r.nii.gz')
                    flt.inputs.in_matrix_file = os.path.join(output_dir, subject, 'B0_r_transform.mat')
                    res = flt.run()

                    # apply skull stripping mask
                    am = fsl.maths.ApplyMask()
                    am.inputs.in_file = os.path.join(temp_dir, 'CBV_r.nii.gz')
                    am.inputs.mask_file = os.path.join(output_dir, subject, 'DWI_b0_mask.nii.gz')
                    am.inputs.out_file = os.path.join(output_dir, subject, 'CBV.nii.gz')
                    res = am.run()

                    # z score normalization
                    CBV_path = os.path.join(output_dir, subject, 'CBV.nii.gz')
                    CBV_final = nib.load(CBV_path)
                    DWI_b0_mask_path = os.path.join(output_dir, subject, 'DWI_b0_mask.nii.gz')
                    mask = nib.load(DWI_b0_mask_path)
                    CBV_norm = zscore_normalize(CBV_final, mask)
                    nib.save(CBV_norm, CBV_path)

                    print('CBV coregistration done...')
                else:
                    pass
            else:
                pass
        elif modality == 'MTT':
            if not os.path.exists(os.path.join(output_dir, subject, 'MTT.nii.gz')):
                if os.path.exists(os.path.join(data_dir, subject, 'MTT.nii.gz')) and os.path.exists(os.path.join(
                        output_dir, subject, 'B0_r_transform.mat')):
                    reorient = fsl.utils.Reorient2Std()
                    reorient.inputs.in_file = os.path.join(data_dir, subject, 'MTT.nii.gz')
                    reorient.inputs.out_file = os.path.join(temp_dir, 'MTT_reorient.nii.gz')
                    res = reorient.run()

                    # register with MTT
                    flt = fsl.FLIRT(cost_func='mutualinfo', interp='spline',
                                    searchr_x=[-180, 180], searchr_y=[-180, 180], searchr_z=[-180, 180], dof=6)
                    flt.inputs.in_file = os.path.join(temp_dir, 'MTT_reorient.nii.gz')
                    if os.path.exists(os.path.join(data_dir, subject, 'FLAIR.nii.gz')):
                        flt.inputs.reference = os.path.join(output_dir, subject, 'FLAIR.nii.gz')
                    else:
                        flt.inputs.reference = os.path.join(output_dir, subject, 'DWI_b0.nii.gz')
                    flt.inputs.out_file = os.path.join(temp_dir, 'MTT_r.nii.gz')
                    flt.inputs.in_matrix_file = os.path.join(output_dir, subject, 'B0_r_transform.mat')
                    res = flt.run()

                    # apply skull stripping mask
                    am = fsl.maths.ApplyMask()
                    am.inputs.in_file = os.path.join(temp_dir, 'MTT_r.nii.gz')
                    am.inputs.mask_file = os.path.join(output_dir, subject, 'DWI_b0_mask.nii.gz')
                    am.inputs.out_file = os.path.join(output_dir, subject, 'MTT.nii.gz')
                    res = am.run()

                    # z score normalization
                    MTT_path = os.path.join(output_dir, subject, 'MTT.nii.gz')
                    MTT_final = nib.load(MTT_path)
                    DWI_b0_mask_path = os.path.join(output_dir, subject, 'DWI_b0_mask.nii.gz')
                    mask = nib.load(DWI_b0_mask_path)
                    MTT_norm = zscore_normalize(MTT_final, mask)
                    nib.save(MTT_norm, MTT_path)

                    print('MTT coregistration done...')
                else:
                    pass
            else:
                pass

        print('.........................')
        print('patient %s coregistration on modality %s done' % (subject, modality))


def hist_match(data_dir, subject, modality, ref_dir, output_dir):
    # register with different modality
    if modality == 'DWI_b1000':
        if not os.path.exists(os.path.join(output_dir, subject, 'DWI_b0.nii.gz')):
            if os.path.exists(os.path.join(data_dir, subject, 'DWI_b0.nii.gz')):
                input_volume = os.path.join(data_dir, subject, 'DWI_b0.nii.gz')
                ref_volume = os.path.join(ref_dir, 'DWI_b0.nii.gz')
                output_volume = os.path.join(output_dir, subject, 'DWI_b0.nii.gz')
                subprocess.call('~/toolbox/Slicer-4.10.2-linux-amd64/Slicer --launch HistogramMatching \
                                -- %s %s %s' % (input_volume,
                                                ref_volume,
                                                output_volume),
                                shell=True)
                print('T2 histogram matching done...')
    if modality == 'DWI_b1000':
        if not os.path.exists(os.path.join(output_dir, subject, 'DWI_b1000.nii.gz')):
            if os.path.exists(os.path.join(data_dir, subject, 'DWI_b1000.nii.gz')):
                input_volume = os.path.join(data_dir, subject, 'DWI_b1000.nii.gz')
                ref_volume = os.path.join(ref_dir, 'DWI_b1000.nii.gz')
                output_volume = os.path.join(output_dir, subject, 'DWI_b1000.nii.gz')
                subprocess.call('~/toolbox/Slicer-4.10.2-linux-amd64/Slicer --launch HistogramMatching \
                                -- %s %s %s' % (input_volume,
                                                ref_volume,
                                                output_volume),
                                shell=True)
                print('DWI histogram matching done...')
    if modality == 'FLAIR':
        if not os.path.exists(os.path.join(output_dir, subject, 'FLAIR.nii.gz')):
            if os.path.exists(os.path.join(data_dir, subject, 'FLAIR.nii.gz')):
                input_volume = os.path.join(data_dir, subject, 'FLAIR.nii.gz')
                ref_volume = os.path.join(ref_dir, 'FLAIR.nii.gz')
                output_volume = os.path.join(output_dir, subject, 'FLAIR.nii.gz')
                subprocess.call('~/toolbox/Slicer-4.10.2-linux-amd64/Slicer --launch HistogramMatching \
                                -- %s %s %s' % (input_volume,
                                                ref_volume,
                                                output_volume),
                                shell=True)
                print('FLAIR histogram matching done...')


if __name__ == '__main__':
    atlas_folder = "/mnt/sharedJH/atlas"
    data_folder = '/mnt/sharedJH/NIFTI_Renamed_for_correction'
    output_folder = '/mnt/sharedJH/Registered_output_correction'
    reference_dir = '/mnt/sharedJH/Registered_output/570244/'
    in_histmatch_folder = '/mnt/sharedJH/Registered_output'
    out_histmatch_folder = '/mnt/sharedJH/Registered_output_histmatch'

    modality_list = ['DWI_b1000', 'FLAIR', 'ADC', 'TMAX', 'TTP', 'CBF', 'CBV', 'MTT']
    modality_list_histmatch = ['DWI_b0', 'DWI_b1000', 'FLAIR']

    parallel = False

    # def complete_reg_steps(p):
    #     if not os.path.isdir(os.path.join(output_folder, p)):
    #         os.makedirs(os.path.join(output_folder, p))
    #
    #     preprocess(data_folder, p, atlas_folder, output_folder)
    #
    #     for mo in modality_list:
    #         coregister(data_folder, p, mo, atlas_folder, output_folder)
    #
    #
    # if not parallel:
    #     for patient in os.listdir(data_folder):
    #
    #         if not os.path.isdir(os.path.join(output_folder, patient)):
    #             os.makedirs(os.path.join(output_folder, patient))
    #
    #         preprocess(data_folder, patient, atlas_folder, output_folder)
    #
    #         for m in modality_list:
    #             coregister(data_folder, patient, m, atlas_folder, output_folder)
    # else:
    #     results = Parallel(n_jobs=8)(delayed(complete_reg_steps)(i) for i in os.listdir(data_folder))

    for patient in os.listdir(in_histmatch_folder):
        if not os.path.isdir(os.path.join(out_histmatch_folder, patient)):
            os.makedirs(os.path.join(out_histmatch_folder, patient))
        for m in modality_list_histmatch:
            hist_match(in_histmatch_folder, patient, m, reference_dir, out_histmatch_folder)
