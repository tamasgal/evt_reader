import os
import unittest

from icecube import icetray, dataclasses


filename = os.path.expandvars('$I3_SRC/evt_reader/resources/test/example.evt')

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
    raw_events = []
    event = None
    for line in evt_file:
        line = line.strip()
        #print("Checking line '{:s}'".format(line))
        if line.startswith('end_event:') and event:
            raw_events.append(event)
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
                event.setdefault(tag, []).append([float(x) for x in value.split()])
            else:
                event[tag] = value.split()
    return raw_events

def mctree_maker(event):
    """Convert EVT-event to an I3MCTree"""
    if len(event['neutrino']) > 1:
        raise NotImplemented("Sorry, only one primary is support atm!")
    raw_neutrino = event['neutrino'][0]
    neutrino_id, rest = unpack_nfirst(raw_neutrino, 1)
    pos_x, pos_y, pos_z, rest = unpack_nfirst(rest, 3)
    dir_x, dir_y, dir_z, rest = unpack_nfirst(rest, 3)
    energy, time, _, _, _, pdg, _ = rest
    neutrino = dataclasses.I3Particle()
    neutrino.time = time
    neutrino.energy = energy
    neutrino.pdg_encoding = int(pdg)
    position = dataclasses.I3Position(pos_x, pos_y, pos_z)
    direction = dataclasses.I3Direction(dir_x, dir_y, dir_z)
    neutrino.dir = direction
    neutrino.pos = position

def unpack_nfirst(seq, nfirst):
    """Unpack the nfrist items from the list and return the rest.
    
    a, b, c, rest = unpack_nfirst((1, 2, 3, 4, 5), 3)
    # a = 1, b = 2, c = 3, rest = (4, 5)
    """
    it = iter(seq)
    for x in xrange(nfirst):
        yield next(it, None)
    yield tuple(it)


with open(filename) as evt_file:
    raw_header = extract_header(evt_file)
    print("Parsing events...")
    events = event_generator(evt_file)
    print("Got {:d} events.".format(len(events)))
    mctree_maker(events[0])


class TestCase(unittest.TestCase):

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
