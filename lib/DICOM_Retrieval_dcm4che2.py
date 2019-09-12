import errno
import subprocess
import logging
import random
import time
import pandas as pd
import numpy as np
import os
import pydicom


def retrieve(out_dir, accession, series_uid, f):
    """
    credentials:
    local:
        bofa-420-aberle@10.9.94.219:12112
    remote:
        WWPACSQR@10.7.1.64:4100
    """
    subprocess.call('~/toolbox/dcm4che-2.0.29-bin/dcm4che-2.0.29/bin/dcmqr -L bofa-420-aberle@10.9.94.219:12112 \
                WWPACSQR@10.7.1.64:4100 -cmove bofa-420-aberle -S -qAccessionNumber=%s -qSeriesInstanceUID=%s \
                -cstore SC:NOPXD -cstoredest %s'
                    % (accession, series_uid, out_dir), stdout=f, stderr=f, shell=True)


if __name__ == '__main__':
    out_base_dir = '/media/harryzhang/VolumeWD/DataDump_MRN_series'
    out_query_dir = '/media/harryzhang/VolumeWD/QueryUID'
    logging.getLogger().setLevel(logging.INFO)
    log_outdir = os.path.join('/media/harryzhang/VolumeWD/', 'logs')

    if not os.path.isdir(log_outdir):
        os.makedirs(log_outdir)

    dcm_file = pd.read_csv('/home/harryzhang/PACS_QUERY/DICOM_Query_0806.csv', dtype=str)
    dcm_array = np.array(dcm_file)
    num_iterations = 5

    i = 1
    while i < num_iterations:

        logging.info("Iter %d, Starting DICOM dump into directory %s" % (i, out_base_dir,))
        logging.info("Logs located at %s" % log_outdir)

        for pt_row in dcm_array:
            print(pt_row)
            patient_query_dir = os.path.join(out_query_dir, pt_row[0], 'AccessionNumber-' + pt_row[2])
            for series_file in os.listdir(patient_query_dir):
                series = pydicom.dcmread(patient_query_dir + '/' + series_file, force=True)
                out_series_dir = out_base_dir + '/' + pt_row[0] + '/' + os.fsdecode(series_file)
                if not os.path.isdir(out_series_dir):
                    os.makedirs(out_series_dir)
                path, dir, files = next(os.walk(out_series_dir))

                if len(files) < int(series.NumberOfSeriesRelatedInstances):
                    log_out_retrieve = os.path.join(log_outdir, '%s.%s.%d.retrieve.log' % (str(pt_row[0]),
                                                                                           os.fsdecode(series_file), i))
                    retrieve_log = open(log_out_retrieve, 'w')
                    retrieve(out_dir=out_series_dir, accession=pt_row[2], series_uid=series.SeriesInstanceUID,
                             f=retrieve_log)
                    retrieve_log.close()

        i += 1

    logging.info("Dump complete")
