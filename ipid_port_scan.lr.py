#!/usr/bin/env python3
from numpy import array, asarray
import numpy as np
from ipid_prediction_lib import *
from sklearn.metrics import mean_squared_error
from math import sqrt
from sklearn import datasets, preprocessing
import time
import decimal
import threading
from ctypes import *
import concurrent.futures
import pandas as pd
import math
import statistics
from scipy.stats import norm, linregress
import random
import csv
import logging
from sklearn import linear_model

#import seaborn as sns
#import matplotlib.pyplot as plt

#cols = sns.color_palette("colorblind")
#sns.set_theme(style="darkgrid")

class go_string(Structure):
    _fields_ = [
        ("p", c_char_p),
        ("n", c_int)]
        

def extract(string_arr):
	arr = []
	matches = re.findall(regex, string_arr)
	for match in matches:
		arr.append(int(match))
	return arr

def modify(times):
	start = times[0]
	i = 0
	for time in times:
		times[i] = int(round(float(time - start)/1000000.0))
		i+=1
	return times

def computeIpidVelocity(ids, times, MAX):

	spd = float(0)

	for i in range(0, len(ids)-1):
		
		gap = float(rela_diff(ids[i], ids[i+1], MAX))
		#dur = float(times[i+1]-times[i])/1000000000.0 #unit: ID/s
		dur = float(times[i+1]-times[i])
		spd += gap/dur
	
	spd /= float(len(ids)-1)
	
	return round(spd, 3)

def computeIpidVelocity02(ids, times, MAX):
	id_seg = list()
	time_seg = list()
	vels = list()
	for i in range(len(ids)):
		id_seg.append(ids[i])
		time_seg.append(times[i])
		if len(id_seg) == 3:
			vel = computeIpidVelocity(id_seg, time_seg, MAX)
			vels.append(vel)
			id_seg = []
			time_seg = []
	return np.median(vels)

def computeIpidVelocitySeg(ids, times, MAX):
	id_segment = []
	time_segment = []
	vels = []
	for i in range(len(ids)):
		if math.isnan(ids[i]):
			if len(id_segment) >= 3:
				vel = computeIpidVelocity(id_segment, time_segment, MAX)
				vels.append(vel)
			id_segment = []
			time_segment = []
			continue
		id_segment.append(ids[i])
		time_segment.append(times[i])
	if len(id_segment) >= 3: # without NAN
		vel = computeIpidVelocity(id_segment, time_segment, MAX)
		vels.append(vel)
	if len(vels) == 2 and len(id_segment) > len(ids)/2: return vels[1]
	return np.median(vels)

def computeIpidVelocityNan(ids, times, MAX):
	id_segment = []
	time_segment = []
	for i in range(len(ids)):
		if math.isnan(ids[i]):
			continue
		id_segment.append(ids[i])
		time_segment.append(times[i])
	vel = computeIpidVelocity(id_segment, time_segment, MAX)
	return vel

def count_ipid_wraps(data):
	count = 0
	for i in range(0, len(data)-1):
		if data[i+1]-data[i] < 0:
			count = count + 1
	return count

def series_to_supervised(data, n_in=1, n_out=1, dropnan=True):
	n_vars = 1 if type(data) is list else data.shape[1]
	df = DataFrame(data)
	cols = list()
	# input sequence (t-n, ... t-1)
	for i in range(n_in, 0, -1):
		cols.append(df.shift(i))
	
	# forecast sequence (t, t+1, ... t+n)
	for i in range(0, n_out):
		cols.append(df.shift(-i))
	
	# put it all together
	agg = concat(cols, axis=1)
	#print(agg)
	# drop rows with NaN values
	if dropnan:
		agg.dropna(inplace=True)
	return agg.values
	
def obtain_restore_data(sequence, diff_data):
	base_data = list()
	restore_data = list()
	for i in range(3, len(diff_data)):
		if math.isnan(diff_data[i-3]+diff_data[i-2]+diff_data[i-1]+diff_data[i]): continue
		base_data.append(sequence[i])
		restore_data.append(sequence[i+1])
	return base_data, restore_data
 
