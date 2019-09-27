### RGB to HSV

from skimage.color import rgb2hsv
import nibabel as nib
import matplotlib
import itk
import SimpleITK as sitk
import numpy as np
import matplotlib
from skimage.color import rgb2gray
import os


def rapid_map_conversion(input_path):
    rap_ims = {'RAPID_TMAX.nii.gz': 255,
               'RAPID_CBV.nii.gz': 255,
               'RAPID_CBF.nii.gz': 255,
               'RAPID_MTT.nii.gz': 255}

    for pt in os.listdir(input_path):
        pt_path = os.path.join(input_path, pt)
        if 'RAPID_TMAX_C.nii.gz' in os.listdir(pt_path):
            os.rename(os.path.join(pt_path, 'RAPID_TMAX.nii.gz'), os.path.join(pt_path, 'RAPID_TMAX_raw.nii.gz'))
            os.rename(os.path.join(pt_path, 'RAPID_TMAX_C.nii.gz'), os.path.join(pt_path, 'RAPID_TMAX.nii.gz'))

            os.rename(os.path.join(pt_path, 'RAPID_CBV.nii.gz'), os.path.join(pt_path, 'RAPID_CBV_raw.nii.gz'))
            os.rename(os.path.join(pt_path, 'RAPID_CBV_C.nii.gz'), os.path.join(pt_path, 'RAPID_CBV.nii.gz'))

            os.rename(os.path.join(pt_path, 'RAPID_CBF.nii.gz'), os.path.join(pt_path, 'RAPID_CBF_raw.nii.gz'))
            os.rename(os.path.join(pt_path, 'RAPID_CBF_C.nii.gz'), os.path.join(pt_path, 'RAPID_CBF.nii.gz'))

            os.rename(os.path.join(pt_path, 'RAPID_MTT.nii.gz'), os.path.join(pt_path, 'RAPID_MTT_raw.nii.gz'))
            os.rename(os.path.join(pt_path, 'RAPID_MTT_C.nii.gz'), os.path.join(pt_path, 'RAPID_MTT.nii.gz'))

        if not all(x in os.listdir(pt_path) for x in ['TMAX.nii.gz', 'CBF.nii.gz', 'MTT.nii.gz', 'CBV.nii.gz']):
            for file in os.listdir(pt_path):

                if file in rap_ims.keys():
                    input_path_im = os.path.join(pt_path, file)
                    itk_image = itk.imread(input_path_im)
                    nib_img = nib.load(input_path_im)
                    np_copy = itk.GetArrayFromImage(itk_image)
                    # Do numpy stuff
                    gray = matplotlib.colors.rgb_to_hsv(np_copy)
                    # Find the inverse of hue if not 0
                    gray_copy = np.zeros(gray.shape[0:3])
                    # iterate through voxels - annoying
                    for z in np.arange(0, gray.shape[0]):
                        for x in np.arange(0, gray.shape[1]):
                            for y in np.arange(0, gray.shape[2]):
                                voxel = gray[z, x, y]
                                # if it's not background? maybe there's a better/faster way to do this
                                if sum(voxel) > 0:
                                    # get the inverse, and multiply by the scale of the image 
                                    h = (1 - voxel[0]) * rap_ims[file]
                                    # add to the array
                                    gray_copy[z, x, y] = h
                    # create output file name and path
                    output_im = file[6:-7] + '.nii.gz'
                    output_path_im = os.path.join(pt_path, output_im)

                    # if file has a raw version, crop out only the scale
                    if 'RAPID_TMAX_raw.nii.gz' in os.listdir(pt_path):
                        gray_copy[:, :, :20] = np.zeros((gray_copy.shape[0], gray_copy.shape[1], 20))
                    # otherwise, both the scale and the heading at the top
                    else:
                        gray_copy[:, -50:, :] = np.zeros((gray_copy.shape[0], 50, gray_copy.shape[2]))
                        gray_copy[:, :, :50] = np.zeros((gray_copy.shape[0], gray_copy.shape[1], 50))
                    # change the datatype in the header
                    nib_img.header.set_data_dtype(np.uint8)
                    # create our new nifti image in grayscale
                    bw_image = nib.Nifti1Image(gray_copy.T, nib_img.affine, nib_img.header)
                    # save the image
                    nib.save(bw_image, output_path_im)
    print('RAPID Grayscale conversion complete.')
    return None


if __name__ == '__main__':
    data_folder = '/mnt/sharedJH/NIFTI_Renamed'
    rapid_map_conversion(data_folder)