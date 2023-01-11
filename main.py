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
            self.update.emit({"error": f"Ununable to connect to BigSky YAG\n{err}."})
            self.finished.emit()
            return

        t0 = 0
        while self.parent.running:
            while not self.cmd_queue.empty():
                config_type, val = self.cmd_queue.get()
                try:
                    if config_type == "toggle_pump":
                        self.yag.pump = not self.yag.pump
                        self.update.emit({"pump_status": self.yag.pump})
                    elif config_type == "toggle_shutter":
                        self.yag.shutter = not self.yag.shutter
                        self.update.emit({"shutter_status": self.yag.shutter})
                    elif config_type == "toggle_flashlamp":
                        flashlamp_status = self.yag.laser_status.flashlamp
                        if flashlamp_status in [0, 1]:
                            # STOP or SINGLE
                            self.yag.flashlamp.activate()
                        elif flashlamp_status == 2:
                            # START
                            self.yag.flashlamp.stop()
                        self.update.emit({"flashlamp_status": self.yag.laser_status.flashlamp})
                    elif config_type == "toggle_simmer":
                        # simmer_status = self.yag.laser_status.simmer
                        self.yag.flashlamp.simmer()
                        self.update.emit({"simmer_status": self.yag.laser_status.simmer})
                    elif config_type == "flashlamp_trigger":
                        self.yag.flashlamp.trigger = val
                        self.update.emit({config_type: self.yag.flashlamp.trigger})
                    elif config_type == "flashlamp_frequency_Hz":
                        self.yag.flashlamp.frequency = val
                        self.update.emit({config_type: self.yag.flashlamp.frequency})
                    elif config_type == "flashlamp_voltage_V":
                        self.yag.flashlamp.voltage = val
                        self.update.emit({config_type: self.yag.flashlamp.voltage})
                    elif config_type == "flashlamp_energy_J":
                        self.yag.flashlamp.energy = val
                        self.update.emit({config_type: self.yag.flashlamp.energy})
                    elif config_type == "flashlamp_capacitance_uF":
                        self.yag.flashlamp.capacitance = val
                        self.update.emit({config_type: self.yag.flashlamp.capacitance})
                    elif config_type == "falshlamp_reset_user_counter":
                        self.yag.flashlamp.user_counter_reset()
                        self.update.emit({"flashlamp_user_counter": self.yag.flashlamp.user_counter})
                    elif config_type == "toggle_qswitch":
                        if self.yag.qswitch.status:
                            self.yag.qswitch.start()
                        else:
                            self.yag.qswitch.stop()
                        self.update.emit({"qswitch_status": self.yag.qswitch.status})
                    elif config_type == "qswitch_mode":
                        self.yag.qswitch.mode = val
                        self.update.emit({config_type: self.yag.qswitch.mode})
                    elif config_type == "qswitch_delay_us":
                        self.yag.qswitch.delay = val
                        self.update.emit({config_type: self.yag.qswitch.delay})
                    elif config_type == "qswitch_freq_divider":
                        self.yag.qswitch.frequency_divider = val
                        self.update.emit({config_type: self.yag.qswitch.frequency_divider})
                    elif config_type == "qswitch_burst_pulses":
                        self.yag.qswitch.pulses = val
                        self.update.emit({config_type: self.yag.qswitch.pulses})
                    elif config_type == "qswitch_reset_user_counter":
                        # self.yag.qswitch.user_counter_reset()
                        self.update.emit({"qswitch_user_counter": self.yag.flashlamp.user_counter})
                    else:
                        self.update.emit({"error": f"Unsupported command {(config_type, val)}."})
                except Exception as err:
                    self.update.emit({"error": f"Ununable to read/write YAG parameters {config_type} \n {err}."})
                
            if self.parent.running and (time.time() - t0 > self.parent.config.getfloat("setting", "loop_cycle_seconds")):
                try:
                    self.update.emit({"serial_number": self.yag.serial_number})
                except Exception as err:
                    self.update.emit({"error": f"Ununable to read YAG serial number\n {err}."})

                try:
                    self.update.emit({"pump_status": self.yag.pump})
                except Exception as err:
                    self.update.emit({"error": f"Ununable to read YAG pump status\n {err}."})

                try:
                    self.update.emit({"temperature_C": self.yag.temperature_cooling_group})
                except Exception as err:
                    self.update.emit({"error": f"Ununable to read YAG cooling group temperature\n {err}."})

                try:
                    self.update.emit({"shutter_status": self.yag.shutter})
                except Exception as err:
                    self.update.emit({"error": f"Ununable to read YAG shutter status\n {err}."})

                try:
                    self.update.emit({"flashlamp_status": self.yag.laser_status.flashlamp})
                except Exception as err:
                    self.update.emit({"error": f"Ununable to read YAG flashlamp status\n {err}."})

                try:
                    self.update.emit({"simmer_status": self.yag.laser_status.simmer})
                except Exception as err:
                    self.update.emit({"error": f"Ununable to read YAG flashlamp simmer status\n {err}."})

                try:
                    self.update.emit({"flashlamp_trigger": self.yag.flashlamp.trigger})
                except Exception as err:
                    self.update.emit({"error": f"Ununable to read YAG flashlamp trigger\n {err}."})

                try:
                    self.update.emit({"flashlamp_frequency_Hz": self.yag.flashlamp.frequency})
                except Exception as err:
                    self.update.emit({"error": f"Ununable to read YAG flashlamp frequency\n {err}."})

                try:
                    self.update.emit({"flashlamp_voltage_V": self.yag.flashlamp.voltage})
                except Exception as err:
                    self.update.emit({"error": f"Ununable to read YAG flashlamp voltage\n {err}."})

                try:
                    self.update.emit({"flashlamp_energy_J": self.yag.flashlamp.energy})
                except Exception as err:
                    self.update.emit({"error": f"Ununable to read YAG flashlamp energy\n {err}."})

                try:
                    self.update.emit({"flashlamp_capacitance_uF": self.yag.flashlamp.capacitance})
                except Exception as err:
                    self.update.emit({"error": f"Ununable to read YAG flashlamp capacitance\n {err}."})

                try:
                    self.update.emit({"flashlamp_counter": self.yag.flashlamp.counter})
                except Exception as err:
                    self.update.emit({"error": f"Ununable to read YAG flashlamp counter\n {err}."})

                try:
                    self.update.emit({"flashlamp_user_counter": self.yag.flashlamp.counter})
                except Exception as err:
                    self.update.emit({"error": f"Ununable to read YAG flashlamp user counter\n {err}."})

                try:
                    self.update.emit({"qswitch_status": self.yag.qswitch.status})
                except Exception as err:
                    self.update.emit({"error": f"Ununable to read YAG qswitch status\n {err}."})

                try:
                    self.update.emit({"qswitch_mode": self.yag.qswitch.mode})
                except Exception as err:
                    self.update.emit({"error": f"Ununable to read YAG qswitch mode\n {err}."})

                try:
                    self.update.emit({"qswitch_delay_us": self.yag.qswitch.delay})
                except Exception as err:
                    self.update.emit({"error": f"Ununable to read YAG qswitch delay\n {err}."})

                try:
                    self.update.emit({"qswitch_freq_divider": self.yag.qswitch.frequency_divider})
                except Exception as err:
                    self.update.emit({"error": f"Ununable to read YAG qswitch frequency divider\n {err}."})

                try:
                    self.update.emit({"qswitch_burst_pulses": self.yag.qswitch.pulses})
                except Exception as err:
                    self.update.emit({"error": f"Ununable to read YAG qswitch burst pulse number\n {err}."})

                try:
                    self.update.emit({"qswitch_counter": self.yag.qswitch.counter})
                except Exception as err:
                    self.update.emit({"error": f"Ununable to read YAG qswitch counter\n {err}."})

                try:
                    self.update.emit({"qswitch_user_counter": self.yag.qswitch.user_counter})
                except Exception as err:
                    self.update.emit({"error": f"Ununable to read YAG qswitch user counter\n {err}."})

            time.sleep(0.05)

        self.finished.emit()


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
        self.toggle_pump_pb.clicked.connect(lambda config_type="toggle_pump": self.update_config(config_type))
        ctrl_box.frame.addWidget(self.toggle_pump_pb, 7, 2)

        ctrl_box.frame.addWidget(qt.QLabel("Cooling group temperature (C):"), 8, 0, alignment=PyQt6.QtCore.Qt.AlignmentFlag.AlignRight)
        self.temp_la = qt.QLabel("N/A")
        ctrl_box.frame.addWidget(self.temp_la, 8, 1)

        ctrl_box.frame.addWidget(qt.QLabel("Shutter status:"), 9, 0, alignment=PyQt6.QtCore.Qt.AlignmentFlag.AlignRight)
        self.shutter_status_la = qt.QLabel("N/A")
        ctrl_box.frame.addWidget(self.shutter_status_la, 9, 1)
        self.toggle_shutter_pb = qt.QPushButton("Toggle shutter status")
        self.toggle_shutter_pb.clicked.connect(lambda config_type="toggle_shutter": self.update_config(config_type))
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
        self.toggle_flashlamp_pb.clicked.connect(lambda config_type="toggle_flashlamp": self.update_config(config_type))
        ctrl_box.frame.addWidget(self.toggle_flashlamp_pb, 0, 2)

        ctrl_box.frame.addWidget(qt.QLabel("Flashlamp simmer:"), 1, 0, alignment=PyQt6.QtCore.Qt.AlignmentFlag.AlignRight)
        self.flashlamp_simmer_la = qt.QLabel("N/A")
        ctrl_box.frame.addWidget(self.flashlamp_simmer_la, 1, 1)
        self.toggle_simmer_pb = qt.QPushButton("Toggle flashlamp simmer")
        self.toggle_simmer_pb.clicked.connect(lambda config_type="toggle_simmer": self.update_config(config_type))
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
        self.flashlamp_user_counter_pb.clicked.connect(lambda config_type="reset_flashlamp_user_counter": self.update_config(config_type))
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
        self.toggle_qswitch_pb.clicked.connect(lambda config_type="toggle_qswitch": self.update_config(config_type))
        ctrl_box.frame.addWidget(self.toggle_qswitch_pb, 0, 2)

        ctrl_box.frame.addWidget(qt.QLabel("QSwitch mode:"), 1, 0, alignment=PyQt6.QtCore.Qt.AlignmentFlag.AlignRight)
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
        self.qswitch_user_counter_pb.clicked.connect(lambda config_type="reset_qswitch_user_counter": self.update_config(config_type))
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

    def update_config(self, config_type, val=None):
        if config_type in self.config["setting"].keys():
            self.config["setting"][config_type] = str(val)

        if config_type == "com_port":
            self.reconnect_com()
        elif config_type == "loop_cycle_seconds":
            return
        else:
            self.worker.cmd_queue.put((config_type, val))

    @PyQt6.QtCore.pyqtSlot(tuple)
    def update_labels(self, info_dict):
        if "serial_number" in info_dict.keys():
            self.serial_number_la.setText(info_dict["serial_number"])
        elif "temperature_C" in info_dict.keys():
            self.temp_la.setText(info_dict["temperature_C"])
        elif "pump_status" in info_dict.keys():
            self.pump_status_la.setText(info_dict["pump_status"])
        elif "shutter_status" in info_dict.keys():
            self.shutter_status_la.setText(info_dict["shutter_status"])
        elif "flashlamp_status" in info_dict.keys():
            self.flashlamp_status_la.setText(info_dict["flashlamp_status"])
        elif "flashlamp_trigger" in info_dict.keys():
            self.flashlamp_trigger_la.setText(info_dict["flashlamp_trigger"])
        elif "flashlamp_frequency_Hz" in info_dict.keys():
            self.flashlamp_frequency_la.setText(info_dict["flashlamp_frequency_Hz"])
        elif "flashlamp_voltage_V" in info_dict.keys():
            self.flashlamp_voltage_la.setText(info_dict["flashlamp_voltage_V"])
        elif "flashlamp_energy_J" in info_dict.keys():
            self.flashlamp_energy_la.setText(info_dict["flashlamp_energy_J"])
        elif "flashlamp_capacitance_uF" in info_dict.keys():
            self.flashlamp_capacitance_la.setText(info_dict["flashlamp_capacitance_uF"])
        elif "flashlamp_counter" in info_dict.keys():
            self.flashlamp_counter_la.setText(info_dict["flashlamp_counter"])
        elif "flashlamp_user_couter" in info_dict.keys():
            self.flashlamp_user_counter_la.setText(info_dict["flashlamp_user_counter"])
        elif "qswitch_status" in info_dict.keys():
            self.qswitch_status_la.setText(info_dict["qswitch_status"])
        elif "qswitch_mode" in info_dict.keys():
            self.qswitch_mode_la.setText(info_dict["qswitch_mode"])
        elif "qswitch_delay_us" in info_dict.keys():
            self.qswitch_delay_la.setText(info_dict["qswitch_delay_us"])
        elif "qswitch_frequency_divider" in info_dict.keys():
            self.qswitch_freq_divider_la.setText(info_dict["qswitch_frequency_divider"])
        elif "qswitch_burst_pulses" in info_dict.keys():
            self.qswitch_burst_pulses_la.setText(info_dict["qswitch_burst_pulses"])
        elif "qswitch_counter" in info_dict.keys():
            self.flashlamp_counter_la.setText(info_dict["qswitch_counter"])
        elif "qswitch_user_couter" in info_dict.keys():
            self.flashlamp_user_counter_la.setText(info_dict["qswitch_user_counter"])
        
        elif "error" in info_dict.keys():
            pass


    def refresh_com(self):
        """Get latests list of available com ports. And reconnect to YAG."""

        com = self.com_port_cb.currentText()
        self.com_port_cb.blockSignals(True)
        self.com_port_cb.clear()
        self.com_port_cb.addItems(self.get_com_port_list())
        self.com_port_cb.setCurrentText(com)
        self.com_port_cb.blockSignals(False)
        com_new = self.com_port_cb.currentText()

        if com_new != com:
            self.config["setting"]["com_port"] = com
            self.reconnect_com()

    def reconnect_com(self):
        self.running = False
        try:
            self.thread.quit()
            self.thread.wait()
        except RuntimeError as err:
            pass
        time.sleep(0.2)

        self.running = True
        self.start_control() 

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