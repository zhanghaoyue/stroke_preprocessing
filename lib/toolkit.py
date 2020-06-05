import os


def walkit(root_dir):
    # os.walk gives you the name of the directory it's in,
    # all the subdirs (as a list),
    # and all the filesnames (as a list)
    for curr_dir, sub_dir, filename in os.walk(root_dir):
        print("---------------------------")
        for i in sub_dir:
            print("This Directory =", curr_dir, "\nSubdirectories:", i)

            ADC_name = os.path.join(curr_dir, i, "ADC.nii.gz")
            old_name = os.path.join(curr_dir, i, "ADC_coreg.nii.gz")

            try:  # Use try except to catch problems
                print("Delete ADC")
                os.remove(ADC_name)
                os.remove(os.path.join(curr_dir, i, "ADC_fsl.nii.gz"))
                os.remove(os.path.join(curr_dir, i, "ADC_masked.nii.gz"))
                print("Renaming '{}' to '{}' ... ".format(old_name, ADC_name), end='')
                os.rename(old_name, ADC_name)  # Rename the file
                print("OK")  # Worked
            except Exception as e:  # Failed
                print("FAILED! (ERROR:{})".format(str(e)))


if __name__ == '__main__':
    data_folder = "/data/haoyuezhang/data/stroke_MRI/stroke_MRI/Registered_output_ds"
    walkit(data_folder)
