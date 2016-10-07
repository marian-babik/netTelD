#!/usr/bin/env python
# imports
from __future__ import print_function
from __future__ import division
from messaging.queue.dqs import DQS
import json
import numpy as np
import pandas as pd
import logging
import time
import urllib2
import pickle
import socket
from keras.models import load_model
import logging.handlers
from daemon import Daemon
from DataStore import DataStore


class netTel(Daemon):

    def __init__(self, pidfile,  loglevel=logging.DEBUG, **kwargs):
        Daemon.__init__(self, pidfile, **kwargs)
        self.loglevel = loglevel

    def run(self):
        self.netTel_main_program(loglevel=self.loglevel)


    # ------------------ Main Function ------------------
    def netTel_main_program(self, loglevel=logging.DEBUG):
        # set up logging
        log = logging.getLogger('netTel_logger')
        log.setLevel(loglevel)
        # maximum size of one log should be 20 mb
        handler = logging.handlers.RotatingFileHandler(
            "/var/log/netTel/netTel.log", maxBytes=20971520, backupCount=5)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        log.addHandler(handler)

        # Configuration variables

        # folder where stompclt saves stuff
        # input message q
        input_message_q_path = "/var/spool/netTel/input/"
        output_message_q_path = "/var/spool/netTel/output/"

        # url for nn download
        nn_url = "https://cernbox.cern.ch/index.php/s/68IKwd2uI2uQM9J/download"
        nn_scaler_url = "https://cernbox.cern.ch/index.php/s/sHXaEcVXDovJYzU/download"
        nn_file_path = "globalNN_for_netTel.h5"
        nn_scaler_file_path = "global_NN_for_netTel_scaler.pkl"

        log.info("Setting up netTel")

        log.info("Setting up q's")
        mq = DQS(path=input_message_q_path)
        mq_output = DQS(path=output_message_q_path)

        log.info("Setting up global NN and scaler")
        # download NN and its scaler
        nn_download = urllib2.urlopen(nn_url)
        with open(nn_file_path, 'wb') as output:
            output.write(nn_download.read())

        nn_scaler_download = urllib2.urlopen(nn_scaler_url)
        with open(nn_scaler_file_path, 'wb') as output:
            output.write(nn_scaler_download.read())

        # if we are later using multi threading, we need a specific lock here!
        # we will not want to integrate this into each dataStore, because the memory footprint is rather high
        nn_model = load_model(nn_file_path)
        nn_scaler = pickle.load(open(nn_scaler_file_path, "rb"))

        log.info("Deleting left over messages")
        for name in mq:
            if mq.lock(name):
                mq.remove(name)
        mq.purge()
        mq_output.purge()

        log.info("Setting global variables")
        data_src_dest = {}
        data_meta_header_src_dest = {}
        # I am actually not sure anymore if storing the meta and header in another dictionary improves performance
        # Saving it the DataStore class is way cleaner...
        local_IP = socket.gethostbyname(socket.gethostname())
        statistics_counter = 0
        messages_sum = 0
        reading_messages_time = 0
        reading_messages_and_calcing_time = 0
        total_used_time = 0
        error_counter = 0
        msg_counter = 0

        log.info("Starting main loop (reading messages)")
        while 1:
            if mq.count() == 0:
                time.sleep(1)
            startTime = time.time()
            # read latest messages
            # Reading latest messages from queue
            # remember: the data we get from here is automatically sorted!
            numMessages = mq.count()
            data_src_dest, data_meta_header_src_dest = self.read_latest_messages(mq,
                                                                                 base_data_raw_src_dest=data_src_dest,
                                                                                 base_data_meta_header_src_dest=data_meta_header_src_dest,
                                                                                 delete_messages_after_reading=True)
            reading_messages_time += time.time() - startTime

            # Processing Data and Computing predictions
            for key1 in data_src_dest.keys():
                for key2 in data_src_dest[key1].keys():
                    # this should have been done in calculate_all_time_vars() but it dosent work for some reason...
                    # data_src_dest[key1][key2].rawData.dropna(inplace = True)
                    # compute alltime values
                    data_src_dest[key1][key2].calculate_all_time_vars()
                    # cut raw data to not bloat the memory
                    # after this the memory usage per dataFrame should be at 768 bytes
                    # this makes about 11 mb at 15,000 connections for all raw_data frames
                    data_src_dest[key1][key2].cut_raw_data()
                    # smooth data
                    data_src_dest[key1][key2].smooth_raw_data_if_appropriate()
                    # calculate predictions
                    data_src_dest[key1][key2].calculate_predictions(nn_model, nn_scaler)
            reading_messages_and_calcing_time += time.time() - startTime

            # "send out" predictions
            # this still needs some "polishing"
            for key1 in data_src_dest.keys():
                for key2 in data_src_dest[key1].keys():
                    if data_src_dest[key1][key2].was_updated == False:
                        continue
                    # make sure there is actually a prediction in there
                    if data_src_dest[key1][key2].has_prediction == True:
                        orig_meta = data_meta_header_src_dest[key1][key2]['meta']
                        orig_header = data_meta_header_src_dest[key1][key2]['header']
                        msg_out = data_src_dest[key1][key2].generate_output_message(orig_header, orig_meta,
                                                                                    local_IP=local_IP)
                        mq_output.add_message(msg_out)
                        msg_counter += 1
                    data_src_dest[key1][key2].was_updated = False

            # so some house keeping
            deltaTime = time.time() - startTime
            messages_sum += numMessages
            total_used_time += deltaTime
            statistics_counter += 1
            if (statistics_counter % 10) == 0:
                # print some statistics
                count_conns = 0
                count_full_conns = 0
                for key1 in data_src_dest.keys():
                    for key2 in data_src_dest[key1].keys():
                        count_conns += 1
                        if len(data_src_dest[key1][key2].rawData) >= 32:
                            count_full_conns += 1
                messages_per_sec = messages_sum / total_used_time
                reading_messages_percentage = (reading_messages_time / total_used_time) * 100
                calculating_percentage = ((
                                              reading_messages_and_calcing_time - reading_messages_time) / total_used_time) * 100
                sending_messagespercentage = 100 - (reading_messages_percentage + calculating_percentage)
                stat_msg = "Current statistics:"
                stat_msg += "\n | Total connections seen: " + str(count_conns)
                stat_msg += " | Connections with full buffers: " + str(count_full_conns) + " (" + str(round(100*(count_full_conns/count_conns))) + " %)"
                stat_msg += "\n | Messages read: " + str(messages_sum)
                stat_msg += " | Messages sent: " + str(msg_counter)
                stat_msg += "\n | Average processing speed: " + str(messages_per_sec) + " [messages/sec]"
                stat_msg += "\n | Time spent reading messages: " + str(reading_messages_time) + " [sec] (" + str(
                    round(reading_messages_percentage)) + " %)"
                stat_msg += " | Time spent calculating: " + str(
                    reading_messages_and_calcing_time - reading_messages_time) + " [sec] (" + str(
                    round(calculating_percentage)) + " %)"
                stat_msg += "\n | Time spent sending messages: " + str(
                    total_used_time - reading_messages_and_calcing_time) + " [sec] (" + str(
                    round(sending_messagespercentage)) + " %)"
                log.info(stat_msg)
                # reset statistics
                messages_sum = 0
                statistics_counter = 0
                reading_messages_time = 0
                reading_messages_and_calcing_time = 0
                total_used_time = 0
                msg_counter = 0
                # clean the dirqs
                mq.purge()
                mq_output.purge()
                error_counter = 0  # if we made it till here, clear our error_counter
            time.sleep(1)
            # be carefull! this will as well catch interrupts from the notebook, so that the cell just keeps running!
            # except:
            #    if error_counter == 10:
            #        log.error("Experienced 10 unexpected errors in a row - Exiting now.")
            #        exit(1)
            #    log.warning("An unexpected error occured - Restarting. ")
            #    error_counter += 1
            #    log.info("Deleting left over messages and clearing buffers")
            #    for name in mq:
            #       if mq.lock(name):
            #          mq.remove(name)
            #    data_src_dest = {}


    # ------------------ Helper Functions ------------------

    def read_latest_messages(self, mq, base_data_raw_src_dest={}, base_data_meta_header_src_dest={}, delete_messages_after_reading=True):
        data_meta_header_src_dest = base_data_meta_header_src_dest
        data_src_dest = base_data_raw_src_dest
        for name in mq:
            if mq.lock(name):
                msg = mq.get_message(name)
                msgBody = json.loads(msg.get_body())
                src = str(msgBody["meta"]["source"])
                dest = str(msgBody["meta"]["destination"])
                # check if we have saved the stuff
                if src not in data_src_dest.keys():
                    data_src_dest[src] = {}
                    data_meta_header_src_dest[src] = {}
                if dest not in data_src_dest[src].keys():
                    data_src_dest[src][dest] = DataStore()
                    data_meta_header_src_dest[src][dest] = {}
                if str(msg.get_header()['destination']) == '/topic/perfsonar.raw.histogram-owdelay':
                    # do stuff for the owd
                    data_src_dest[src][dest].rawData = self.readOWDMessage(msgBody, base_data=data_src_dest[src][dest].rawData)
                else:
                    # do stuf for the packet loss
                    data_src_dest[src][dest].rawData = self.readPacketloss(msgBody, base_data=data_src_dest[src][dest].rawData)
                # mark the data as updated
                data_src_dest[src][dest].was_updated = True
                # save the metadata, we will reuse it later
                data_meta_header_src_dest[src][dest]['meta'] = msgBody["meta"]
                data_meta_header_src_dest[src][dest]['header'] = msg.get_header()
                if delete_messages_after_reading:
                    mq.remove(name)
                else:
                    mq.unlock(name)
        return data_src_dest, data_meta_header_src_dest


    def readPacketloss(self, message_body, base_data=pd.DataFrame(), appendix=""):
        data = base_data.copy(deep=True)
        for timestomp in message_body['datapoints'].keys():
            timestamp_epoch = int(timestomp)
            data.set_value(timestamp_epoch, "packet_loss"+appendix,
                           float(message_body['datapoints'][timestomp]))
        data = data.sort_index(ascending=False)
        return data

    def readOWDMessage(self, message_body, base_data=pd.DataFrame(), appendix=""):
        data = base_data.copy(deep=True)
        for timestomp in message_body['datapoints'].keys():
            timestamp_epoch = int(timestomp)
            avgStdMedian = self.getAvgStdMedianFromHistogram(message_body['datapoints'][timestomp])
            data.set_value(timestamp_epoch, "delay_avg"+appendix, avgStdMedian[0])
            data.set_value(timestamp_epoch, "delay_std"+appendix, avgStdMedian[1])
            data.set_value(timestamp_epoch, "delay_median"+appendix, avgStdMedian[2])
        data = data.sort_index(ascending=False)
        return data

    def getAvgStdMedianFromHistogram(self, hitogram_dict):
        histogram = np.array(hitogram_dict.items(), float)
        values, weights_out = np.split(histogram, 2, axis=1)
        avg = np.average(values, weights=weights_out)
        std = np.sqrt(np.average((values-avg)**2, weights=weights_out))
        summ = np.cumsum(weights_out)
        index = np.searchsorted(summ, summ[len(summ)-1]/2)
        median = values[index][0]
        return avg, std, median



