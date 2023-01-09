import sys, os, time
import logging, traceback
import configparser, queue
import PyQt6
import PyQt6.QtWidgets as qt
import numpy as np
import qdarkstyle, pyvisa

import widgets
from big_sky_yag import BigSkyYag

def pt_to_px(pt):
    """Convert GUI widget size from unit pt to unit px using monitor dpi"""

    return round(pt*monitor_dpi/72)


class Worker(PyQt6.QtCore.QObject):
    """A worker class that controls Hornet. This class should be run in a separate thread."""

    finished = PyQt6.QtCore.pyqtSignal()
    update = PyQt6.QtCore.pyqtSignal(dict)

    def __init__(self, parent):
        super().__init__()
        self.parent = parent
        self.cmd_queue = queue.Queue()

    def run(self):
        """Repeatedly read from the device."""

        try:
            self.yag = BigSkyYag(resource_name=self.parent.config["setting"]["com_port"])
        except Exception as err:
            logging.error(f"Can't connect to BigSky YAG at COM port {self.parent.config['setting']['com_port']}.\n"+str(err))
            self.finished.emit()
            return

        t0 = 0
        while self.parent.running:
            while not self.cmd_queue.empty():
                config_type, val = self.cmd_queue.get()
                if config_type == "flashlamp_trigger":
                    self.yag.flashlamp.trigger = val
                    self.update.emit({"flashlamp_trigger": self.yag.flashlamp.trigger})
                elif config_type == "flashlamp_frequency_Hz":
                    pass

            if self.parent.running and (time.time() - t0 > self.parent.config.getfloat("setting", "loop_cycle_seconds")):
                pass

    def open_com(self, com_port):  
        """Open a com port."""

        try:
            self.instr = self.rm.open_resource(str(com_port))
        except pyvisa.errors.VisaIOError as err:
            logging.error(f"Can't open COM port {com_port}")
            logging.error(traceback.format_exc())
            self.instr = None
            return

        time.sleep(0.2)
        
        self.instr.read_termination = "\r"
        self.instr.write_termination = "\r"

        self.rm.visalib.set_buffer(self.instr.session, pyvisa.constants.BufferType.io_in, 1024)
        self.rm.visalib.set_buffer(self.instr.session, pyvisa.constants.BufferType.io_out, 1024)
        time.sleep(0.2)
        self.FlushTransmitBuffer()
        time.sleep(0.2)
        self.FlushReceiveBuffer()
        time.sleep(0.2)

    def FlushReceiveBuffer(self):
        # buffer operation can be found at https://pyvisa.readthedocs.io/en/latest/_modules/pyvisa/constants.html
        # re = self.rm.visalib.flush(self.instr.session, pyvisa.constants.BufferOperation.discard_receive_buffer)
        # print(re)
        self.instr.flush(pyvisa.constants.BufferOperation.discard_receive_buffer)

    def FlushTransmitBuffer(self):
        # buffer operation can be found at https://pyvisa.readthedocs.io/en/latest/_modules/pyvisa/constants.html
        # re = self.rm.visalib.flush(self.instr.session, pyvisa.constants.BufferOperation.flush_transmit_buffer)
        # print(re)
        self.instr.flush(pyvisa.constants.BufferOperation.discard_transmit_buffer)

    def reconnect_com(self):
        pass


