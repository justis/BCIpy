import csv
import time
import re
from datetime import datetime
from decimal import Decimal
from matplotlib import *
import matplotlib.pyplot as plt
import matplotlib.pylab as pylab
pylab.rcParams['figure.figsize'] = 15, 6
from os.path import join
from scipy.signal import butter, lfilter, freqz
import numpy as np

import warnings
warnings.filterwarnings('ignore', 'DeprecationWarning')


try: # Import config params
   import dev_settings as config
except ImportError:
   print "Please create a dev_settings.py using dev_settings.py.example as an example"

def print_config():
    print config.DATA_URL
    print config.SAVE_URL

def format_time(ti):
    """
    Converts format '2010-12-14 16:56:36.996' to Decimal
    """
    to = datetime.strptime(ti, '%Y-%m-%d %H:%M:%S.%f')
    #Decimal not losing precision
    to = Decimal(to.strftime('%s.%f'))
    return str(to)
    
def format_task_xls(file):
    path_task_xls = join(config.DATA_URL, file + ".xls")
    path_task_xls_labels = join(config.SAVE_URL,  file + "_xls_labels.csv")
    
    with open(path_task_xls, 'rb') as fi,\
    open(path_task_xls_labels, 'w') as fo:
        fr = csv.reader(fi, delimiter='\t')
        fw = csv.writer(fo, delimiter='\t')
        
        h = fr.next()
        fw.writerow(['taskid',h[0], h[1], h[2], h[3], h[-1]]) #header
        
        for idx, row in enumerate(fr):
            row[2] = format_time(row[2])
            row[3] = format_time(row[3])
            fw.writerow([idx, row[0], row[1], row[2], row[3], row[-1]])

# deprecated?
def compress_time_labels(file_name):
    """
    Combines contiguous time windows
    with same difficulty label
    """
    with open(file_name, 'rb') as fi,\
    open("./preprocess/task_xls_labels_compress.csv", 'w') as fo:
        fr = csv.reader(fi, delimiter='\t')
        fw = csv.writer(fo, delimiter='\t')
        fw.writerow(fr.next()) #header
        
        row1 = fr.next()
        t_id =row1[0]
        t_s = row1[1]
        t_e = row1[2]
        lab = row1[3]
        
        for row in fr: #row 2 onwards
            if row[3] == lab:
                t_e = row[2]
            else:
                fw.writerow([str(t_id),str(t_s), str(t_e), lab])
                t_id =row[0]
                t_s = row[1]
                t_e = row[2]
                lab = row[3]
        fw.writerow([str(t_id),str(t_s), str(t_e), lab]) #last row

def label_data(in_file, out_file, compressed_label_file, subj_t, time_t, dbg=False):
    if dbg: print "#"+subj_t + "--------"
    
    with open(in_file, 'rb') as fi,\
    open(out_file, 'rb') as fi2,\
    open(compressed_label_file, 'w') as fo:
        
        day = time_t[0:4]+"-"+time_t[4:6]+"-"+time_t[6:8]
        fr1 = csv.reader(fi,  delimiter=',') # combined.csv
        fr2 = csv.reader(fi2, delimiter='\t')# xls_labels.csv
        fw  = csv.writer(fo,  delimiter='\t')# combined_label_uncompress.csv
        
        if dbg: print "day: " + day
        
        #headers
        fw.writerow(next(fr1, None) + ['Difficulty', 'taskid'] )
        next(fr2, None)
        
        #forward till subject data starts
        lab_row = fr2.next()
        while subj_t != lab_row[2]:
            lab_row = fr2.next()
        if dbg: print "start: " + str(lab_row[0])
        
        for idx, row in enumerate(fr1):
            row[0] = datetime.strptime(day+' '+row[0]+'.0',\
                            '%Y-%m-%d %H:%M:%S.%f').strftime('%s.%f')
            if Decimal(row[0]) < Decimal(lab_row[3]): # t < start_time
                if dbg: print str(idx)+": t<start_time"
                label = -1
                fw.writerow(row + [label, lab_row[0]])
                continue
                
            if Decimal(row[0]) <= Decimal(lab_row[4]): # t <= end_time
                if dbg: print str(idx)+": t <= end_time"
                label = lab_row[5]
                fw.writerow(row + [label, lab_row[0]])
                continue
            
            while Decimal(row[0] > lab_row[4]): # t > end_time
                try:
                    lab_row = next(fr2)
                    label = lab_row[5]
                    if lab_row[2] != subj_t:
                        raise Exception("Reached end of data for subject" + subj_t)
                except Exception as e: # reached end of file, or next subject
                    label = -1
                    if dbg: print e
                    break
            fw.writerow(row + [label,lab_row[0]])
        
        if dbg: print "end:   "+str(lab_row[0])
    return