# split a univariate dataset into train/test sets
def train_test_split(data, n_test):
	return data[:-n_test, :], data[-n_test:, :]

# split a univariate sequence into samples
def split_sequence(sequence, n_steps):
	X, y = list(), list()
	for i in range(len(sequence)-n_steps):
		# find the end of this pattern
		end_ix = i + n_steps
		# gather input and output parts of the pattern
		seq_x, seq_y = sequence[i:end_ix], sequence[end_ix]
		X.append(seq_x)
		y.append(seq_y)
	return array(X), array(y)
	
def sMAPE02(chps_ind, actual, predictions):
	res = list()
	for i in range(len(actual)):
		if i in chps_ind and abs(predictions[i]-actual[i]) > 30000:
			if predictions[i] < actual[i]:
				predictions[i] = predictions[i] + 65536
				#res.append(2 * abs(pre-actual[i]) / (actual[i] + pre))
			else:
				actual[i] = actual[i] + 65536
				#res.append(2 * abs(predictions[i]-ac) / (ac + predictions[i]))
			continue
		if  (actual[i] + predictions[i]) !=0:
			if (actual[i] + predictions[i]) <0: continue
			res.append(2 * abs(predictions[i]-actual[i]) / (actual[i] + predictions[i]))
		else:
			res.append(0)
	after_res = list()
	for v in res:
		if math.isnan(v): continue
		after_res.append(v)
	return np.mean(after_res)

def MAPE(chps_ind, actual, predictions):
	res = list()
	for i in range(len(actual)):
		if i in chps_ind and abs(predictions[i]-actual[i]) > 30000:
			if predictions[i] < actual[i]:
				pre = predictions[i] + 65536
				res.append(abs(pre-actual[i]) / actual[i])
			else:
				ac = actual[i] + 65536
				res.append(abs(predictions[i]-ac) / ac )
			continue
		if  (actual[i] + predictions[i]) !=0:
			if (actual[i] + predictions[i]) <0: continue
			res.append(abs(predictions[i]-actual[i]) / actual[i])
		else:
			res.append(0)
	after_res = list()
	for v in res:
		if math.isnan(v): continue
		after_res.append(v)
	return np.mean(after_res)
	
def filter_outliers01(outlier, sequence, thr, MAX):
	indices = list()
	new_window = [i for i in sequence]
	if not outlier: return new_window
	index = 0
	for i in range(index, len(new_window)-2):
		mini_window = [new_window[i], new_window[i+1], new_window[i+2]]
		if containNAN(mini_window): continue
		delta1 = rela_diff(new_window[i], new_window[i+1], MAX)
		delta2 =  rela_diff(new_window[i+1], new_window[i+2], MAX)
		
		if delta1 > thr or delta2 > thr: # suitable for two consecutive outliers
			mini_window = array(mini_window)
			med = np.median(mini_window)
			mini_window = abs(mini_window - med)
			max_index = max( (v, i) for i, v in enumerate(mini_window) )[1]
			if i+max_index == 0: # process the outliers detected
				new_window[i+max_index]  = new_window[1]
			else:
				new_window[i+max_index] = new_window[i+max_index-1]
			indices.append(i+max_index)
			if len(indices) >= 3: ## if the number of consecutive outliers is more than three, then the change will be viewed as normal
				if indices[-2]-indices[-3] == 1 and indices[-1]-indices[-2] == 1:
					new_window = [i for i in sequence]
					index = indices[-1] + 1
	return new_window

