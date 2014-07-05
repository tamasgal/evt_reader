#!/usr/bin/env python 
# -*- coding: utf-8 -*-
# Filename: evt_reader.py
"""
A collection of functions and an IceTray module to convert EVT files to I3.

"""
__author__ = "Tamas Gal"
__copyright__ = ("Copyright 2014, Tamas Gal and the KM3NeT collaboration "
                 "(http://km3net.org)")
__credits__ = [""]
__license__ = "GPL"
__version__ = "0.1.0"
__maintainer__ = "Tamas Gal"
__email__ = "tgal@km3net.de"
__status__ = "Development"  

import os
import unittest

from icecube import icetray, dataclasses



class EventGenerator(icetray.I3Module):
    """Converts events in EVT files to I3 frames."""

    def __init__(self, context): # pylint: disable=E1002
        super(self.__class__, self).__init__(context)
        self.AddParameter("filename", "An EVT file", None)
        self.AddOutBox("OutBox")

    def Configure(self): # pylint: disable=C0103,C0111
        filename = self.GetParameter("filename")
        self.evt_file = open(filename)
        # TODO: header conversion
        raw_header = extract_header(self.evt_file)
        self.events = event_generator(self.evt_file)

    def Physics(self, frame): # pylint: disable=C0103,C0111
        try:
            event = self.events.next()
        except StopIteration:
            return

        frame['I3MCTree'] = mctree_maker(event)

        # TODO: extract method(s) and cleanup
        raw_hit_series = dict()
        physics_hit_series = dict()
        simple_hit_series = dict()
        raw_hits = event['hit']
        for raw_hit in raw_hits:
            hit_id, rest = unpack_nfirst(raw_hit, 1)
            pmt_id, rest = unpack_nfirst(rest, 1)
            charge, time, geant_code, origin, _, _ = rest
            pulse = dataclasses.I3RecoPulse()
            pulse.time = time
            pulse.charge = charge
            pulse.width = 30
            omkey = pmtid2omkey(pmt_id)
            raw_hit_series.setdefault(omkey, []).append(pulse)
            if origin > 0:
                physics_hit_series.setdefault(omkey, []).append(pulse)
                omkey = icetray.OMKey(omkey[0], omkey[1], 0)
                simple_hit_series.setdefault(omkey, []).append(pulse)

        raw_hit_map = dataclasses.I3RecoPulseSeriesMap(raw_hit_series)
        physics_hit_map = dataclasses.I3RecoPulseSeriesMap(physics_hit_series)
        simple_hit_map = dataclasses.I3RecoPulseSeriesMap(simple_hit_series)
        frame.Put("RawHitSeries", raw_hit_map)
        frame.Put("PhysicsHitSeries", physics_hit_map)
        frame.Put("SimpleHitSeries", simple_hit_map)

        self.PushFrame(frame)

    def Finish(self):
        self.evt_file.close()


def extract_header(evt_file):
    """Create a dictionary with the EVT header information"""
    raw_header = {}
    for line in evt_file:
        line = line.strip()
        try:
            tag, value = line.split(':')
        except ValueError:
            continue
        raw_header[tag] = value.split()
        if line.startswith('end_event:'):
            return raw_header 
    raise ValueError("Incomplete header, no 'end_event' tag found!")


def event_generator(evt_file):
    """Create a generator object which extracts events from an EVT file."""
    event = None
    for line in evt_file:
        line = line.strip()
        if line.startswith('end_event:') and event:
            yield event
            event = None
            continue
        if line.startswith('start_event:'):
            event = {}
            tag, value = line.split(':')
            event[tag] = value.split()
            continue
        if event:
            tag, value = line.split(':')
            if tag in ('neutrino', 'track_in', 'hit'):
                values = [float(x) for x in value.split()]
                event.setdefault(tag, []).append(values)
            else:
                event[tag] = value.split()


def mctree_maker(event):
    """Convert EVT-event to an I3MCTree"""
    neutrino = get_neutrino(event)
    secondaries = get_secondaries(event)
    mctree = dataclasses.I3MCTree()
    mctree.add_primary(neutrino)
    for secondary in secondaries:
        mctree.append_child(neutrino, secondary)
    return mctree


