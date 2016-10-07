from __future__ import print_function
from __future__ import division
import json
import numpy as np
import pandas as pd
import time
import math
import threading
from messaging.message import Message


class DataStore:
    smoothing_steps = 15
    NN_num_of_last_measurements = 15
    filter_delay_std_adjustor = 1
    filter_min_packet_loss = 0.0001
    designated_num_of_cols = 4  # numbers of rows in your rawData dataframe
    num_of_max_counts = 1e11  # determits how often the all time values are reset

    def __init__(self):
        self.was_updated = True
        self.contains_smoothed_data = False
        self.rawData = pd.DataFrame()
        self.smoothedData = pd.DataFrame()
        self.delay_all_time_avg = 0
        self.delay_all_time_std = 0
        self.delay_all_time_min = 9999999999999
        self.loss_all_time_avg = 0
        self.loss_all_time_std = 0
        self._sumdelay = 0
        self._sumdelay_square = 0
        self._sumloss = 0
        self._sumloss_square = 0
        self._sumdelay_backup = 0
        self._sumdelay_square_backup = 0
        self._sumloss_backup = 0
        self._sumloss_square_backup = 0
        self._sum_counter = 0
        self._sum_lastTimestamp = 0
        self.prediction_empirical = 0
        self.prediction_nn = 0
        self.has_prediction = False
        self.lock = threading.Lock()

    def calculate_all_time_vars(self):
        # the data is already sorted, so no need to worry about anything
        if (self.was_updated == False) or (len(self.rawData.axes[1]) < self.designated_num_of_cols):
            return
        # drop unusable data
        self.rawData.dropna(inplace=True)
        # if we emptied the frame return
        if len(self.rawData) == 0:
            return
        # find minimum
        currentMin = self.rawData['delay_avg'].min()
        if self.delay_all_time_min > currentMin:
            self.delay_all_time_min = currentMin
        # find last timestamp
        loc = self.rawData.index.get_loc(self._sum_lastTimestamp, method='nearest')
        if loc == 0:
            return
        # calc sums
        for i in xrange(loc):
            delay = self.rawData.iloc[i]['delay_avg']
            loss = self.rawData.iloc[i]['packet_loss']
            self._sumdelay += delay
            self._sumdelay_square += delay ** 2
            self._sumloss += loss
            self._sumloss_square += loss ** 2
            self._sum_counter += 1
            # make sure we reset the all time values at some point
            if self._sum_counter > self.num_of_max_counts:
                self._sumdelay_backup += delay
                self._sumdelay_square_backup += delay ** 2
                self._sumloss_backup += loss
                self._sumloss_square_backup += loss ** 2
                if self._sum_counter >= (self.num_of_max_counts + 50):
                    self._sumdelay = self._sumdelay_backup
                    self._sumdelay_square = self._sumdelay_square_backup
                    self._sumloss = self._sumloss_backup
                    self._sumloss_square = self._sumloss_square_backup
                    self._sum_counter = 50
                    # calc avg and stds
        self.delay_all_time_avg = self._sumdelay / self._sum_counter
        self.delay_all_time_std = np.sqrt(
            (self._sumdelay_square / self._sum_counter) - (self._sumdelay / self._sum_counter) ** 2)
        self.loss_all_time_avg = self._sumloss / self._sum_counter
        self.loss_all_time_std = np.sqrt(
            (self._sumloss_square / self._sum_counter) - (self._sumloss / self._sum_counter) ** 2)
        # get latest timestamp
        self._sum_lastTimestamp = self.rawData.index[0]

    def smooth_raw_data_if_appropriate(self):
        # skip inclomplete dataFrames and those that have not been updated
        if (self.was_updated == False) or (len(self.rawData) < (self.smoothing_steps * 2 + 2)) or (
                    len(self.rawData.axes[1]) < self.designated_num_of_cols):
            self.contains_smoothed_data = False
            return
        self.smoothedData = self._smoothDataFrame_simplifyedMod(self.rawData, self.smoothing_steps)
        # add the gradient for delay_avg and packetloss
        # if we need more speed over here we can first: change edge_order from 2 to 1
        # or secondly remove it completly and train the NN again...
        self.smoothedData['delay_avg_gradient'] = np.gradient(self.smoothedData['delay_avg'], edge_order=2)
        self.smoothedData['packet_loss_gradient'] = np.gradient(self.smoothedData['packet_loss'], edge_order=2)
        self.contains_smoothed_data = True

    def _smoothDataFrame_simplifyedMod(self, data, steps):
        # make sure that there are no nans! This would brick the cumsum function!
        # This may happen naturally when the packet_loss is at 1, so no packets get through
        # for simplicity we will drop those lines
        data_smired = data.copy(deep=True)
        data_smired = data_smired.dropna()
        for col in data_smired.axes[1]:
            vals = data_smired[col].values
            valsSumed = np.cumsum(vals)
            for i in range(steps, len(data_smired)):
                summ = valsSumed[i] - valsSumed[i - steps]
                vals[i] = summ / steps
            data_smired[col] = vals
        # make sure not to use the first values, which were not averaged, e.g. delete them
        data_smired = data_smired.drop(data_smired.index[:steps])
        return data_smired

    def cut_raw_data(self):
        if len(self.rawData) <= (self.smoothing_steps * 2 + 2):
            return
        self.rawData.drop(self.rawData.index[(self.smoothing_steps * 2 + 1): len(self.rawData) - 1],
                          inplace=True)

    def _make_nn_input_scaled(self, nn_scaler):
        if len(self.smoothedData) < 16:
            return
        zw = dict(self.smoothedData.iloc[0])
        # include all time data
        zw['delay_all_time_avg'] = self.delay_all_time_avg
        zw['delay_all_time_std'] = self.delay_all_time_std
        zw['delay_all_time_min'] = self.delay_all_time_min
        zw['loss_all_time_avg'] = self.loss_all_time_avg
        zw['loss_all_time_std'] = self.loss_all_time_std

        # add last measurements
        sumdelay = 0
        sumdelay_square = 0
        sumloss = 0
        sumloss_square = 0
        for j in range(1, self.NN_num_of_last_measurements + 1):
            dataPoint = self.smoothedData.iloc[j]
            zw['delay_avg_past_' + str(j)] = dataPoint['delay_avg']
            sumdelay += dataPoint['delay_avg']
            sumdelay_square += dataPoint['delay_avg'] * dataPoint['delay_avg']
            zw['packet_loss_past_' + str(j)] = dataPoint['packet_loss']
            sumloss += dataPoint['packet_loss']
            sumloss_square += dataPoint['packet_loss'] * dataPoint['packet_loss']
        zw['delay_avg_past_avg'] = sumdelay / self.NN_num_of_last_measurements
        zw['packet_loss_past_avg'] = sumloss / self.NN_num_of_last_measurements
        zw['delay_avg_past_std'] = np.sqrt(
            (sumdelay_square / self.NN_num_of_last_measurements) - (sumdelay / self.NN_num_of_last_measurements) ** 2)
        zw['packet_loss_past_std'] = np.sqrt(
            (sumloss_square / self.NN_num_of_last_measurements) - (sumloss / self.NN_num_of_last_measurements) ** 2)
        if math.isnan(zw['packet_loss_past_std']):
            zw['packet_loss_past_std'] = 0
        if math.isnan(zw['delay_avg_past_std']):
            zw['delay_avg_past_std'] = 0

        nn_input = pd.DataFrame.from_dict([zw])
        # we might need the upper one, but we shouldn't...
        # normalizeDataSet(nn_input, scaler=nn_scaler)
        # maybe we can skipp the .as_matrix() here and just leave it out
        nn_input_scaled = nn_scaler.transform(nn_input.as_matrix())
        return nn_input_scaled

    def calculate_predictions(self, nn_model, nn_scaler):
        if (self.was_updated == False) or (self.contains_smoothed_data == False):
            return
        # calculate empirical model
        # set to 0 if packet_loss or delay are to small
        if self.smoothedData.iloc[0]['packet_loss'] < self.filter_min_packet_loss:
            self.prediction_empirical = 0
        elif self.smoothedData.iloc[0]['delay_avg'] < (
                        self.delay_all_time_std * self.filter_delay_std_adjustor + self.delay_all_time_min):
            self.prediction_empirical = 0
        else:
            self.prediction_empirical = np.absolute(
                self.smoothedData.iloc[0]['packet_loss'] * self.smoothedData.iloc[0]['delay_avg'])

        # self.prediction_empirical = self.smoothedData.iloc[0]['delay_avg']
        # calculate NN
        nn_input_scaled = self._make_nn_input_scaled(nn_scaler)
        prediction = nn_model.predict(nn_input_scaled, batch_size=32)
        # scale it back between 0 and 1
        self.prediction_nn = ((prediction[0][0]) - 0.1) / 0.8
        self.has_prediction = True

    def generate_output_message(self, header, meta, local_IP='127.0.0.1'):
        # create message
        # copy usefull information from header
        timestamp = int(time.time())
        output_header = {'event-type': 'telemetry.perfsonar',
                         'destination': '/topic/telemetry.perfsonar',
                         'gmt-timestamp': str(timestamp),
                         'timestamp': str(timestamp),
                         'summaries': '1',
                         'input-destination': header['input-destination'],
                         'input-source': header['input-source']}
        # copy usefull information from the meta
        output_meta = {'destination': meta['destination'],
                       'input_destination': meta['input_destination'],
                       'input_source': meta['input_source'],
                       'ip_transport_protocol': 'udp',
                       'measurement_agent': str(local_IP),
                       'source': meta['source'],
                       'subject_type': meta['subject_type'],
                       'time_duration': str(60),
                       'tool_name': 'netTel'}
        output_summaries = [{'event_type': 'telemetry.perfsonar',
                             'summary_window': str(60),
                             'summary_type': 'statistics',
                             'summary_data': [[timestamp, {'ml': str(self.prediction_nn),
                                                           'empirical': str(self.prediction_empirical)}]]
                             }]
        output_body = {'meta': output_meta,
                       'summaries': output_summaries}
        output_body_json = json.dumps(output_body)
        msg_out = Message(body=output_body_json, header=output_header)
        return msg_out