def filter_outliersv2(outlier, sequence, thr, MAX, actual, outlier_ind):
	change = False
	new_window = [i for i in sequence]
	if not outlier: return new_window, change
	if len(actual) == len(new_window):
		n = 0
	else:
		n = len(new_window)-3
	for i in range(n, len(new_window)-2):
		mini_window = [new_window[i], new_window[i+1], new_window[i+2]]
		if containNAN(mini_window): continue
		if alarm_turning_point(thr, mini_window[0], mini_window[1], MAX):
			mini_window[1] = (mini_window[1] + MAX) 
		if alarm_turning_point(thr, mini_window[1], mini_window[2], MAX):
			mini_window[2] = (mini_window[2] + MAX) 
		delta1 = rela_diff(mini_window[0], mini_window[1], MAX)
		delta2 =  rela_diff(mini_window[1], mini_window[2], MAX)
		if delta1 > thr or delta2 > thr: # suitable for two consecutive outliers
			mini_window = array(mini_window)
			med = np.median(mini_window)
			mini_window = abs(mini_window - med)
			max_index = max( (v, i) for i, v in enumerate(mini_window) )[1]
			
			if i+max_index == 0: # process the outliers detected
				new_window[i+max_index]  = new_window[1]
			else:
				new_window[i+max_index] = new_window[i+max_index-1]
			outlier_ind.append(len(actual)-len(new_window)+i+max_index)
			if len(outlier_ind) >= 3:	
				if (outlier_ind[-1] - outlier_ind[-2]) == 1 and (outlier_ind[-2] - outlier_ind[-3]) == 1 :
						new_window[i] = actual[i+len(actual)-len(new_window)]
						new_window[i+1] = actual[i+1+len(actual)-len(new_window)]
						new_window[i+2] = actual[i+2+len(actual)-len(new_window)]
						outlier_ind.clear()
						change = True
	return new_window, change
	
	
def alarm_turning_point(thr, a1, a2, MAX):
	alarm = False
	delta = a2 - a1 
	if delta < 0 and rela_diff(a1, a2, MAX) < thr: # a2-a1+MAX approximates to a2 (close to 1 in ideal)
		alarm = True
	return alarm
	

def eliminate_trans_error(chps_ind, actual, predictions):
	diff = list()
	for i in range(len(actual)):
		if i in chps_ind and abs(predictions[i]-actual[i]) > 30000: # if the turning point is predicted with a prior second, then the main prediction error is on the upper turining point, otherwise, th error is on the lower turning point.
			if predictions[i] < actual[i]:
				diff.append(predictions[i]-actual[i] + 65536)
			else:
				diff.append(predictions[i]-actual[i] - 65536)
			continue
		diff.append(predictions[i]-actual[i])
	return diff

def containNAN(data):
	for i in range(len(data)):
		if math.isnan(data[i]): return True
	return False

def countNans(data):
	num = 0
	for i in range(len(data)-2):
		if math.isnan(data[i]):
			if math.isnan(data[i+1]) and math.isnan(data[i+2]):
				num = 3
				return num
	return num
	

def filter_outliers(outliers, thr, history, MAX):
	data = filter_outliers01(outliers, history, thr, MAX)
	return data

def data_preprocess(thr, history, MAX):
	data = [i for i in history]
	wraps = list()
	for i in range(len(data)-1):
		if data[i+1] - data[i] < 0 and rela_diff(data[i], data[i+1], MAX) < thr:
			wraps.append(i+1)
	for _, i in enumerate(wraps):
		for t in range(i, len(data)):
			data[t] = data[t] + MAX
	return wraps, data
		
def one_time_forecast(data, times, ntime, k, predictions, MAX):
	X = np.array(times).reshape(-1, 1)
	y = np.array(data)
	model = linear_model.LinearRegression().fit(X, y)
	nt = np.array(ntime).reshape(-1, 1)
	y_pred = model.predict(nt)[0] - MAX*k
	predictions.append(y_pred)


def group_ips_measure(ips, protocol, port, domains, dst_ip, dst_port, l, spoof, dataset):
	for ip, ns in zip(ips, domains):
		single_port_scan(ip, protocol, port, ns, dst_ip, dst_port, l, spoof, dataset)
		
