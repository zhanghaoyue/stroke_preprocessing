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

    def listening(self, patient, f):
        self.patient_outdir = os.path.join(self.out_base_dir, patient)
        self.ls = subprocess.Popen('storescp -b bofa-420-aberle@10.9.94.219:12112 \
         --directory %s' % self.patient_outdir, shell=True, stdout=f, preexec_fn=os.setsid)

    def query(self, patient, accession, f):
        patient_uid_dir = os.path.join(self.out_query_dir, patient, 'AccessionNumber-' + accession)
        subprocess.call('findscu -b bofa-420-aberle@10.9.94.219:12112 \
                -c WWPACSQR@10.7.1.64:4100 -m AccessionNumber=%s -r StudyInstanceUID NumberOfSeriesRelatedInstances\
                --out-dir %s' % (accession, patient_uid_dir), stdout=f, shell=True)

    def retrieve(self, patient, accession, f):
        patient_uid_dir = os.path.join(self.out_query_dir, patient, 'AccessionNumber-' + accession + '/*')
        self.rv = subprocess.call('movescu -b bofa-420-aberle@10.9.94.219:12112 \
        -c WWPACSQR@10.7.1.64:4100 -i StudyInstanceUID --dest bofa-420-aberle %s' %
                                  patient_uid_dir, stdout=f, shell=True)

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

        logging.info("Iter %d, Starting DICOM dump into directory %s" % (i, out_base_dir,))
        logging.info("Error logs located at %s" % log_outdir)

        for pt_row in dcm_array[0:3]:
            t0 = time.time()
            print(pt_row)
            if not os.path.isdir(out_base_dir+'/'+pt_row[0]):
                os.makedirs(out_base_dir+'/'+pt_row[0])
            path, dir, files = next(os.walk(out_base_dir+'/'+pt_row[0]))
            if len(files) < int(pt_row[4]):
                log_out_query = os.path.join(log_outdir, '%s.%d.query.log' % (str(pt_row[0]), i))
                log_out_listen = os.path.join(log_outdir, '%s.%d.listen.log' % (str(pt_row[0]), i))
                log_out_retrieve = os.path.join(log_outdir, '%s.%d.retireve.log' % (str(pt_row[0]), i))
                query_log = open(log_out_query, 'w')
                listening_log = open(log_out_listen, 'w')
                retrieve_log = open(log_out_retrieve, 'w')
                retrieval_instance = DicomRetrieval(out_base_dir, out_query_dir)
                retrieval_instance.query(patient=pt_row[0], accession=pt_row[2], f=query_log)
                retrieval_instance.listening(patient=pt_row[0], f=listening_log)
                print("port listening process PID:")
                print(retrieval_instance.ls.pid)
                print("start retrieving")
                time.sleep(1)
                retrieval_instance.retrieve(patient=pt_row[0], accession=pt_row[2], f=retrieve_log)
                t1 = time.time()
                print('retrieval time used %d ' % (t1 - t0))
                print('Waiting...30s')
                time.sleep(30)
                query_log.close()
                listening_log.close()
                retrieve_log.close()
                '''
                try:
                    retrieval_instance.ls.wait(timeout=1)
                except subprocess.TimeoutExpired:
                    retrieval_instance.kill(retrieval_instance.ls.pid)
                '''
                os.killpg(os.getpgid(retrieval_instance.ls.pid), signal.SIGTERM)
            else:
                continue

        i += 1

    logging.info("Dump complete")
