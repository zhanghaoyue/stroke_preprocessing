import os
from nipype.interfaces.ants import Registration, ApplyTransforms, N4BiasFieldCorrection
from fsl.wrappers import robustfov, fslreorient2std
import subprocess

test_dir = "G:/ResearchStroke/no-reflow/sample_case/"

# reorient to MNI standard direction
# reorient_in_file = os.path.join(test_dir, '0599875_pre_FLAIR.nii.gz')
# reorient_out_file = os.path.join(test_dir, '0599875_pre_FLAIR_reorient.nii.gz')
# fslreorient2std(reorient_in_file, reorient_out_file)
#
# reorient_in_file = os.path.join(test_dir, '0599875_post_FLAIR.nii.gz')
# reorient_out_file = os.path.join(test_dir, '0599875_post_FLAIR_reorient.nii.gz')
# fslreorient2std(reorient_in_file, reorient_out_file)
#
# # robust fov to remove neck and lower head automatically
# rf_in_file = os.path.join(test_dir, '0599875_pre_FLAIR_reorient.nii.gz')
# rf_out_roi = os.path.join(test_dir, '0599875_pre_FLAIR_RF.nii.gz')
# robustfov(rf_in_file, rf_out_roi)
#
# rf_in_file = os.path.join(test_dir, '0599875_post_FLAIR_reorient.nii.gz')
# rf_out_roi = os.path.join(test_dir, '0599875_post_FLAIR_RF.nii.gz')
# robustfov(rf_in_file, rf_out_roi)

# n4_1 = N4BiasFieldCorrection()
# n4_1.inputs.dimension = 3
# n4_1.inputs.input_image = os.path.join(test_dir, '0599875_pre_FLAIR.nii.gz')
# n4_1.inputs.bspline_fitting_distance = 300
# n4_1.inputs.shrink_factor = 3
# n4_1.inputs.n_iterations = [50, 50, 30, 20]
# n4_1.inputs.output_image = os.path.join(test_dir, '0599875_pre_FLAIR_n4.nii.gz')
# subprocess.call(n4_1.cmdline, shell=True)
#
# n4_2 = N4BiasFieldCorrection()
# n4_2.inputs.dimension = 3
# n4_2.inputs.input_image = os.path.join(test_dir, '0599875_post_FLAIR.nii.gz')
# n4_2.inputs.bspline_fitting_distance = 300
# n4_2.inputs.shrink_factor = 3
# n4_2.inputs.n_iterations = [50, 50, 30, 20]
# n4_2.inputs.output_image = os.path.join(test_dir, '0599875_post_FLAIR_n4.nii.gz')
# subprocess.call(n4_2.cmdline, shell=True)
#
# print('N4 Bias Field Correction running...')

print('ANTs registration...')
reg = Registration()
# reg = RegistrationSynQuick()
reg.inputs.fixed_image = os.path.join(test_dir, '0599875_pre_FLAIR_n4_stripped.nii.gz')
reg.inputs.moving_image = os.path.join(test_dir, '0599875_post_FLAIR_n4_stripped.nii.gz')
reg.inputs.output_transform_prefix = os.path.join(test_dir, '5492881_transform.mat')
reg.inputs.winsorize_upper_quantile = 0.995
reg.inputs.winsorize_lower_quantile = 0.005
reg.inputs.transforms = ['Translation', 'Rigid', 'Affine', 'SyN']
reg.inputs.transform_parameters = [(0.1,), (0.1,), (0.1,), (0.2, 3.0, 0.0)]
reg.inputs.number_of_iterations = ([[10000, 111110, 11110]] * 3 + [[100, 50, 30]])
reg.inputs.dimension = 3
reg.inputs.write_composite_transform = True
reg.inputs.collapse_output_transforms = False
reg.inputs.initialize_transforms_per_stage = True
reg.inputs.metric = ['Mattes'] * 3 + [['Mattes', 'CC']]
reg.inputs.metric_weight = [1] * 3 + [[0.5, 0.5]]
reg.inputs.radius_or_number_of_bins = [32] * 3 + [[32, 4]]
reg.inputs.sampling_strategy = ['Regular'] * 3 + [[None, None]]
reg.inputs.sampling_percentage = [0.3] * 3 + [[None, None]]
reg.inputs.convergence_threshold = [1.e-8] * 3 + [-0.01]
reg.inputs.convergence_window_size = [20] * 3 + [5]
reg.inputs.smoothing_sigmas = [[4, 2, 1]] * 3 + [[1, 0.5, 0]]
reg.inputs.sigma_units = ['vox'] * 4
reg.inputs.shrink_factors = [[6, 4, 2]] + [[3, 2, 1]] * 2 + [[4, 2, 1]]
reg.inputs.use_histogram_matching = [False] * 3 + [True]
reg.inputs.output_warped_image = os.path.join(test_dir, '0599875_post_FLAIR_r.nii.gz')
reg.inputs.initial_moving_transform_com = True
reg.inputs.verbose = True
print(reg.cmdline)
subprocess.call(reg.cmdline, shell=True)
print('ANTs registration done...')

print('ANTs apply transform...')
at = ApplyTransforms()
at.inputs.dimension = 3
at.inputs.input_image = os.path.join(test_dir, '0599875_post_TMAX.nii.gz')
at.inputs.reference_image = os.path.join(test_dir, '0599875_post_FLAIR_r.nii.gz')
at.inputs.output_image = os.path.join(test_dir, '0599875_post_TMAX_r.nii.gz')
at.inputs.default_value = 0
at.inputs.transforms = os.path.join(test_dir, '0599875_transform.matComposite.h5')
print(at.cmdline)
subprocess.call(at.cmdline, shell=True)
print('ANTs apply transform done...')