def probe(ipv4, protocol, flag, port, ns):
	ipv4 = bytes(ipv4, 'utf-8')
	protocol = bytes(protocol, 'utf-8')
	flag = bytes(flag, 'utf-8')
	ns = bytes(ns, 'utf-8')
	ip = go_string(c_char_p(ipv4), len(ipv4))
	proto = go_string(c_char_p(protocol), len(protocol))
	flag = go_string(c_char_p(flag), len(flag))
	ns = go_string(c_char_p(ns), len(ns))
	
	a = lib.probe(ip, proto, flag, port, ns)
	return a
		
def spoofing_probe(ipv4, protocol, port, ns, dst_ip, dst_port, n):
	ipv4 = bytes(ipv4, 'utf-8')
	protocol = bytes(protocol, 'utf-8')
	ns = bytes(ns, 'utf-8')
	dst_ip = bytes(dst_ip, 'utf-8')
	
	ip = go_string(c_char_p(ipv4), len(ipv4))
	proto = go_string(c_char_p(protocol), len(protocol))
	ns = go_string(c_char_p(ns), len(ns))
	dst_ip = go_string(c_char_p(dst_ip), len(dst_ip))
	
	lib.spoofing_probe(ip, dst_ip, proto, port, dst_port, ns, n) #port: reflector port

def spoofing_samples(diff_data):
	x = np.max(diff_data, axis=-1) #when the estimated error is the maximum of previous errors, maybe an abnormal value when there is ana outlier
	u = np.mean(diff_data)
	s = np.std(diff_data)
	n = 0
	#if s == 0: # to keep the trend monotonously increasing
	#	n = 5
	#else:
	n = 1+int(4*s+x-u) #2.06,
	
	return n, u, s
	
def is_open_port(u, s, e, n):
	if s == 0:
		if abs(e) >= n: return True
		else: return False
	
	v = (e-u)/s
	if norm.cdf(v) > 0.98 or norm.cdf(v) < 0.02: # p = 0.02
		return True
	return False


def test_dst_port(ip, protocol, flag, port, ns):
	count = 0
	status = 'open'
	for i in range(3):
		ipid = probe(ip, protocol, flag, port, ns)
		if ipid == -1: count = count+1
	if count == 3:
		status = 'closed'
	return status
	
