class Cell:
    def __init__(self,cell,d2GaugeControllers=None,asynPorts=None,gaugeConfig=None):
        self.cell = cell
        self.inputFileName = f"SR{self.cell:02d}C-VA-IOC-01.xml"
        self.outputFilename = self.inputFileName.replace(".xml", "_converted.xml")

        if d2GaugeControllers is None:
            self.d2GaugeControllers = ["SS","KS"]
        else:
            self.d2GaugeControllers = d2GaugeControllers

        if asynPorts is None:
            self.asynPorts = {f"GCTLR_{self.d2GaugeControllers[0]}_01_PORT":f"192.168.{self.cell}.11:7001",
                              "GCTLR_A_01_PORT":f"192.168.{self.cell}.11:7002",
                              "GCTLR_S_01_PORT":f"192.168.{self.cell}.11:7003",
                              "MPC_S_01_PORT":f"192.168.{self.cell}.11:7004",
                              "MPC_A_01_PORT":f"192.168.{self.cell}.11:7005",
                              "MPC_A_02_PORT":f"192.168.{self.cell}.11:7006",
                              "RGA_PC_01_PORT":f"192.168.{self.cell}.12:7001",
                              f"GCTLR_{self.d2GaugeControllers[1]}_01_PORT":f"192.168.{self.cell}.12:7002",
                              "GCTLR_A_02_PORT":f"192.168.{self.cell}.12:7003",
                              "GCTLR_A_03_PORT":f"192.168.{self.cell}.12:7004",
                              "MPC_A_03_PORT":f"192.168.{self.cell}.12:7005",
                              "MPC_A_04_PORT":f"192.168.{self.cell}.12:7006",
                              "MPC_A_05_PORT":f"192.168.{self.cell}.12:7007",
                              "MPC_A_06_PORT":f"192.168.{self.cell}.12:7008",
                              "MPC_A_07_PORT":f"192.168.{self.cell}.12:7009",
                              "MPC_A_08_PORT":f"192.168.{self.cell}.12:7010"}
        else:
            self.asynPorts = asynPorts

        if gaugeConfig is None:
            self.gaugeConfig = {"GAUGE_S_01":{"slot":"A","vlvcc":"1","mksType":"b"},
                                "GAUGE_S_02":{"slot":"B","vlvcc":"1","mksType":"b"},
                                "GAUGE_A_01":{"slot":"A","vlvcc":"1","mksType":"b"},
                                "GAUGE_A_02":{"slot":"B","vlvcc":"1","mksType":"b"},
                                "GAUGE_A_03":{"slot":"B","vlvcc":"2","mksType":"b"},
                                "GAUGE_A_31":{"slot":"A","vlvcc":"2","mksType":"b"},
                                "GAUGE_A_04":{"slot":"B","vlvcc":"2","mksType":"b"}}
        else:
            self.gaugeConfig = gaugeConfig



class CellCollection:
    def __init__(self):
        self.cells = [None]*24

        self.cells[6] = Cell(6)
        self.cells[7] = Cell(7)