def create_raw_incremental(in_file, out_file):
    "Create raw file with incremental miliseconds"
    with open(in_file,'rb') as fi, open(out_file,'w') as fo:
        fr = csv.reader(fi, delimiter=',')
        fw = csv.writer(fo, delimiter=',')
        
        fw.writerow(next(fr))#header
        
        c=0.0
        prev_time = '100'#dummy
        for row in fr:
            if row[0]==prev_time:
                c = c + 0.001
            else:
                c = 0.0
                prev_time = row[0]
            fw.writerow([row[0] + '.' + str(c).split('.')[1], row[1]])

def label_data_raw(in_file, out_file, task_xls_label_file, mach_t, time_t, dbg=False):
    if dbg: print "#"+mach_t + "--------"
    
    with open(in_file, 'rb') as fi,\
    open(task_xls_label_file, 'rb') as fi2,\
    open(out_file, 'w') as fo:
        
        day = time_t[0:4]+"-"+time_t[4:6]+"-"+time_t[6:8]
        fr1 = csv.reader(fi,  delimiter=',') #microsec file
        fr2 = csv.reader(fi2, delimiter='\t')# xls_labels.csv
        fw  = csv.writer(fo,  delimiter='\t')
        
        #headers
        fw.writerow(next(fr1, None) + ['Difficulty', 'taskid'] )
        next(fr2, None)
        
        #forward till subject mach starts
        lab_row = fr2.next()
        while mach_t != lab_row[1]:
            lab_row = fr2.next()
        if dbg: print "start: " + str(lab_row[0])
        
        for idx, row in enumerate(fr1):
            row[0] = datetime.strptime(day+' '+row[0],\
                            '%Y-%m-%d %H:%M:%S.%f').strftime('%s.%f')
            if Decimal(row[0]) < Decimal(lab_row[3]): # t < start_time
                label = -1
                fw.writerow(row + [label, lab_row[0]])
                continue
                
            if Decimal(row[0]) < Decimal(lab_row[4]): # t < end_time
                label = lab_row[5]
                fw.writerow(row + [label, lab_row[0]])
                continue
            
            while Decimal(row[0] > lab_row[4]): # t > end_time
                try:
                    lab_row = next(fr2)
                    label = lab_row[5]
                except: # reached end of file
                    label = -1
                    break
            fw.writerow(row + [label, lab_row[0]])
        
        if dbg: print "end:   "+str(lab_row[0])
    return
    
def plot_signal(x_ax, y_ax, label, ax=None):
    if ax==None:
        fig, ax = plt.subplots()
    ax.plot(x_ax, y_ax, label=label)
    ax.grid(True)
    fig.tight_layout()
    plt.legend(loc='upper left')
    plt.show()
    return ax
    
def butter_bandpass(lowcut, highcut, fs, order=5):
    """
    http://wiki.scipy.org/Cookbook/ButterworthBandpass
    """
    nyq = 0.5 * fs
    low = lowcut / nyq
    high = highcut / nyq
    b, a = butter(order, [low, high], btype='band')
    return b, a

def butter_bandpass_filter(data, lowcut, highcut, fs, order=5):
    b, a = butter_bandpass(lowcut, highcut, fs, order=order)
    y = lfilter(b, a, data)
    return y
    
def plot_butter(fs, lowcut, highcut, orders):
    """Plot the frequency response for a few different orders."""
    plt.figure(1)
    plt.clf()
    for order in orders:
        b, a = butter_bandpass(lowcut, highcut, fs, order=order)
        w, h = freqz(b, a, worN=2000)
        plt.plot((fs * 0.5 / np.pi) * w, abs(h), label="order = %d" % order)
        plt.title("Sample frequency responses of the band filter")
        plt.xlabel('Frequency (Hz)')
        plt.ylabel('Gain')
        plt.grid(True)
        plt.legend(loc='best')