#!/usr/bin/env python2
# -*- coding: utf-8 -*-

import xml.etree.cElementTree as ET
import pprint
from collections import defaultdict
import re

osmfile = "san_jose_california.osm"

#|-----------------------------------------|
#|---Auditing & Cleaning Street Names------|
#|-----------------------------------------|

#unusual street types
street_type_re = re.compile(r'\S+\.?$', re.IGNORECASE)
street_types = defaultdict(set)

#expected values based on current usps database
expected_street = ["Close", "Cove", "Commons", "Bend", "Grove", "Green", "Glen",
            "Gardens", "Heights", "Highway", "Hills", "Landing", "Mall",
            "Meadows", "Park", "Parkway", "Plaza", "Point", "Ridge", "Row",
            "Run", "Spur", "Square", "Station", "Terrace", "Trail", "View",
            "Vista", "Walk", "Wall", "Alley", "Center", "Crescent", "Way",
            "Road", "Street", "Avenue", "Boulevard", "Drive", "Court",
            "Place", "Alley", "Circle", "Estates", "Lane", "Loop", "Expressway"]

#corrections
mapping = { "street": "Street",
            "st": "Street",
            "boulevard" : "Boulevard",
            "avenue": "Avenue",
            "ave": "Avenue",
            "av.": "Avenue",
            "Ter": "Terrace",
            "Steet": "Street",
            "St.": "Street",
            "St": "Street",
            "street": "Street",
            "Pkwy": "Parkway",
            "ST": "Street",
            "Rd.": "Road",
            "Rd": "Road",
            "ROAD": "Road",
            "RD": "Road",
            "Pl": "Plaza",
            "PL": "Plaza",
            "Ln.": "Lane",
            "Hwy": "Highway",
            "Dr.": "Drive",
            "Dr": "Drive",
            "Ct": "Court",
            "CT": "Court",
            "court": "Court",
            "Blvd.": "Boulevard",
            "Blvd": "Boulevard",
            "Boulvevard": "Boulevard",
            "Ave.": "Avenue",
            "Ave": "Avenue",
            "Av.": "Avenue",
            "AVENUE": "Avenue",
            "AVE": "Avenue",
            "ave": "Avenue",
            "Cir": "Circle",
            "Sq": "Square"
           }


#checks if values are in the expected_street names list
#and adds them to the street types dict if not 
def audit_street_type(street_types, street_name):
    m = street_type_re.search(street_name)
    if m:
        street_type = m.group()
        if street_type not in expected_street:
            street_types[street_type].add(street_name)


#helper function used in audit(osmfile), to use correct element
def is_street_name(tag):
    return (tag.attrib['k'] == "addr:street")


#checks steet types for node and way top level tags
#prints out the unusual street types in a dictionary format
#returns the unusual street types
def audit(osmfile):
    osm_file = open(osmfile, "r")
    street_types = defaultdict(set)
    for event, elem in ET.iterparse(osm_file, events=("start",)):
        if elem.tag == "node" or elem.tag == "way":
            for tag in elem.iter("tag"):
                if is_street_name(tag):
                    audit_street_type(street_types, tag.attrib['v'])
    #pprint.pprint(dict(street_types))                
    osm_file.close()
    return street_types


#Cleaning the data by replacing the unusual street types with the corrections in mapping
#prints out the cleaned data
def fix_street(osmfile):
    st_types = audit(osmfile)
    for st_type, ways in st_types.iteritems():
        for name in ways:
            if st_type in mapping:
                better_name = name.replace(st_type, mapping[st_type])
                print name, "=>", better_name


fix_street(osmfile)

#|------------------------|
#|---Auditing Cities------|
#|------------------------|

#checks what cities are present in this OSM file
def audit_city(osmfile):
    osm_file = open(osmfile, "r")  
    cities = set()
    for event, elem in ET.iterparse(osm_file, events=("start",)):
        if elem.tag == "node" or elem.tag == "way":
            for tag in elem.iter("tag"):
                if tag.attrib['k'] == "addr:city" and tag.attrib['v'] != "San Jose" and tag.attrib['v'] != "san Jose" and tag.attrib['v'] != "San jose" and tag.attrib['v'] != "san jose":
                    cities.add(tag.attrib['v'])
    print "Cities in the OSM file:", cities


audit_city(osmfile)


#|--------------------------------------|
#|---Auditing & Cleaning Zip Codes------|
#|--------------------------------------|

expected_zipcode = ["94089", "95002", "95008", "95013", "95014", "95032",
                     "95035", "95037", "95050", "95054", "95070", "95110",
                     "95111", "95112", "95113", "95116", "95117", "95118",
                     "95119", "95120", "95121", "95122", "95123", "95124",
                     "95125", "95126", "95127", "95128", "95129", "95130",
                     "95131", "95132", "95133", "95134", "95135", "95136",
                     "95138", "95139", "95140", "95148"] 

invalid_zipcodes = defaultdict(set)

def audit_zipcode(invalid_zipcodes, zipcode):
    digits = zipcode[0:6]
    if digits not in expected_zipcode:
        invalid_zipcodes[digits].add(zipcode)
        
def is_zipcode(tag):
    return (tag.attrib['k'] == "addr:postcode")

def audit_zip(osmfile):
    osm_file = open(osmfile, "r")
    invalid_zipcodes = defaultdict(set)
    for event, elem in ET.iterparse(osm_file, events=("start",)):
        if elem.tag == "node" or elem.tag == "way":
            for tag in elem.iter("tag"):
                if is_zipcode(tag):
                    audit_zipcode(invalid_zipcodes, tag.attrib['v'])
    #pprint.pprint(dict(invalid_zipcodes))
    return invalid_zipcodes

zipcode = audit_zip(osmfile)

#cleaning postal codes
def fix_zipcode(zipcode):
    letters = re.findall('[a-zA-Z]*', zipcode)
    if letters:
        letters = letters[0]
    letters.strip()
    if letters == "CA":
        return re.findall(r'\d{5}', zipcode)[0]
    else:
        return re.findall(r'\d{5}', zipcode)


for street_type, ways in zipcode.iteritems():
    for name in ways:
        corrected = fix_zipcode(name)
        print name, "=>", corrected
        





    



