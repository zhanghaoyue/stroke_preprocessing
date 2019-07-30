import subprocess
import logging
import ast
import time
import pandas as pd
import numpy as np
import os
import signal
import psutil


class DicomRetrieval:

    def __init__(self, out_base_dir, out_query_dir):

        self.out_base_dir = out_base_dir
        self.out_query_dir = out_query_dir
        self.patient_outdir = None
        self.rv = None
        self.ls = None

    def listening(self, patient):
        self.patient_outdir = os.path.join(self.out_base_dir, patient)
        self.ls = subprocess.Popen('storescp -b bofa-420-aberle@10.9.94.219:12112 \
         --directory %s' % self.patient_outdir, shell=True, stdout=subprocess.PIPE, preexec_fn=os.setsid)

    def query(self, patient, accession):
        patient_uid_dir = os.path.join(self.out_query_dir, patient, 'AccessionNumber-' + accession)
        subprocess.call('findscu -b bofa-420-aberle@10.9.94.219:12112 \
                -c WWPACSQR@10.7.1.64:4100 -m AccessionNumber=%s -r StudyInstanceUID \
                --out-dir %s' % (accession, patient_uid_dir), shell=True)

    def retrieve(self, patient, accession, fout):
        patient_uid_dir = os.path.join(self.out_query_dir, patient, 'AccessionNumber-' + accession + '/*')
        self.rv = subprocess.call('movescu -b bofa-420-aberle@10.9.94.219:12112 \
        -c WWPACSQR@10.7.1.64:4100 -i StudyInstanceUID --dest bofa-420-aberle %s' %
                                  patient_uid_dir, stdout=fout, shell=True)

    @staticmethod
    def kill(proc_pid):
        process = psutil.Process(proc_pid)
        for proc in process.children(recursive=True):
            proc.kill()
        process.kill()


if __name__ == '__main__':
    out_base_dir = '/media/harryzhang/VolumeWD/DataDump_MRN'
    out_query_dir = '/media/harryzhang/VolumeWD/QueryUID'
    logging.getLogger().setLevel(logging.INFO)
    log_outdir = os.path.join(out_base_dir, 'logs')
    if not os.path.isdir(log_outdir):
        os.makedirs(log_outdir)

    dcm_file = pd.read_csv('/home/harryzhang/PACS_QUERY/Johnny_Accessions.csv', dtype=str)
    dcm_array = np.array(dcm_file)
    num_iterations = 2

    i = 1

    while i < num_iterations:

        completed_patients_fname = os.path.join(out_base_dir, 'completed_patients.txt')
        try:
            completed_patients_in = open(completed_patients_fname, 'r')
        except:
            completed_patients_in = open(completed_patients_fname, 'w')
            completed_patients_in = open(completed_patients_fname, 'r')

        completed_list = []
        for line in completed_patients_in:
            completed_list.append(ast.literal_eval(line))
        completed_patients_in.close()

        new_list = []
        for pt in np.arange(0, dcm_array.shape[0]):
            if dcm_array[pt][0] not in completed_list:
                new_list.append(dcm_array[pt])

        if len(new_list) == 0:
            break

        completed_patients_out = open(completed_patients_fname, 'a')

        logging.info("Iter %d, Starting DICOM dump into directory %s" % (i, out_base_dir,))
        logging.info("Error logs located at %s" % log_outdir)
        logging.info("%d studies remain" % (len(new_list),))

        for pt_row in new_list:
            print(pt_row)
            retrieval_instance = DicomRetrieval(out_base_dir, out_query_dir)
            retrieval_instance.query(patient=pt_row[0], accession=pt_row[2])
            retrieval_instance.listening(patient=pt_row[0])
            time.sleep(1)
            log_out_filename = os.path.join(log_outdir, '%s.%d.log' % (str(pt_row[0]), num_iterations))
            fout = open(log_out_filename, 'w')
            retrieval_instance.retrieve(patient=pt_row[0], accession=pt_row[2], fout=fout)
            print('Waiting...')
            time.sleep(30)
            fout.close()
            try:
                retrieval_instance.ls.wait(timeout=3)
            except subprocess.TimeoutExpired:
                retrieval_instance.kill(retrieval_instance.ls.pid)
            print(retrieval_instance.ls.pid)
            os.killpg(os.getpgid(retrieval_instance.ls.pid), signal.SIGTERM)

            empty_dirs = [dirpath for (dirpath, dirnames, filenames) in os.walk(retrieval_instance.patient_outdir) if
                          len(filenames) == 0 and len(dirnames) == 0]
            if len(empty_dirs) == 0:
                completed_patients_out.write('%s\n' % (pt_row[0],))
            else:
                for ed in empty_dirs:
                    logging.error("Failure rv(%d) for patient %s" % (retrieval_instance.rv, pt_row[0]))
                    print("Failure rv(%d) for patient %s" % (retrieval_instance.rv, pt_row[0]))
                    os.rmdir(ed)
        completed_patients_out.close()

        num_iterations += 1
    logging.info("Dump complete")