class mainWindow(qt.QMainWindow):
    """GUI main window, including all device boxes."""

    def __init__(self, app):
        super().__init__()
        self.app = app
        self.running = True
        logging.getLogger().setLevel("WARNING")

        self.config = configparser.ConfigParser()
        self.config.optionxform = str
        self.config.read("main_config_latest.ini")

        self.box = widgets.NewBox(layout_type="grid")
        self.box.setStyleSheet("QGroupBox{border-width: 0 px;}")

        self.config = configparser.ConfigParser()
        self.config.optionxform = str
        self.config.read("main_config_latest.ini")

        self.setCentralWidget(self.box)
        self.resize(self.config.getint("general", "window_width"), self.config.getint("general", "window_height"))
        self.setWindowTitle("BigSky-YAG-control")

        self.tab = qt.QTabWidget()
        self.box.frame.addWidget(self.tab, 0, 0)

        ctrl_box = self.place_general_controls()
        self.tab.addTab(ctrl_box, "General")

        ctrl_box = self.place_flashlamp_controls()
        self.tab.addTab(ctrl_box, "Flashlamp")

        ctrl_box = self.place_qswitch_controls()
        self.tab.addTab(ctrl_box, "QSwitch")

        event_log_box = self.place_event_log_controls()
        self.box.frame.addWidget(event_log_box, 1, 0)

        self.show()

        self.start_control()

    def place_general_controls(self):
        """Place general control widgets."""

        ctrl_box = widgets.NewBox("grid")
        ctrl_box.setTitle("")
        ctrl_box.setStyleSheet("QGroupBox{border-width: 4px; padding-top: 18px; font-size: 15pt; font-weight: Normal}QPushButton{font: 10pt}QLabel{font: 10pt}QLineEdit{font: 10pt}QCheckBox{font: 10pt}")

        ctrl_box.frame.addWidget(qt.QLabel("COM port:"), 0, 0, alignment=PyQt6.QtCore.Qt.AlignmentFlag.AlignRight)
        # self.com_port_cb = widgets.NewComboBox(item_list=self.get_com_port_list(), current_item=self.config.get("setting", "com_port"))
        self.com_port_cb = widgets.NewComboBox(item_list=[self.config.get("setting", "com_port")], current_item=self.config.get("setting", "com_port"))
        self.com_port_cb.currentTextChanged[str].connect(lambda val, config_type="com_port": self.update_config(config_type, val))
        ctrl_box.frame.addWidget(self.com_port_cb, 0, 1)
        self.reconnect_com_pb = qt.QPushButton("Reconnect COM")
        self.reconnect_com_pb.clicked.connect(self.reconnect_com)
        ctrl_box.frame.addWidget(self.reconnect_com_pb, 1, 1)
        self.refresh_com_pb = qt.QPushButton("Refresh COM list")
        self.refresh_com_pb.clicked.connect(self.refresh_com)
        ctrl_box.frame.addWidget(self.refresh_com_pb, 1, 2)

        ctrl_box.frame.addWidget(qt.QLabel("loop cycle (s):"), 2, 0, alignment=PyQt6.QtCore.Qt.AlignmentFlag.AlignRight)
        self.loop_cycle_dsb = widgets.NewDoubleSpinBox(range=(0, 600), decimals=1)
        self.loop_cycle_dsb.setValue(self.config.getfloat("setting", "loop_cycle_seconds"))
        self.loop_cycle_dsb.valueChanged[float].connect(lambda val, config_type="loop_cycle_seconds": self.update_config(config_type, val))
        ctrl_box.frame.addWidget(self.loop_cycle_dsb, 2, 1)

        ctrl_box.frame.addWidget(qt.QLabel("Configurations:"), 3, 0, alignment=PyQt6.QtCore.Qt.AlignmentFlag.AlignRight)
        self.save_config_pb = qt.QPushButton("Save config")
        ctrl_box.frame.addWidget(self.save_config_pb, 3, 1)
        self.load_config_pb = qt.QPushButton("Load config")
        ctrl_box.frame.addWidget(self.load_config_pb, 3, 2)

        ctrl_box.frame.addWidget(qt.QLabel("Send custom command:"), 4, 0, alignment=PyQt6.QtCore.Qt.AlignmentFlag.AlignRight)
        self.message_le = qt.QLineEdit("Enter command here...")
        ctrl_box.frame.addWidget(self.message_le, 4, 1)

        ctrl_box.frame.addWidget(qt.QLabel(), 5, 0)

        ctrl_box.frame.addWidget(qt.QLabel("Serial number:"), 6, 0, alignment=PyQt6.QtCore.Qt.AlignmentFlag.AlignRight)
        self.serial_la = qt.QLabel("N/A")
        ctrl_box.frame.addWidget(self.serial_la, 6, 1)

        ctrl_box.frame.addWidget(qt.QLabel("Pump status:"), 7, 0, alignment=PyQt6.QtCore.Qt.AlignmentFlag.AlignRight)
        self.pump_status_la = qt.QLabel("N/A")
        ctrl_box.frame.addWidget(self.pump_status_la, 7, 1)
        self.toggle_pump_pb = qt.QPushButton("Toggle pump status")
        self.toggle_pump_pb.clicked.connect(lambda config_type="pump": self.toggle_status(config_type))
        ctrl_box.frame.addWidget(self.toggle_pump_pb, 7, 2)

        ctrl_box.frame.addWidget(qt.QLabel("Temperature (C):"), 8, 0, alignment=PyQt6.QtCore.Qt.AlignmentFlag.AlignRight)
        self.temp_la = qt.QLabel("N/A")
        ctrl_box.frame.addWidget(self.temp_la, 8, 1)

        ctrl_box.frame.addWidget(qt.QLabel("Shutter status:"), 9, 0, alignment=PyQt6.QtCore.Qt.AlignmentFlag.AlignRight)
        self.shutter_status_la = qt.QLabel("N/A")
        ctrl_box.frame.addWidget(self.shutter_status_la, 9, 1)
        self.toggle_shutter_pb = qt.QPushButton("Toggle shutter status")
        self.toggle_shutter_pb.clicked.connect(lambda config_type="shutter": self.toggle_status(config_type))
        ctrl_box.frame.addWidget(self.toggle_shutter_pb, 9, 2)

        # let column 100 grow if there are extra space (row index start from 0, default stretch is 0)
        ctrl_box.frame.setRowStretch(100, 1)

        ctrl_box.frame.setColumnStretch(1, 1)
        ctrl_box.frame.setColumnStretch(2, 1)

        return ctrl_box

    def place_flashlamp_controls(self):
        ctrl_box = widgets.NewBox("grid")
        ctrl_box.setTitle("")
        ctrl_box.setStyleSheet("QGroupBox{border-width: 4px; padding-top: 18px; font-size: 15pt; font-weight: Normal}QPushButton{font: 10pt}QLabel{font: 10pt}QLineEdit{font: 10pt}QCheckBox{font: 10pt}")

        ctrl_box.frame.addWidget(qt.QLabel("Flashlamp status:"), 0, 0, alignment=PyQt6.QtCore.Qt.AlignmentFlag.AlignRight)
        self.flashlamp_status_la = qt.QLabel("N/A")
        ctrl_box.frame.addWidget(self.flashlamp_status_la, 0, 1)
        self.toggle_flashlamp_pb = qt.QPushButton("Toggle flashlamp status")
        self.toggle_flashlamp_pb.clicked.connect(lambda config_type="flashlamp": self.toggle_status(config_type))
        ctrl_box.frame.addWidget(self.toggle_flashlamp_pb, 0, 2)

        ctrl_box.frame.addWidget(qt.QLabel("Flashlamp simmer:"), 1, 0, alignment=PyQt6.QtCore.Qt.AlignmentFlag.AlignRight)
        self.flashlamp_simmer_la = qt.QLabel("N/A")
        ctrl_box.frame.addWidget(self.flashlamp_simmer_la, 1, 1)
        self.toggle_simmer_pb = qt.QPushButton("Toggle flashlamp simmer")
        self.toggle_simmer_pb.clicked.connect(lambda config_type="simmer": self.toggle_status(config_type))
        ctrl_box.frame.addWidget(self.toggle_simmer_pb, 1, 2)

        ctrl_box.frame.addWidget(qt.QLabel("Flashlamp trigger:"), 2, 0, alignment=PyQt6.QtCore.Qt.AlignmentFlag.AlignRight)
        self.flashlamp_trigger_la = qt.QLabel("N/A")
        ctrl_box.frame.addWidget(self.flashlamp_trigger_la, 2, 1)
        self.flashlamp_trigger_cb = widgets.NewComboBox(item_list=["internal", "external"], current_item=self.config.get("setting", "flashlamp_trigger"))
        self.flashlamp_trigger_cb.currentTextChanged[str].connect(lambda val, config_type="flashlamp_trigger": self.update_config(config_type, val))
        self.flashlamp_trigger_cb.setToolTip("Choose trigger mode here.")
        ctrl_box.frame.addWidget(self.flashlamp_trigger_cb, 2, 2)

        ctrl_box.frame.addWidget(qt.QLabel("Flashlamp frequency (Hz):"), 3, 0, alignment=PyQt6.QtCore.Qt.AlignmentFlag.AlignRight)
        self.flashlamp_frequency_la = qt.QLabel("N/A")
        ctrl_box.frame.addWidget(self.flashlamp_frequency_la, 3, 1)
        self.flashlamp_frequency_dsb = widgets.NewDoubleSpinBox(range=(1, 99.99), decimals=3)
        self.flashlamp_frequency_dsb.setValue(self.config.getfloat("setting", "flashlamp_frequency_Hz"))
        self.flashlamp_frequency_dsb.valueChanged[float].connect(lambda val, config_type="flashlamp_frequency_Hz": self.update_config(config_type, val))
        self.flashlamp_frequency_dsb.setToolTip("Change flashlamp frequency here.")
        ctrl_box.frame.addWidget(self.flashlamp_frequency_dsb, 3, 2)

        ctrl_box.frame.addWidget(qt.QLabel("Flashlamp voltage (V):"), 4, 0, alignment=PyQt6.QtCore.Qt.AlignmentFlag.AlignRight)
        self.flashlamp_voltage_la = qt.QLabel("N/A")
        ctrl_box.frame.addWidget(self.flashlamp_voltage_la, 4, 1)
        self.flashlamp_voltage_sb = widgets.NewSpinBox(range=(500, 1800))
        self.flashlamp_voltage_sb.setValue(self.config.getint("setting", "flashlamp_voltage_V"))
        self.flashlamp_voltage_sb.valueChanged[int].connect(lambda val, config_type="flashlamp_voltage_V": self.update_config(config_type, val))
        self.flashlamp_voltage_sb.setToolTip("Change flashlamp voltage here.")
        ctrl_box.frame.addWidget(self.flashlamp_voltage_sb, 4, 2)

        ctrl_box.frame.addWidget(qt.QLabel("Flashlamp energy (J):"), 5, 0, alignment=PyQt6.QtCore.Qt.AlignmentFlag.AlignRight)
        self.flashlamp_energy_la = qt.QLabel("N/A")
        ctrl_box.frame.addWidget(self.flashlamp_energy_la, 5, 1)
        self.flashlamp_energy_dsb = widgets.NewDoubleSpinBox(range=(7, 23), decimals=3)
        self.flashlamp_energy_dsb.setValue(self.config.getfloat("setting", "flashlamp_energy_J"))
        self.flashlamp_energy_dsb.valueChanged[float].connect(lambda val, config_type="flashlamp_energy_J": self.update_config(config_type, val))
        self.flashlamp_energy_dsb.setToolTip("Change flashlamp energy here.")
        ctrl_box.frame.addWidget(self.flashlamp_energy_dsb, 5, 2)

        ctrl_box.frame.addWidget(qt.QLabel("Flashlamp capacitance (uF):"), 6, 0, alignment=PyQt6.QtCore.Qt.AlignmentFlag.AlignRight)
        self.flashlamp_capacitance_la = qt.QLabel("N/A")
        ctrl_box.frame.addWidget(self.flashlamp_capacitance_la, 6, 1)
        self.flashlamp_capacitance_dsb = widgets.NewDoubleSpinBox(range=(27, 33), decimals=3)
        self.flashlamp_capacitance_dsb.setValue(self.config.getfloat("setting", "flashlamp_capacitance_uF"))
        self.flashlamp_capacitance_dsb.valueChanged[float].connect(lambda val, config_type="flashlamp_capacitance_uF": self.update_config(config_type, val))
        self.flashlamp_capacitance_dsb.setToolTip("Change flashlamp capacitance here.")
        ctrl_box.frame.addWidget(self.flashlamp_capacitance_dsb, 6, 2)

        ctrl_box.frame.addWidget(qt.QLabel("Flashlamp counter:"), 7, 0, alignment=PyQt6.QtCore.Qt.AlignmentFlag.AlignRight)
        self.flashlamp_counter_la = qt.QLabel("N/A")
        ctrl_box.frame.addWidget(self.flashlamp_counter_la, 7, 1)

        ctrl_box.frame.addWidget(qt.QLabel("Flashlamp user counter:"), 8, 0, alignment=PyQt6.QtCore.Qt.AlignmentFlag.AlignRight)
        self.flashlamp_user_counter_la = qt.QLabel("N/A")
        ctrl_box.frame.addWidget(self.flashlamp_user_counter_la, 8, 1)
        self.flashlamp_user_counter_pb = qt.QPushButton("Reset user counter")
        ctrl_box.frame.addWidget(self.flashlamp_user_counter_pb, 8, 2)
 
        # let column 100 grow if there are extra space (row index start from 0, default stretch is 0)
        ctrl_box.frame.setRowStretch(100, 1)

        ctrl_box.frame.setColumnStretch(1, 1)
        ctrl_box.frame.setColumnStretch(2, 1)

        return ctrl_box

    def place_qswitch_controls(self):
        ctrl_box = widgets.NewBox("grid")
        ctrl_box.setTitle("")
        ctrl_box.setStyleSheet("QGroupBox{border-width: 4px; padding-top: 18px; font-size: 15pt; font-weight: Normal}QPushButton{font: 10pt}QLabel{font: 10pt}QLineEdit{font: 10pt}QCheckBox{font: 10pt}")

        ctrl_box.frame.addWidget(qt.QLabel("QSwitch status:"), 0, 0, alignment=PyQt6.QtCore.Qt.AlignmentFlag.AlignRight)
        self.qswitch_status_la = qt.QLabel("N/A")
        ctrl_box.frame.addWidget(self.qswitch_status_la, 0, 1)
        self.toggle_qswitch_pb = qt.QPushButton("Toggle qswitch status")
        self.toggle_qswitch_pb.clicked.connect(lambda config_type="qswitch": self.toggle_status(config_type))
        ctrl_box.frame.addWidget(self.toggle_qswitch_pb, 0, 2)

        ctrl_box.frame.addWidget(qt.QLabel("QSwitch trigger:"), 1, 0, alignment=PyQt6.QtCore.Qt.AlignmentFlag.AlignRight)
        self.qswitch_mode_la = qt.QLabel("N/A")
        ctrl_box.frame.addWidget(self.qswitch_mode_la, 1, 1)
        self.qswitch_mode_cb = widgets.NewComboBox(item_list=["auto", "burst", "external"], current_item=self.config.get("setting", "qswitch_mode"))
        self.qswitch_mode_cb.currentTextChanged[str].connect(lambda val, config_type="qswitch_mode": self.update_config(config_type, val))
        self.qswitch_mode_cb.setToolTip("Choose trigger mode here.")
        ctrl_box.frame.addWidget(self.qswitch_mode_cb, 1, 2)

        ctrl_box.frame.addWidget(qt.QLabel("QSwitch delay (us):"), 2, 0, alignment=PyQt6.QtCore.Qt.AlignmentFlag.AlignRight)
        self.qswitch_delay_la = qt.QLabel("N/A")
        ctrl_box.frame.addWidget(self.qswitch_delay_la, 2, 1)
        self.qswitch_delay_sb = widgets.NewSpinBox(range=(10, 999))
        self.qswitch_delay_sb.setValue(self.config.getint("setting", "qswitch_delay_us"))
        self.qswitch_delay_sb.valueChanged[int].connect(lambda val, config_type="qswitch_delay_us": self.update_config(config_type, val))
        self.qswitch_delay_sb.setToolTip("Change QSwitch delay here.")
        ctrl_box.frame.addWidget(self.qswitch_delay_sb, 2, 2)

        ctrl_box.frame.addWidget(qt.QLabel("QSwitch freq divider:"), 3, 0, alignment=PyQt6.QtCore.Qt.AlignmentFlag.AlignRight)
        self.qswitch_freq_divider_la = qt.QLabel("N/A")
        ctrl_box.frame.addWidget(self.qswitch_freq_divider_la, 3, 1)
        self.qswitch_freq_divider_sb = widgets.NewSpinBox(range=(1, 99))
        self.qswitch_freq_divider_sb.setValue(self.config.getint("setting", "qswitch_freq_divider"))
        self.qswitch_freq_divider_sb.valueChanged[int].connect(lambda val, config_type="qswitch_freq_divider": self.update_config(config_type, val))
        self.qswitch_freq_divider_sb.setToolTip("Change QSwitch frequency divider here.")
        ctrl_box.frame.addWidget(self.qswitch_freq_divider_sb, 3, 2)

        ctrl_box.frame.addWidget(qt.QLabel("QSwitch burst pulses:"), 4, 0, alignment=PyQt6.QtCore.Qt.AlignmentFlag.AlignRight)
        self.qswitch_burst_pulses_la = qt.QLabel("N/A")
        ctrl_box.frame.addWidget(self.qswitch_burst_pulses_la, 4, 1)
        self.qswitch_burst_pulses_sb = widgets.NewSpinBox(range=(1, 999))
        self.qswitch_burst_pulses_sb.setValue(self.config.getint("setting", "qswitch_burst_pulses"))
        self.qswitch_burst_pulses_sb.valueChanged[int].connect(lambda val, config_type="qswitch_vurst_pulses": self.update_config(config_type, val))
        self.qswitch_burst_pulses_sb.setToolTip("Change QSwitch burst pulse number here.")
        ctrl_box.frame.addWidget(self.qswitch_burst_pulses_sb, 4, 2)

        ctrl_box.frame.addWidget(qt.QLabel("QSwitch counter:"), 5, 0, alignment=PyQt6.QtCore.Qt.AlignmentFlag.AlignRight)
        self.qswitch_counter_la = qt.QLabel("N/A")
        ctrl_box.frame.addWidget(self.qswitch_counter_la, 5, 1)

        ctrl_box.frame.addWidget(qt.QLabel("QSwitch user counter:"), 6, 0, alignment=PyQt6.QtCore.Qt.AlignmentFlag.AlignRight)
        self.qswitch_user_counter_la = qt.QLabel("N/A")
        ctrl_box.frame.addWidget(self.qswitch_user_counter_la, 6, 1)
        self.qswitch_user_counter_pb = qt.QPushButton("Reset user counter")
        ctrl_box.frame.addWidget(self.qswitch_user_counter_pb, 6, 2)

        # let column 100 grow if there are extra space (row index start from 0, default stretch is 0)
        ctrl_box.frame.setRowStretch(100, 1)

        ctrl_box.frame.setColumnStretch(1, 1)
        ctrl_box.frame.setColumnStretch(2, 1)

        return ctrl_box

    def place_event_log_controls(self):
        """Place event log widgets."""

        event_log_box = widgets.NewBox("grid")
        event_log_box.setTitle("Event Log")
        event_log_box.setStyleSheet("QGroupBox{border-width: 4px; padding-top: 18px; font-size: 15pt; font-weight: Normal}QPushButton{font: 10pt}QLabel{font: 10pt}QLineEdit{font: 10pt}QCheckBox{font: 10pt}")

        self.clear_log_pb = qt.QPushButton('Clear event log')
        event_log_box.frame.addWidget(self.clear_log_pb, 0, 0)

        self.event_log_tb = qt.QTextBrowser()
        self.clear_log_pb.clicked.connect(self.event_log_tb.clear)
        event_log_box.frame.addWidget(self.event_log_tb, 1, 0)

        return event_log_box

    # for a really nice tutorial for QThread(), see https://realpython.com/python-pyqt-qthread/
    def start_control(self):
        """Start a worker thread. Be called when the class instantiates."""

        self.thread = PyQt6.QtCore.QThread()

        self.worker = Worker(self)
        self.worker.moveToThread(self.thread)

        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.thread.wait)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.worker.update[dict].connect(self.update_labels)

        self.thread.start()

    def update_config(self, config_type, val):
        self.config["setting"][config_type] = str(val)
        self.worker.cmd_queue.put((config_type, val))

    def toggle_status(self, config_type):
        self.worker.cmd_queue.put((config_type, "toggle"))

    def update_labels(self, info_dict):
        pass

    def refresh_com(self):
        """Get latests list of available com ports. And reconnect to YAG."""

        com = self.com_port_cb.currentText()
        self.com_port_cb.blockSignals(True)
        self.com_port_cb.clear()
        self.com_port_cb.addItems(self.get_com_port_list())
        self.com_port_cb.setCurrentText(com)
        self.com_port_cb.blockSignals(False)
        com = self.com_port_cb.currentText()
        self.config["setting"]["com_port"] = com

        self.reconnect_com()

    def reconnect_com(self):
        pass

    def get_com_port_list(self):
        """Get a list of com ports that have device connected."""

        rm = pyvisa.ResourceManager()
        return rm.list_resources()

    def closeEvent(self, event):
        configfile = open("main_config_latest.ini", "w")
        self.config["general"]["window_width"] = str(self.frameGeometry().width())
        self.config["general"]["window_height"] = str(self.frameGeometry().height())
        self.config.write(configfile)
        configfile.close()

        super().closeEvent(event)


if __name__ == '__main__':
    app = qt.QApplication(sys.argv)
    # screen = app.screens()
    # monitor_dpi = screen[0].physicalDotsPerInch()
    monitor_dpi = 254
    # palette = {"dark":qdarkstyle.dark.palette.DarkPalette, "light":qdarkstyle.light.palette.LightPalette}
    # app.setStyleSheet(qdarkstyle._load_stylesheet(qt_api='pyqt5', palette=palette["dark"]))
    prog = mainWindow(app)
    
    try:
        sys.exit(app.exec())
    except SystemExit:
        print("\nApp is closing...")