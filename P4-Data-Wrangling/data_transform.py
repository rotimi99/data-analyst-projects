#!/usr/bin/env python2
# -*- coding: utf-8 -*-

import xml.etree.cElementTree as ET
import pprint
from collections import defaultdict
import re
import csv
import codecs
import pprint
import cerberus
import schema

osmfile = "san_jose_california.osm"
OSM_PATH = "san_jose_california.osm"

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
    street_types = defaultdict(set)
    for event, elem in ET.iterparse(osmfile, events=("start",)):
        if elem.tag == "node" or elem.tag == "way":
            for tag in elem.iter("tag"):
                if is_street_name(tag):
                    audit_street_type(street_types, tag.attrib['v'])
    return street_types


#Cleaning the data by replacing the unusual street types with the corrections in mapping
#prints out the cleaned data
def fix_street(name, mapping):
    m = street_type_re.search(name)
    if m and m.group() in mapping:
        name = re.sub(street_type_re, mapping[m.group()], name)
    return name


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
    invalid_zipcodes = defaultdict(set)
    for event, elem in ET.iterparse(osmfile, events=("start",)):
        if elem.tag == "node" or elem.tag == "way":
            for tag in elem.iter("tag"):
                if is_zipcode(tag):
                    audit_zipcode(invalid_zipcodes, tag.attrib['v'])
    return invalid_zipcodes

zipcode = audit_zip(osmfile)

#cleaning postal codes
def fix_zipcode(zipcode):
    letters = re.findall('[a-zA-Z]*', zipcode)
    if letters:
        letters = letters[0]
    letters.strip()
    if letters == "CA":
        return str(re.findall(r'\d{5}', zipcode)[0])
    else:
        return str(re.findall(r'\d{5}', zipcode))


def update_zipcode(name):
    for street_type, ways in zipcode.iteritems():
        for name in ways:
            corrected = fix_zipcode(name)
            return corrected


NODES_PATH = "nodes.csv"
NODE_TAGS_PATH = "nodes_tags.csv"
WAYS_PATH = "ways.csv"
WAY_NODES_PATH = "ways_nodes.csv"
WAY_TAGS_PATH = "ways_tags.csv"

LOWER_COLON = re.compile(r'^([a-z]|_)+:([a-z]|_)+')
PROBLEMCHARS = re.compile(r'[=\+/&<>;\'"\?%#$@\,\. \t\r\n]')

SCHEMA = schema.schema

# Make sure the fields order in the csvs matches the column order in the sql table schema
NODE_FIELDS = ['id', 'lat', 'lon', 'user', 'uid', 'version', 'changeset', 'timestamp']
NODE_TAGS_FIELDS = ['id', 'key', 'value', 'type']
WAY_FIELDS = ['id', 'user', 'uid', 'version', 'changeset', 'timestamp']
WAY_TAGS_FIELDS = ['id', 'key', 'value', 'type']
WAY_NODES_FIELDS = ['id', 'node_id', 'position']


def shape_element(element, node_attr_fields=NODE_FIELDS, way_attr_fields=WAY_FIELDS,
                  problem_chars=PROBLEMCHARS, default_tag_type='regular'):
    """Clean and shape node or way XML elements to Python dict"""

    node_attribs = {}
    way_attribs = {}
    way_nodes = []
    tags = []  # Handles secondary tags the same way for both node and way elements


    if element.tag == "node":
        for i in NODE_FIELDS:
            try:
                node_attribs[i] = element.attrib[i]
            except:
                node_attribs[i] = '00000'
                pass
        for child in element.iter("tag"):
            #taking out unexpected characters
            if PROBLEMCHARS.search(child.attrib["k"]):
                pass
            elif LOWER_COLON.search(child.attrib["k"]):
                dic = {'id':element.attrib['id']}
                dic["type"] = child.attrib["k"].split(":", 1)[0]
                dic["key"] = child.attrib["k"].split(":", 1)[1]
                if child.attrib['k'] == "addr:street":
                    #cleaning street names
                    dic["value"] = fix_street(child.attrib["v"], mapping)
                elif child.attrib["k"] == 'addr:postcode':
                    #cleaning postcode
                    dic["value"] = update_zipcode(child.attrib["v"])
                else:
                    dic["value"] = child.attrib['v']
            else:
                dic = {'id':element.attrib['id']}
                #sharing top level node id
                dic["id"] = element.attrib["id"]
                dic["type"] = "regular"
                dic["key"] = child.attrib["k"]
                if child.attrib["k"] == "postcode":
                    #cleaning postcode
                    dic["value"] = update_zipcode(child.attrib['v'])
                else:
                    dic["value"] = child.attrib['v']
            tags.append(dic)
        return {'node': node_attribs, 'node_tags': tags}

    if element.tag == "way":
        for i in WAY_FIELDS:
            try:
                way_attribs[i] = element.attrib[i]
            except:
                way_attribs[i] == '00000'
                pass
        for child in element.iter("tag"):
            #taking out unexpected characters
            if PROBLEMCHARS.search(child.attrib["k"]):
                pass
            elif LOWER_COLON.search(child.attrib["k"]):
                dic = {'id':element.attrib['id']}
                dic["type"] = child.attrib["k"].split(":", 1)[0]
                dic["key"] = child.attrib["k"].split(":", 1)[1]
                if child.attrib['k'] == "addr:street":
                    #cleaning street names
                    dic["value"] = fix_street(child.attrib["v"], mapping)
                elif child.attrib["k"] == 'addr:postcode':
                    #cleaning postcode
                    dic["value"] = update_zipcode(child.attrib["v"])
                else:
                    dic["value"] = child.attrib['v']
            else:
                dic = {'id':element.attrib['id']}
                #sharing top level node id
                dic["id"] = element.attrib["id"]
                dic["type"] = "regular"
                dic["key"] = child.attrib["k"]
                if child.attrib["k"] == "postcode":
                    #cleaning postcode
                    dic["value"] = update_zipcode(child.attrib['v'])
                else:
                    dic["value"] = child.attrib['v']
            tags.append(dic)
        pos = 0
        for child in element.iter('nd'):
            dic = {}
            dic['id'] = element.attrib['id']
            dic['node_id'] = child.attrib['ref']
            dic['position'] = pos
            way_nodes.append(dic)
            pos += 1
        return {'way': way_attribs, 'way_nodes': way_nodes, 'way_tags': tags}


