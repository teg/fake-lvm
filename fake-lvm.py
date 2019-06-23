#!/usr/bin/python2

import argparse
import json
import lvm2
import pvdissect

class ParseActions(object):

    def make_document(self, input, start, end, elements):
        dictionary = {}

        for key, value in elements[1].elements:
            dictionary[key] = value

        return dictionary

    def make_value_pair(self, input, start, end, elements):
        return (elements[1], elements[5])

    def make_object_pair(self, input, start, end, elements):
        return (elements[1], elements[3])

    def make_empty_array(self, input, start, end, elements):
        return []

    def make_array(self, input, start, end, elements):
        array = [elements[2]]

        for el in elements[4].elements:
            array.append(el.elements[2])

        return array

    def make_object(self, input, start, end, elements):
        dictionary = {}

        for key, value in elements[2].elements:
            dictionary[key] = value

        return dictionary

    def make_name(self, input, start, end, elements):
        return input[start:end]

    def make_string(self, input, start, end, elements):
        return elements[1].text

    def make_zero(self, input, start, end):
        return 0

    def make_number(self, input, start, end, elements):
        return int(input[start:end], 10)

def fake_lvm_mount_pv(pv, extent_size, offset, count):
    return {'uuid': pv["id"],
            'sector_start': pv["pe_start"] + offset * extent_size,
            'sector_count': count * extent_size}

def fake_lvm_mount(vg, lv):
    lv = vg["logical_volumes"][lv]

    if lv["segment_count"] != 1:
        print "The logical volume must have exactly one segment."
        return
    segment = lv["segment1"]

    if segment["start_extent"] != 0:
        print "The segment must start at the beginning of the LV"
        return

    extent_count = segment["extent_count"]

    if segment["type"] != "striped":
        print "The logical volume must be striped."
        return
    if segment["stripe_count"] != 1:
        print "The logical volume must have exactly one stripe."
    stripes = segment["stripes"]

    pv = vg["physical_volumes"][stripes[0]]
    pv_offset = stripes[1]

    extent_size = vg["extent_size"]

    return fake_lvm_mount_pv(pv, extent_size, pv_offset, segment["extent_count"])

def fake_lvm(pv, vg, lv):
    header = pvdissect.PV()
    header.open(pv)
    if len(header._metadatas) != 1:
        print("Only one piece of metadata supported.")
        header.close()
        return
    else:
        metadata = lvm2.parse(header._metadatas[0].value[2], actions=ParseActions())
        header.close()

    print json.dumps(fake_lvm_mount(metadata[vg], lv), indent=4)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fake LVM mounter")
    parser.add_argument("physical_volume", metavar="PV",
                        help="blockdevice containing the only physical volume of the volume group")
    parser.add_argument("volume_group", metavar="VG",
                        help="volume group to use")
    parser.add_argument("logical_volume", metavar="LV",
                        help="logical volume to mount")

    args = parser.parse_args()

    fake_lvm(args.physical_volume, args.volume_group, args.logical_volume)
