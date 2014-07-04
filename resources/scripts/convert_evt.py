#!/usr/bin/env python 
# -*- coding: utf-8 -*-
# Filename: convert_evt.py
"""
Converts an EVT file to an I3 file, ready to use in IceTray.

Usage:
    convert_evt.py -i <evt_file> -o <i3_file>
    convert_evt.py (-h | --help)
    convert_evt.py --version

Options:
    -h --help       Show this screen.
    -i <evt_file>   Input file.
    -o <i3_file>    Output file.
"""
__author__ = "Tamas Gal"
__copyright__ = ("Copyright 2014, Tamas Gal and the KM3NeT collaboration "
                 "(http://km3net.org)")
__credits__ = [""]
__license__ = "GPL"
__version__ = "0.0.1"
__maintainer__ = "Tamas Gal"
__email__ = "tgal@km3net.de"
__status__ = "Development"  

from docopt import docopt
arguments = docopt(__doc__, version=__version__)
inputfile = arguments['-i']
outputfile = arguments['-o']

from os.path import expandvars

from I3Tray import *
from icecube import dataclasses, dataio, phys_services
from icecube.evt_reader import EventGenerator

#geometry = expandvars("$I3_SRC/evt_reader/resources/geo/km3net_geo.i3")

tray = I3Tray()
#tray.AddModule("I3Reader", "reader", Filename=geometry)
#tray.AddService("I3GCDFileServiceFactory", "geometry")(
#              ("GCDFileName", geometry)
#              )

tray.AddModule("I3InfiniteSource","source",Stream=icetray.I3Frame.Physics)

#filename = expandvars('$I3_SRC/evt_reader/resources/test/example.evt')
tray.AddModule(EventGenerator, "event_generator", filename=inputfile)


tray.AddModule('I3MetaSynth',"muxme")

tray.AddModule("Dump","dump")

tray.AddModule("I3Writer","writer")(("filename", outputfile))
tray.AddModule("TrashCan", "the can")
tray.Execute(10)
tray.Finish()
