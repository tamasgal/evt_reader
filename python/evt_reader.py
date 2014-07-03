import unittest

filename = '/Users/tamasgal/Desktop/modk40_v4_numuNC_23.evt'

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
                event.setdefault(tag, []).append(value.split())
            else:
                event[tag] = value.split()
    return raw_events

#with open(filename) as evt_file:
#    raw_header = extract_header(evt_file)
#    print("Parsing events...")
#    events = event_generator(evt_file)
#    print("Got {:d} events.".format(len(events)))
#    print events[0]['track_in']


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
