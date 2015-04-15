import xml.etree.cElementTree as ET
from xml.dom import minidom
import numpy as np

def parse_garmin(filename, asarray=True):
    """
    Simple, slow form of parser.  Works OK for small data sets:

    dd1 = parse_garmin('6-6-13 10-02-31 AM.tcx')
    """
    xml = minidom.parse(filename)

    trackpoints = xml.getElementsByTagName('Trackpoint')

    datadict = {
            'altitude':[],
            'distance':[],
            'latitude':[],
            'longitude':[],
            'time':[],
            'hr_bpm':[],
            }
    dtypes = {
            'altitude':'float',
            'distance':'float',
            'latitude':'float',
            'longitude':'float',
            'time':'datetime64[s]',
            'hr_bpm':'int',
            }

    for tp in trackpoints:
        try: 
            datadict['altitude'] += [float(tp.getElementsByTagName('AltitudeMeters')[0].childNodes[0].nodeValue)]
            datadict['distance'] += [float(tp.getElementsByTagName('DistanceMeters')[0].childNodes[0].nodeValue)]
            datadict['longitude'] += [float(tp.getElementsByTagName('LongitudeDegrees')[0].childNodes[0].nodeValue)]
            datadict['latitude'] += [float(tp.getElementsByTagName('LatitudeDegrees')[0].childNodes[0].nodeValue)]
            datadict['time']     += [(tp.getElementsByTagName('Time')[0].childNodes[0].nodeValue)]
            if tp.getElementsByTagName('HeartRateBpm'):
                datadict['hr_pbm'] += [(tp.getElementsByTagName('HeartRateBpm')[0].childNodes[0].nodeValue)]
        except IndexError:
            print "Skipped ",
            print tp,tp.childNodes,[N.nodeValue for N in tp.childNodes if
                                    hasattr(N,'nodeValue')]

    dt = np.array(datadict['time'], dtype='datetime64[s]') - np.datetime64(datadict['time'][0])
    datadict['dt'] = dt.astype('float').tolist()
    dtypes['dt'] = 'float'

    if asarray:
        keys = datadict.keys()
        dataarr = np.array(zip(*[datadict[k] for k in keys if any(datadict[k])]),
                            dtype=[(k,dtypes[k]) for k in keys if any(datadict[k])])
        return dataarr

    return datadict


def find_workouts_by_startpoint(startlat=40.020631,startlon=-105.296255,tolerance=1e-5):
    et = ET.parse('All Training Center Data.tcx')
    activities = [e for e in et.iter() if '}Activity' in e.tag]
    lonlat = {}
    for A in activities:
        for L in list(A):
            found_lat = False
            found_lon = False
            if '}Lap' in L.tag:
                starttime = L.attrib['StartTime']
                lonlat[starttime] = [L]
                for e in L.iter():
                    if found_lat and found_lon:
                        break
                    if not found_lat and '}LatitudeDegrees' in e.tag:
                        lonlat[starttime] += [float(e.text)]
                        found_lat = True
                    if not found_lon and '}LongitudeDegrees' in e.tag:
                        lonlat[starttime] += [float(e.text)]
                        found_lon = True

    location_runs = []

    for k in lonlat:
        if len(lonlat[k]) != 3:
            print "Skipped ",k
            continue
        A,lat,lon = lonlat[k]
        dist = ((lon-startlon)**2 + (lat-startlat)**2)
        if dist < tolerance:
            print "Activity ",k," is a location run"
            location_runs.append(A)
        
    return location_runs

def get_location_arrays(tolerance=1e-5,endlat=40.034425,endlon=-105.305303,**kwargs):
    location_runs = find_location(**kwargs)
    location_arrays = [datadict_to_array(activity_to_datadict(A)) for A in location_runs]
    indexed = {str(arr[0]['time']):arr for arr in location_arrays}
    popkeys = []
    for k in indexed:
        lon =  indexed[k][-1]['lon']
        lat =  indexed[k][-1]['lat']
        dist = ((lon-endlon)**2 + (lat-endlat)**2)
        if dist > tolerance:
            popkeys.append(k)
    for k in popkeys:
        indexed.pop(k)
    return indexed

def plot_arrays(data):
    """
    Convenience function for overplotting various quantities
    """
    import pylab as pl
    ncolors = len(data)
    pl.rc('axes',color_cycle=[pl.cm.spectral(float(ii)/ncolors) for ii in xrange(ncolors)])
    pl.figure(1)
    pl.clf()
    for k in data:
        pl.plot(data[k]['distance']-data[k]['distance'][0],data[k]['altitude'],label=k)
    pl.xlabel("Distance (m)")
    pl.ylabel("Altitude (m)")
    pl.legend(loc='best')

    pl.figure(2)
    pl.clf()
    for k in data:
        pl.plot((data[k]['time']-data[k]['time'][0]).astype('float'),data[k]['distance']-data[k]['distance'][0],label=k)
    pl.plot([0,1500],[0,1500*(1600/(24.*60))],'k--',label='24 minute miles')
    pl.plot([0,1500],[0,1500*(1600/(21.*60))],'k:' ,label='21 minute miles')
    pl.plot([0,1500],[0,1500*(1600/(18.*60))],'k-.',label='18 minute miles')
    pl.xlabel("Time (s)")
    pl.ylabel("Distance (m)")
    pl.legend(loc='best')

    pl.figure(3)
    pl.clf()
    for k in data:
        pl.plot(data[k]['altitude']-data[k]['altitude'][0],data[k]['distance']-data[k]['distance'][0],label=k)
    pl.xlabel("Altitude (m)")
    pl.ylabel("Distance (m)")
    pl.legend(loc='best')

    pl.figure(4)
    pl.clf()
    for k in data:
        pl.plot((data[k]['time']-data[k]['time'][0]).astype('float'),data[k]['altitude']-data[k]['altitude'][0],label=k)
    pl.xlabel("Time (s)")
    pl.ylabel("Altitude (m)")
    pl.legend(loc='best')

def activity_to_datadict(activity):
    datadict = {
            'lon':[],
            'lat':[],
            'altitude':[],
            'distance':[],
            'time':[],
            }
    for child in activity.iter():
        if 'Trackpoint' in child.tag:
            datapoint = read_trackpoint(child)
            if all((k in datapoint for k in datadict)):
                for k in datadict:
                    datadict[k].append(datapoint[k])
    return datadict

def datadict_to_array(datadict):
    dtypes = {
            'lon':'float',
            'lat':'float',
            'altitude':'float',
            'distance':'float',
            'time':'datetime64[s]',
            }

    keys = datadict.keys()
    dataarr = np.array(zip(*[datadict[k] for k in keys]),
                        dtype=[(k,dtypes[k]) for k in keys])
    return dataarr

def read_trackpoint(tp):
    data = {}
    for child in tp:
        if 'Time' in child.tag:
            data['time'] = child.text
        if 'DistanceMeters' in child.tag:
            data['distance'] = float(child.text)
        if 'AltitudeMeters' in child.tag:
            data['altitude'] = float(child.text)
        if 'Position' in child.tag:
            data['lat'] = float(list(child)[0].text)
            data['lon'] = float(list(child)[1].text)
    return data
