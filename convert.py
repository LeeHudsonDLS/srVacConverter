import xml.etree.ElementTree as ET


def substitueAsynPorts(input_xml):
    asynPortClasses=["asyn.AsynSerial","mks937a.mks937a","digitelMpc.digitelMpc"]
    tree = ET.ElementTree(ET.fromstring(input_xml))
    root = tree.getroot()
    
    # Step 1: Build a mapping from asyn.AsynSerial name -> replacement name
    serial_replacements = {}
    for elem in root.findall("asyn.AsynSerial"):
        serial_name = elem.get("name")
        serial_replacements[serial_name] = None  # Placeholder
    
    # Step 2: Determine replacement names based on references
    for elem in root:
        if elem.tag in asynPortClasses:
            if elem.tag != "asyn.AsynSerial":
                port = elem.get("port")
                if port in serial_replacements:
                    serial_replacements[port] = f"{elem.get('name')}_PORT"
    
    # Step 3: Remove entries with None values
    serial_replacements = {k: v for k, v in serial_replacements.items() if v is not None}
    
    # Step 4: Replace occurrences in all elements
    for elem in root:
        if elem.tag in asynPortClasses:
            for attr in elem.attrib:
                if elem.attrib[attr] in serial_replacements:
                    elem.attrib[attr] = serial_replacements[elem.attrib[attr]]

    # Convert class to asyn.AsynSerial
    for elem in root.findall("asyn.AsynSerial"):
        elem.tag = "asyn.AsynIP"

    # Clear the port
    for elem in root.findall("asyn.AsynIP"):
        elem.set("port", f"192.168.{cell}.")

    # Remove priority
    for elem in root.findall("asyn.AsynIP"):
        if "priority" in elem.attrib:
            del elem.attrib["priority"]
    
    # Output modified XML with declaration
    return '<?xml version="1.0" ?>\n' + ET.tostring(root, encoding='unicode')

def remove_unwanted_tags(input_xml):
    tree = ET.ElementTree(ET.fromstring(input_xml))
    root = tree.getroot()
    
    # Define unwanted tags
    unwanted_tags = ["mrfTiming.EventReceiverPMC",
                     "ipac.Hy8002",
                     "ipac.Hy8001",
                     "Hy8401ip.Hy8401",
                     "Hy8414.Hy8414",
                     "DLS8515.DLS8515",
                     "FINS.FINSHostlink",
                     "DLS8515.DLS8515channel",
                     "Hy8401ip.auto_Hy8401ip",
                     "dlsPLC.read100",
                     "FastVacuum.Master16",
                     "FastVacuum.auto_Channel16"]
    
    # Remove elements with unwanted tags
    for elem in root.findall("*"):
        if elem.tag in unwanted_tags:
            root.remove(elem)
    
    # Output modified XML with declaration
    return '<?xml version="1.0" ?>\n' + ET.tostring(root, encoding='unicode')


# Example usage
input_filename = "SR06C-VA-IOC-01.xml"
output_filename = input_filename.replace(".xml", "_converted.xml")
cell = 6

with open(input_filename, "r") as file:
    input_xml = file.read()

converted_xml = remove_unwanted_tags(input_xml)
converted_xml = substitueAsynPorts(converted_xml)


with open(output_filename, "w") as file:
    file.write(converted_xml)

print(f"Converted XML saved to {output_filename}")