# ================================================== #
#               Helper Functions                     #
# ================================================== #
def get_element(osm_file, tags=('node', 'way', 'relation')):
    """Yield element if it is the right type of tag"""

    context = ET.iterparse(osm_file, events=("start", "end"))
    _, root = next(context)
    for event, elem in context:
        if event == 'end' and elem.tag in tags:
            yield elem
            root.clear()


def validate_element(element, validator, schema=SCHEMA):
    """Raise ValidationError if element does not match schema"""
    if validator.validate(element, schema) is not True:
        field, errors = next(validator.errors.iteritems())
        message_string = "\nElement of type '{0}' has the following errors:\n{1}"
        error_string = pprint.pformat(errors)

        raise Exception(message_string.format(field, error_string))


class UnicodeDictWriter(csv.DictWriter, object):
    """Extend csv.DictWriter to handle Unicode input"""

    def writerow(self, row):
        super(UnicodeDictWriter, self).writerow({
            k: (v.encode('utf-8') if isinstance(v, unicode) else v) for k, v in row.iteritems()
        })

    def writerows(self, rows):
        for row in rows:
            self.writerow(row)


# ================================================== #
#               Main Function                        #
# ================================================== #
def process_map(file_in, validate):
    """Iteratively process each XML element and write to csv(s)"""

    with codecs.open(NODES_PATH, 'w') as nodes_file, \
         codecs.open(NODE_TAGS_PATH, 'w') as nodes_tags_file, \
         codecs.open(WAYS_PATH, 'w') as ways_file, \
         codecs.open(WAY_NODES_PATH, 'w') as way_nodes_file, \
         codecs.open(WAY_TAGS_PATH, 'w') as way_tags_file:

        nodes_writer = UnicodeDictWriter(nodes_file, NODE_FIELDS)
        node_tags_writer = UnicodeDictWriter(nodes_tags_file, NODE_TAGS_FIELDS)
        ways_writer = UnicodeDictWriter(ways_file, WAY_FIELDS)
        way_nodes_writer = UnicodeDictWriter(way_nodes_file, WAY_NODES_FIELDS)
        way_tags_writer = UnicodeDictWriter(way_tags_file, WAY_TAGS_FIELDS)

        nodes_writer.writeheader()
        node_tags_writer.writeheader()
        ways_writer.writeheader()
        way_nodes_writer.writeheader()
        way_tags_writer.writeheader()

        validator = cerberus.Validator()

        for element in get_element(file_in, tags=('node', 'way')):
            el = shape_element(element)
            if el:
                if validate is True:
                    validate_element(el, validator)

                if element.tag == 'node':
                    nodes_writer.writerow(el['node'])
                    node_tags_writer.writerows(el['node_tags'])
                elif element.tag == 'way':
                    ways_writer.writerow(el['way'])
                    way_nodes_writer.writerows(el['way_nodes'])
                    way_tags_writer.writerows(el['way_tags'])


if __name__ == '__main__':
    # Note: Validation is ~ 10X slower. For the project consider using a small
    # sample of the map when validating.
    process_map(OSM_PATH, validate=True)
