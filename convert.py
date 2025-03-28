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
    output = '<?xml version="1.0" ?>\n' + ET.tostring(root, encoding='unicode')
    return output

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
    output = '<?xml version="1.0" ?>\n' + ET.tostring(root, encoding='unicode')
    return output

def add_fins_udp_init(input_xml):
    tree = ET.ElementTree(ET.fromstring(input_xml))
    root = tree.getroot()
    
    # Create the new FINS.FINSUDPInit element
    fins_elem = ET.Element("FINS.FINSUDPInit")
    fins_elem.set("ip", "192.168.5.10")
    fins_elem.set("name", "VLVCC_01_FINS")
    fins_elem.set("simulation", "None")
    
    # Find the last asyn.AsynIP element
    last_asyn_ip = None
    for elem in root.findall("asyn.AsynIP"):
        last_asyn_ip = elem
    
    # If we found an asyn.AsynIP element, insert after it
    if last_asyn_ip is not None:
        # Find the position to insert after the last asyn.AsynIP
        for i, elem in enumerate(root):
            if elem == last_asyn_ip:
                root.insert(i + 1, fins_elem)
                break
    else:
        # If no asyn.AsynIP is found, append at the end of the root
        root.append(fins_elem)
    
    # Output modified XML with declaration
    output = '<?xml version="1.0" ?>\n' + ET.tostring(root, encoding='unicode')
    output = output.replace('><',">\n\t<")
    return output

def add_NX102_readReal(input_xml):
    tree = ET.ElementTree(ET.fromstring(input_xml))
    root = tree.getroot()
    elementList = list()
    index = 0

    for elem in root.findall("mks937a.mks937aGauge"):
        index += 1
        id = elem.get("id")
        name = elem.get("name")
        dom = elem.get("dom")
        vc = 1
        c = ""
        if gaugeChannels[name] == "A":
            c="1"
        else:
            c="2"

        readReadElem = ET.Element("dlsPLC.NX102_readReal")
        readReadElem.set("device", f"{dom}-VA-GAUGE-{id}:RAW")
        readReadElem.set("name", f"PLC_COMB0{index}")
        readReadElem.set("port", "VLVCC_01_EIP")
        readReadElem.set("tag", f"{dom}_VC{vc}_GCTLR_{id}_COMB_{gaugeChannels[name]}_C{c}_Comb_mBar")
        elementList.append(readReadElem)

    for elem in elementList:
        root.append(elem)
    
    output = '<?xml version="1.0" ?>\n' + ET.tostring(root, encoding='unicode')
    output = output.replace('><',">\n\t<")
    return output


# Example usage
input_filename = "SR06C-VA-IOC-01.xml"
output_filename = input_filename.replace(".xml", "_converted.xml")
cell = 6
gaugeChannels = {"GAUGE_S_01":"A",
                 "GAUGE_S_02":"B",
                 "GAUGE_A_01":"A",
                 "GAUGE_A_02":"B",
                 "GAUGE_A_03":"B",
                 "GAUGE_A_31":"A",
                 "GAUGE_A_04":"B"}

with open(input_filename, "r") as file:
    input_xml = file.read()

converted_xml = remove_unwanted_tags(input_xml)
converted_xml = substitueAsynPorts(converted_xml)
converted_xml = add_fins_udp_init(converted_xml)
converted_xml = add_NX102_readReal(converted_xml)



with open(output_filename, "w") as file:
    file.write(converted_xml)

print(f"Converted XML saved to {output_filename}")