def single_port_scan(ip, protocol, port, ns, dst_ip, dst_port, plth, spoof, dataset):
	code = 0
	count = 0
	for i in range(2):
		ipid = probe(ip, protocol, 'SA', port, ns)
		if ipid == -1: count = count+1
	if count == 2:
		logging.info('Unreachable: {a}'.format(a= ip))
		code = 1
		return code, dst_ip
	
	astatus = test_dst_port(dst_ip, protocol, 'S', dst_port, ns)
	#astatus = ''
	if astatus == 'open': ##need to be updated when no open
		logging.info('Open: {a}'.format(a= dst_ip))
		code = 1
		return code, dst_ip
	
	sliding_window = list()
	wlth = 5
	#plth = 30
	ipids = list()
	actual = list()
	predictions = list() 
	chps_ind = list()
	outlier_ind = list()
	tem_actual = list()

	mae, smape, n, u, s = 0.0, 0.0, 0, 0.0, 0.0
	while True:
		ipid = probe(ip, protocol, 'SA', port, ns)
		start = time.monotonic()
		ipids.append(ipid)	
		if ipid == -1: ipid = math.nan
		sliding_window.append(ipid)
		tem_actual.append(ipid)
		if len(sliding_window) == wlth+1: 
			actual.append(sliding_window[-1])
			sliding_window.pop(0)
		if len(predictions) == plth-1:
			diff = eliminate_trans_error(chps_ind, actual, predictions)
			after_diff = list()
			for v in diff:
				if math.isnan(v): continue
				after_diff.append(v)
			
			if len(after_diff) < (plth-1) * 0.7:
				logging.info('Invalid: {a}'.format(a= ip))
				code = 1
				return code, dst_ip
			mae = np.mean(abs(array(after_diff)))
			smape = sMAPE02(chps_ind, actual, predictions)
			n, u, s = spoofing_samples(after_diff)
			#f.write(ip+','+str(smape)+','+str(n)+'\n')
			if n > 10 or n < 1 :
				logging.info('n>10, require retest: {a}'.format(a= ip)) # 10
				code = 1
				return code, dst_ip
			if spoof:
				spoofing_probe(ip, protocol, port, ns, dst_ip, dst_port, n) # port should be random
				#spoofing_probe(dst_ip, protocol, dst_port, ns, ip, port, n) #test_pred_n, port should be random
				
		if len(sliding_window) == wlth:
			count = 0
			for x in sliding_window:
				if math.isnan(x): count = count + 1
			if count/wlth > 0.5:
				predictions.append(math.nan)
				end = time.monotonic()
				elapsed = end-start
				#lambda elapsed:  time.sleep(1-elapsed) if elapsed < 1 else time.sleep(0)
				time.sleep(1)
				continue
			times = list()
			for i in range(len(sliding_window)):
				times.append(i)
			tHistory = times
			MAX = 65536
			
			outlier = True
			
			if containNAN(sliding_window):
				vel = computeIpidVelocityNan(sliding_window, list(range(len(sliding_window))), MAX)
			else:
				vel = computeIpidVelocity02(sliding_window, list(range(len(sliding_window))), MAX) # eliminate the outliers' impact
			
			if vel < 1000: thr = 15000 # experimentially specify the threshold
			else: thr = 30000
			if vel > 10000: outlier = False # For high fluctuating
			
			if len(predictions) > 1  and  alarm_turning_point(thr, tem_actual[-2], tem_actual[-1], MAX):
					chps_ind.append(i-2)
					chps_ind.append(i-1)
					
			if len(predictions) == plth: break # Update!!!
			
			sliding_window = fill_miss_values(sliding_window) 
			
			sliding_window, _ = filter_outliersv2(outlier, sliding_window, thr, MAX, tem_actual, outlier_ind)
			
			wraps, new_window = data_preprocess(thr, sliding_window, MAX) # identify the truning point and make a preprocessing
			k = len(wraps)
			ntime = tHistory[-1]+1
			one_time_forecast(new_window, tHistory, ntime, k, predictions, MAX)
			if predictions[-1] < 0: predictions[-1] = 0
			
		end = time.monotonic()
		elapsed = end-start
		#lambda elapsed:  time.sleep(1-elapsed) if elapsed < 1 else time.sleep(0)
		time.sleep(1)
	diff = eliminate_trans_error(chps_ind, actual, predictions)
	if math.isnan(diff[-1]):
		logging.info('Packet loss: {a}'.format(a= ip))
		code = 1
		return code, dst_ip
	err = diff[-1] # err is always negative.
	status = None
		
	if is_open_port(u, s, err, n): 
		status = 'open port'
	else:
		status = 'closed or filtered port!'
	
	dataset['ip'].append(ip)
	dataset['mae'].append(mae)
	dataset['smape'].append(smape)
	dataset['n'].append(n)
	dataset['status'].append(status)
	dataset['dst_ip'].append(dst_ip)
	dataset['astatus'].append(astatus)
	#print(ip, dst_ip, status, astatus)
	logging.info('{a} | {b} | {c} | {d}'.format(a= ip, b = dst_ip, c = actual, d = predictions))
	return code, dst_ip
		
def fill_miss_values(data):
	s = pd.Series(data)
	s = s.interpolate(method='pad')
	return (s.interpolate(method='linear', limit_direction ='both').values % 65536).tolist()
	

