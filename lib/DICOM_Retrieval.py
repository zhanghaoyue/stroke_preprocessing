import errno
import subprocess
import logging
import pydicom
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

    def listening(self, patient, series, f):
        self.patient_outdir = os.path.join(self.out_base_dir, patient+'/'+series)
        self.ls = subprocess.Popen('storescp -b bofa-420-aberle@10.9.94.219:12112 \
         --directory %s' % self.patient_outdir, shell=True, stdout=f, stderr=f, preexec_fn=os.setsid)

    def query(self, patient, accession, f):
        patient_uid_dir = os.path.join(self.out_query_dir, patient, 'AccessionNumber-' + accession)
        try:
            os.makedirs(patient_uid_dir)
        except OSError as e:
            if e.errno != errno.EEXIST:
                raise

        if not os.listdir(patient_uid_dir):
            subprocess.call('findscu -b bofa-420-aberle@10.9.94.219:12112 \
                    -c WWPACSQR@10.7.1.64:4100 -m AccessionNumber=%s -L SERIES -r SeriesInstanceUID \
                     NumberOfStudyRelatedInstances NumberOfSeriesRelatedInstances\
                    --out-file series.dcm --out-dir %s' % (accession, patient_uid_dir), stdout=f, stderr=f, shell=True)
        else:
            pass
        return patient_uid_dir

    def retrieve(self, patient, accession, s, f):
        patient_uid_dir = os.path.join(self.out_query_dir, patient, 'AccessionNumber-' + accession + '/*')
        self.rv = subprocess.call('movescu -b bofa-420-aberle@10.9.94.219:12112 \
        -c WWPACSQR@10.7.1.64:4100 -L SERIES -m SeriesInstanceUID=%s \
        --idle-timeout 10000 --retrieve-timeout-total 600000 --dest bofa-420-aberle \
        -- %s' % (s.SeriesInstanceUID, patient_uid_dir), stdout=f, stderr=f, shell=True)

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

    dcm_file = pd.read_csv('/home/harryzhang/PACS_QUERY/DICOM_Query_0806.csv', dtype=str)
    dcm_array = np.array(dcm_file)
    num_iterations = 10

    i = 1

    while i < num_iterations:

        logging.info("Iter %d, Starting DICOM dump into directory %s" % (i, out_base_dir,))
        logging.info("Logs located at %s" % log_outdir)

        for pt_row in dcm_array:
            t0 = time.time()
            print(pt_row)

            log_out_query = os.path.join(log_outdir, '%s.%d.query.log' % (str(pt_row[0]), i))
            query_log = open(log_out_query, 'w')
            retrieval_instance = DicomRetrieval(out_base_dir, out_query_dir)
            patient_query_dir = retrieval_instance.query(patient=pt_row[0], accession=pt_row[2], f=query_log)
            query_log.close()

            for series_file in os.listdir(patient_query_dir):
                series = pydicom.dcmread(patient_query_dir+'/'+series_file, force=True)
                if not os.path.isdir(out_base_dir + '/' + pt_row[0]+'/'+os.fsdecode(series_file)):
                    os.makedirs(out_base_dir + '/' + pt_row[0]+'/'+os.fsdecode(series_file))

                path, dir, files = next(os.walk(out_base_dir+'/'+pt_row[0]+'/'+os.fsdecode(series_file)))
                if len(files) < int(series.NumberOfSeriesRelatedInstances):

                    log_out_listen = os.path.join(log_outdir, '%s.%s.%d.listen.log' % (str(pt_row[0]),
                                                                                       os.fsdecode(series_file), i))
                    log_out_retrieve = os.path.join(log_outdir, '%s.%s.%d.retireve.log' % (str(pt_row[0]),
                                                                                           os.fsdecode(series_file), i))
                    listening_log = open(log_out_listen, 'w')
                    retrieve_log = open(log_out_retrieve, 'w')
                    retrieval_instance.listening(patient=pt_row[0], series=os.fsdecode(series_file), f=listening_log)
                    print("port listening process PID:")
                    print(retrieval_instance.ls.pid)
                    print("start retrieving %s" % os.fsdecode(series_file))
                    time.sleep(5)
                    retrieval_instance.retrieve(patient=pt_row[0], accession=pt_row[2], s=series, f=retrieve_log)
                    t1 = time.time()
                    print('retrieval time used %d s' % (t1 - t0))
                    print('Waiting...5s')
                    time.sleep(5)

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