def get_neutrino(event):
    """Extract and return a neutrino as I3Particle from given EVT-event"""
    if len(event['neutrino']) > 1:
        raise NotImplemented("Sorry, only one primary is supported atm!")
    raw_neutrino = event['neutrino'][0]
    neutrino_id, rest = unpack_nfirst(raw_neutrino, 1)
    pos_x, pos_y, pos_z, rest = unpack_nfirst(rest, 3)
    dir_x, dir_y, dir_z, rest = unpack_nfirst(rest, 3)
    energy, time, _, _, _, pdg, _ = rest
    neutrino = make_particle(pos_x, pos_y, pos_z, dir_x, dir_y, dir_z,
                             energy, time, pdg)
    return neutrino


def get_secondaries(event):
    """Extract and return a secondaries as I3Particles from given EVT-event"""
    secondaries = []
    for raw_secondary in event['track_in']:
        try:
            secondary_id, rest = unpack_nfirst(raw_secondary, 1)
            pos_x, pos_y, pos_z, rest = unpack_nfirst(rest, 3)
            dir_x, dir_y, dir_z, rest = unpack_nfirst(rest, 3)
            energy, time, pdg = rest
            secondary = make_particle(pos_x, pos_y, pos_z,
                                      dir_x, dir_y, dir_z,
                                      energy, time, pdg)
            secondaries.append(secondary)
        except ValueError:
            print("Could not parse line:\n{:s}".format(raw_secondary))
    return secondaries


def make_particle(pos_x, pos_y ,pos_z, dir_x, dir_y, dir_z, energy, time, pdg):
    """Create an I3Particle with given properties"""
    particle = dataclasses.I3Particle()
    particle.time = time
    particle.energy = energy
    particle.pdg_encoding = int(pdg)
    particle.dir = dataclasses.I3Direction(dir_x, dir_y, dir_z)
    particle.pos = dataclasses.I3Position(pos_x, pos_y, pos_z)
    return particle


def pmtid2omkey(pmt_id, first_pmt_id=1, oms_per_string=18, pmts_per_om=31):
    """Convert (consecutive) raw PMT IDs to Multi-OMKeys."""
    pmts_per_string = oms_per_string * pmts_per_om
    string = ((pmt_id - first_pmt_id) / pmts_per_string) + 1
    om = oms_per_string - (pmt_id - first_pmt_id) % pmts_per_string / pmts_per_om
    pmt = (pmt_id - first_pmt_id) % pmts_per_om
    try:
        from icecube import icetray
        return icetray.OMKey(int(string), int(om), int(pmt))
    except ImportError:
        return (string, om, pmt)


def unpack_nfirst(seq, nfirst):
    """Unpack the nfrist items from the list and return the rest.
    
    >>> a, b, c, rest = unpack_nfirst((1, 2, 3, 4, 5), 3)
    >>> a, b, c
    (1, 2, 3)
    >>> rest
    (4, 5)
    """
    it = iter(seq)
    for x in xrange(nfirst):
        yield next(it, None)
    yield tuple(it)


class TestTools(unittest.TestCase):

    def test_unpack_nfirst(self):
        unpack_me = (1, 2, 3, 4, 5, 6)
        a, b, c, rest = unpack_nfirst(unpack_me, 3)
        self.assertEqual(1, a)
        self.assertEqual(2, b)
        self.assertEqual(3, c)
        self.assertTupleEqual(rest, (4, 5, 6))

    def test_pmtid2omkey(self):
        self.assertEqual((1, 13, 12), tuple(pmtid2omkey(168)))
        self.assertEqual((1, 12, 18), tuple(pmtid2omkey(205)))
        self.assertEqual((1, 11, 22), tuple(pmtid2omkey(240)))
        self.assertEqual((4, 11, 2), tuple(pmtid2omkey(1894)))
        self.assertEqual((9, 18, 0), tuple(pmtid2omkey(4465)))
        self.assertEqual((95, 7, 16), tuple(pmtid2omkey(52810)))
        self.assertEqual((95, 4, 13), tuple(pmtid2omkey(52900)))


class TestParser(unittest.TestCase):

    def setUp(self):
        self.TEST_EVT="""
        start_run: 1
        cut_nu: 0.100E+03 0.100E+09-0.100E+01 0.100E+01
        spectrum: -1.40
        end_event:
        """

    def test_parse_header(self):
        raw_header = extract_header(self.TEST_EVT.splitlines())
        self.assertEqual(['1'], raw_header['start_run'])
        self.assertAlmostEqual(-1.4, float(raw_header['spectrum'][0]))
        self.assertAlmostEqual(1, float(raw_header['cut_nu'][2]))

    def test_incomplete_header_raises_valueerror(self):
        CORRUPT_HEADER="""foo"""
        with self.assertRaises(ValueError):
            extract_header(CORRUPT_HEADER.splitlines())


if __name__ == '__main__':
    unittest.main()