lib = cdll.LoadLibrary("./ipid_pred_lib.so")
logging.basicConfig(level=logging.INFO, filename='./ipid_port_scan.lr.web_servers.p44345.log')
#f = open('./ipid_port_scan.lr.test_pred_n.res', 'w')
def main():
	start = time.monotonic()
	fast_scan()
	end = time.monotonic()
	logging.info('Total of time: {a}'.format(a = (end-start)/60))

def test_pred_n():
	ips_list = list()
	domains_list = list()
	ips = list()
	domains = list()
	with open('./lr.reflectors.(low).res', 'r') as filehandle: # ./lr.reflectors.(low).res, scan_target_reflectors.res
		filecontents = filehandle.readlines()
		for line in filecontents:
			fields = line.split(",")
			if len(fields) < 1 : continue
			domain = ''
			ip = fields[0] 
			domains.append(domain)
			ips.append(ip)
			if len(ips) == 10: #10
				ips_list.append(ips)
				domains_list.append(domains)
				ips = list()
				domains = list()
	ips_list.append(ips)
	domains_list.append(domains)
	protocol = 'tcp'
	#port = random.randrange(10000, 65535, 1) 
	port = 80
	dst_ip = '199.244.49.62'
	dst_port = 80
	dataset = {
	'ip': [],
	'mae': [], 
	'smape': [],
	'n': [],
	'dst_ip': [],
	'status': [],
	'astatus': [],
	}
	
	with concurrent.futures.ThreadPoolExecutor(max_workers=100) as executor:
		futures = []
		for ips, domains in zip(ips_list, domains_list):
			futures.append(executor.submit(group_ips_measure, ips, protocol, port, domains, dst_ip, dst_port, 30, False, dataset))
		for future in concurrent.futures.as_completed(futures):
			print('Done!')
	df = pd.DataFrame(dataset)
	df.to_csv('./ipid_port_scan.lr.no.spoofing.res', index=False)
	
	
def start_measure(reflectors, webservers, dataset):
	protocol = 'tcp'
	port = random.randrange(10000, 65535, 1)
	ns = ''
	dst_port = 44345
	#dst_port = 80
	#dst_port = 22
	with concurrent.futures.ThreadPoolExecutor(max_workers=100) as executor:
		futures = []
		for ip, dst_ip in zip(reflectors,webservers):
			futures.append(executor.submit(single_port_scan, ip, protocol, port, ns, dst_ip, dst_port, 30, True, dataset))
		for future in concurrent.futures.as_completed(futures):
			code, dst_ip = future.result()

def fast_scan():
	
	n = 100
	reflectors = list() 
	with open('./scan_target_reflectors.merged.res') as f1: ## less than 10 sampled packets
		filecontents = f1.readlines()
		for line in filecontents:
			fields = line.split(",")
			if len(fields) < 1 : continue
			ip = fields[0].strip('\n')
			reflectors.append(ip)
	webservers = list()
	
	dataset = {
		'ip': [],
		'mae': [], 
		'smape': [],
		'n': [],
		'dst_ip': [],
		'status': [],
		'astatus': [],
	}
	random.shuffle(reflectors) # randomly resorted
	with open('./webserver_ips.target.data') as f2: #./lr.fast_scan.p80.fn.res.res webserver_ips.target.data
		filecontents = f2.readlines()
		for line in filecontents:
			fields = line.split(",")
			if len(fields) < 1 : continue
			ip = fields[0].strip('\n')
			webservers.append(ip)
			if len(webservers) == n:
				subwindow = reflectors[0:n]
				reflectors = reflectors[n:] + subwindow ## pop the prior 100 servers and push them at the end of the previous reflectors window
				start_measure(subwindow, webservers, dataset)
				webservers.clear()
				continue
		if len(webservers) > 0: 
			subwindow = reflectors[0:len(webservers)]
			start_measure(subwindow, webservers, dataset)
	df = pd.DataFrame(dataset)
	df.to_csv('./ipid_port_scan.lr.web_servers.p44345.res', index=False) #ratelimit
	


if __name__ == "__main__":
    # execute only if run as a script
    main()


