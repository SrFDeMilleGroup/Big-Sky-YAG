import sys, os, time
import logging, traceback
import configparser, queue
from collections import deque
import PyQt5
import PyQt5.QtWidgets as qt
import numpy as np
import qdarkstyle, pyvisa

import widgets
from big_sky_yag import BigSkyYag

def pt_to_px(pt):
    """Convert GUI widget size from unit pt to unit px using monitor dpi"""

    return round(pt*monitor_dpi/72)


class Worker(PyQt5.QtCore.QObject):
    """A worker class that controls Hornet. This class should be run in a separate thread."""

    finished = PyQt5.QtCore.pyqtSignal()
    update = PyQt5.QtCore.pyqtSignal(dict)
    update_event_log = PyQt5.QtCore.pyqtSignal(str)

    def __init__(self, parent):
        super().__init__()
        self.parent = parent
        self.cmd_queue = queue.Queue()

    def exec_cmd(self):
         while not self.cmd_queue.empty():
            config_type, val = self.cmd_queue.get()
            try:
                if config_type == "toggle_pump":
                    self.update_event_log.emit("Toggling pump status...")
                    self.yag.pump = not self.yag.pump
                    pump_status = "ON" if self.yag.pump else "OFF"
                    self.update.emit({"type": "pump_status", "success": True, "value": pump_status})
                    self.update_event_log.emit(f"Toggled pump status. It reads {pump_status} now.")

                elif config_type == "toggle_shutter":
                    self.update_event_log.emit("Toggling shutter status...")
                    self.yag.shutter = not self.yag.shutter
                    shutter_status = "OPEN" if self.yag.shutter else "CLOSED"
                    self.update.emit({"type": "shutter_status", "success": True, "value": shutter_status})
                    self.update_event_log.emit(f"Toggled shutter status. It reads {shutter_status} now.")

                elif config_type == "toggle_flashlamp":
                    self.update_event_log.emit("Toggling flashlamp status...")
                    flashlamp_status = self.yag.laser_status.flashlamp
                    if flashlamp_status.name in ["START", "SINGLE"]:
                        self.yag.flashlamp.stop()
                    elif flashlamp_status.name == "STOP":
                        self.yag.flashlamp.activate()
                    flashlamp_status = self.yag.laser_status.flashlamp.name
                    self.update.emit({"type": "flashlamp_status", "success": True, "value": flashlamp_status})
                    self.update_event_log.emit(f"Toggled flashlamp status. It reads {flashlamp_status} now.")

                elif config_type == "turn_on_simmer":
                    self.update_event_log.emit("Turning on flashlamp simmer...")
                    self.yag.flashlamp.simmer()
                    simmer_status = "ON" if self.yag.laser_status.simmer else "OFF"
                    self.update.emit({"type": "simmer_status", "success": True, "value": simmer_status})
                    self.update_event_log.emit(f"Turned flashlamp simmer on. It reads {simmer_status} now.")

                elif config_type == "flashlamp_trigger":
                    self.update_event_log.emit("Setting flashlamp trigger...")
                    self.yag.flashlamp.trigger = val
                    trigger = self.yag.flashlamp.trigger.name
                    self.update.emit({"type": config_type, "success": True, "value": trigger})
                    self.update_event_log.emit(f"Set flashlamp trigger status. It reads {trigger} now.")

                elif config_type == "flashlamp_frequency_Hz":
                    self.update_event_log.emit("Setting flashlamp frequency...")
                    self.yag.flashlamp.frequency = val
                    freq = "{:.2f}".format(self.yag.flashlamp.frequency)
                    self.update.emit({"type": config_type, "success": True, "value": freq})
                    self.update_event_log.emit(f"Set flashlamp frequency. It reads {freq} Hz now.")

                elif config_type == "flashlamp_voltage_V":
                    self.update_event_log.emit("Setting flashlamp frequency...")
                    self.yag.flashlamp.voltage = val
                    voltage = str(self.yag.flashlamp.voltage)
                    self.update.emit({"type": config_type, "success": True, "value": voltage})
                    self.update_event_log.emit(f"Set flashlamp voltage. It reads {voltage} V now.")

                elif config_type == "flashlamp_energy_J":
                    self.update_event_log.emit("Setting flashlamp energy...")
                    self.yag.flashlamp.energy = val
                    energy = "{:.1f}".format(self.yag.flashlamp.energy)
                    self.update.emit({"type": config_type, "success": True, "value": energy})
                    self.update_event_log.emit(f"Set flashlamp energy. It reads {energy} J now.")

                elif config_type == "flashlamp_capacitance_uF":
                    self.update_event_log.emit("Setting flashlamp capacitance...")
                    self.yag.flashlamp.capacitance = val
                    cap = "{:.1f}".format(self.yag.flashlamp.capacitance)
                    self.update.emit({"type": config_type, "success": True, "value": cap})
                    self.update_event_log.emit(f"Set flashlamp capacitance. It reads {cap} uF now.")

                elif config_type == "falshlamp_reset_user_counter":
                    self.update_event_log.emit("Resetting flashlamp user counter...")
                    self.yag.flashlamp.user_counter_reset()
                    count = str(self.yag.flashlamp.user_counter)
                    self.update.emit({"type": "flashlamp_user_counter", "success": True, "value": count})
                    self.update_event_log.emit(f"Reset flashlamp user counter. It reads {count} now.")

                elif config_type == "toggle_qswitch":
                    self.update_event_log.emit("Toggling QSwitch status...")
                    if self.yag.qswitch.status:
                        self.yag.qswitch.stop()
                        time.sleep(0.05)
                        self.yag.qswitch.off()
                    else:
                        self.yag.qswitch.on()
                        time.sleep(0.05)
                        self.yag.qswitch.start()
                    status = "ON" if self.yag.qswitch.status else "OFF"
                    self.update.emit({"type": "qswitch_status", "success": True, "value": status})
                    self.update_event_log.emit(f"Toggled QSwitch status. It reads {status} now.")

                elif config_type == "qswitch_mode":
                    self.update_event_log.emit("Setting QSwitch mode...")
                    self.yag.qswitch.mode = val
                    mode = self.yag.qswitch.mode.name
                    self.update.emit({"type": config_type, "success": True, "value": mode})
                    self.update_event_log.emit(f"Set QSwitch mode. It reads {mode} now.")

                elif config_type == "qswitch_delay_us":
                    self.update_event_log.emit("Setting QSwitch delay...")
                    self.yag.qswitch.delay = val
                    delay = str(self.yag.qswitch.delay)
                    self.update.emit({"type": config_type, "success": True, "value": delay})
                    self.update_event_log.emit(f"Set QSwitch delay. It reads {delay} us now.")

                elif config_type == "qswitch_freq_divider":
                    self.update_event_log.emit("Setting QSwitch frequency divider...")
                    self.yag.qswitch.frequency_divider = val
                    freq_divider = str(self.yag.qswitch.frequency_divider)
                    self.update.emit({"type": config_type, "success": True, "value": freq_divider})
                    self.update_event_log.emit(f"Set QSwitch frequency divider. It reads {freq_divider} now.")

                elif config_type == "qswitch_burst_pulses":
                    self.update_event_log.emit("Setting QSwitch burst pulses...")
                    self.yag.qswitch.pulses = val
                    pulses = str(self.yag.qswitch.pulses)
                    self.update.emit({"type": config_type, "success": True, "value": pulses})
                    self.update_event_log.emit(f"Set QSwitch burst pulses. It reads {pulses} now.")

                elif config_type == "qswitch_reset_user_counter":
                    self.update_event_log.emit(f"Resetting QSwitch user counter...")
                    self.yag.qswitch.user_counter_reset()
                    count = str(self.yag.qswitch.user_counter)
                    self.update.emit({"type": "qswitch_user_counter", "success": True, "value": count})
                    self.update_event_log.emit(f"Reset QSwitch user counter. It reads {count} now.")

                elif config_type == "custom_command":
                    self.update_event_log.emit(f"Sending custom command '{val}'...")
                    retval = self.yag.write(val)
                    self.update_event_log.emit(f"Sent custom command '{val}'. It returns '{retval}'.")

                elif config_type == "activate_yag":
                    flashlamp_status = self.yag.laser_status.flashlamp.name
                    if flashlamp_status in ["START", "SINGLE"]:
                        self.update_event_log.emit("Deactivating YAG...")
                        self.yag.flashlamp.stop()
                        time.sleep(0.05)
                        self.yag.qswitch.stop()
                        time.sleep(0.05)
                        self.yag.qswitch.off()
                        time.sleep(0.05)
                        flashlamp_status = self.yag.laser_status.flashlamp.name
                        shutter_status = self.yag.shutter
                        qswitch_status = self.yag.qswitch.status
                        if (flashlamp_status == "STOP") and (not shutter_status) and (not qswitch_status):
                            return_str = "Deactivated YAG. "
                        else:
                            return_str = "Fail to deactivate YAG. "
                    elif flashlamp_status == "STOP":
                        self.update_event_log.emit("Activating YAG...")
                        self.yag.shutter = True
                        time.sleep(0.05)
                        self.yag.qswitch.on()
                        time.sleep(0.05)
                        self.yag.qswitch.start()
                        time.sleep(0.05)
                        self.yag.flashlamp.activate()
                        time.sleep(0.05)
                        flashlamp_status = self.yag.laser_status.flashlamp.name
                        shutter_status = self.yag.shutter
                        qswitch_status = self.yag.qswitch.status
                        if (flashlamp_status in ["START", "SINGLE"]) and (shutter_status) and (qswitch_status):
                            return_str = "Activated YAG. "
                        else:
                            return_str = "Fail to activate YAG. "

                    return_str += f"Flashlamp reads {flashlamp_status} now. "
                    return_str += "Qswitch reads ON. " if qswitch_status else "Qswitch reads OFF. "
                    return_str += "Shutter reads OPEN." if shutter_status else "Shutter reads CLOSED."
                    self.update_event_log.emit(return_str)

                else:
                    self.update_event_log.emit(f"Unsupported command {(config_type, val)}.")

            except Exception as err:
                try:
                    self.update.emit({"type": config_type, "success": False, "value": "Fail to read/write"})
                    self.update_event_log.emit(f"Ununable to read/write YAG parameters {config_type}.\n{err}")
                except RuntimeError:
                    # RunTime Error could be raised when COM port is disconnected and this object is deleted
                    pass


    def run(self):
        """Repeatedly read from the device."""

        try:
            self.yag = BigSkyYag(resource_name=self.parent.config["setting"]["com_port"])
            self.update_event_log.emit(f'Connected to {self.parent.config["setting"]["com_port"]}.')
        except Exception as err:
            self.update_event_log.emit(f"Can't connect to Big Sky YAG at COM port {self.parent.config['setting']['com_port']}.\n"+str(err))
            self.finished.emit()
            return

        t0 = 0
        while self.parent.running:
            self.exec_cmd()

            if self.parent.running and (time.time() - t0 > self.parent.config.getfloat("setting", "loop_cycle_seconds")):
                t0 = time.time()

                try:
                    self.update.emit({"type": "serial_number", "success": True, "value": self.yag.serial_number})
                except Exception as err:
                    try:
                        self.update.emit({"type": "serial_number", "success": False, "value": "Fail to read"})
                        # self.update_event_log.emit(f"Ununable to read YAG serial number.\n{err}")
                    except RuntimeError:
                        pass

                if not self.parent.running:
                    break

                try:
                    self.update.emit({"type": "pump_status", "success": True, "value": "ON" if self.yag.pump else "OFF"})
                except Exception as err:
                    try:
                        self.update.emit({"type": "pump_status", "success": False, "value": "Fail to read"})
                        # self.update_event_log.emit(f"Ununable to read YAG pump status.\n{err}")
                    except RuntimeError:
                        pass

                if not self.parent.running:
                    break

                try:
                    self.update.emit({"type": "temperature_C", "success": True, "value": str(self.yag.temperature_cooling_group)})
                except Exception as err:
                    try:
                        self.update.emit({"type": "temperature_C", "success": False, "value": "Fail to read"})
                        # self.update_event_log.emit(f"Ununable to read YAG cooling group temperature.\n{err}")
                    except RuntimeError:
                        pass

                if not self.parent.running:
                    break

                try:
                    self.update.emit({"type": "shutter_status", "success": True, "value": "OPEN" if self.yag.shutter else "CLOSED"})
                except Exception as err:
                    try:
                        self.update.emit({"type": "shutter_status", "success": False, "value": "Fail to read"})
                        # self.update_event_log.emit(f"Ununable to read YAG shutter status.\n{err}")
                    except RuntimeError:
                        pass

                if not self.parent.running:
                    break

                try:
                    self.update.emit({"type": "flashlamp_status", "success": True, "value": self.yag.laser_status.flashlamp.name})
                except Exception as err:
                    try:
                        self.update.emit({"type": "flashlamp_status", "success": False, "value": "Fail to read"})
                        # self.update_event_log.emit(f"Ununable to read YAG flashlamp status.\n{err}")
                    except RuntimeError:
                        pass

                if not self.parent.running:
                    break

                try:
                    self.update.emit({"type": "simmer_status", "success": True, "value": "ON" if self.yag.laser_status.simmer else "OFF"})
                except Exception as err:
                    try:
                        self.update.emit({"type": "simmer_status", "success": False,  "value": "Fail to read"})
                        # self.update_event_log.emit(f"Ununable to read YAG simmer status.\n{err}")
                    except RuntimeError:
                        pass

                if not self.parent.running:
                    break

                try:
                    self.update.emit({"type": "flashlamp_trigger", "success": True, "value": self.yag.flashlamp.trigger.name})
                except Exception as err:
                    try:
                        self.update.emit({"type": "flashlamp_trigger", "success": False, "value": "Fail to read"})
                        # self.update_event_log.emit(f"Ununable to read YAG flashlamp trigger.\n{err}")
                    except RuntimeError:
                        pass

                if not self.parent.running:
                    break

                try:
                    self.update.emit({"type": "flashlamp_frequency_Hz", "success": True, "value": "{:.2f}".format(self.yag.flashlamp.frequency)})
                except Exception as err:
                    try:
                        self.update.emit({"type": "flashlamp_frequency_Hz", "success": False, "value": "Fail to read"})
                        # self.update_event_log.emit(f"Ununable to read YAG flashlamp frequency.\n{err}")
                    except RuntimeError:
                        pass

                if not self.parent.running:
                    break

                try:
                    self.update.emit({"type": "flashlamp_voltage_V", "success": True, "value": str(self.yag.flashlamp.voltage)})
                except Exception as err:
                    try:
                        self.update.emit({"type": "flashlamp_voltage_V", "success": False, "value": "Fail to read"})
                        # self.update_event_log.emit(f"Ununable to read YAG flashlamp voltage.\n{err}")
                    except RuntimeError:
                        pass

                if not self.parent.running:
                    break

                try:
                    self.update.emit({"type": "flashlamp_energy_J", "success": True, "value": "{:.1f}".format(self.yag.flashlamp.energy)})
                except Exception as err:
                    try:
                        self.update.emit({"type": "flashlamp_energy_J", "success": False, "value": "Fail to read"})
                        # self.update_event_log.emit(f"Ununable to read YAG flashlamp energy.\n{err}")
                    except RuntimeError:
                        pass

                if not self.parent.running:
                    break

                try:
                    self.update.emit({"type": "flashlamp_capacitance_uF", "success": True, "value": "{:.1f}".format(self.yag.flashlamp.capacitance)})
                except Exception as err:
                    try:
                        self.update.emit({"type": "flashlamp_capacitance_uF", "success": False, "value": "Fail to read"})
                        # self.update_event_log.emit(f"Ununable to read YAG flashlamp capacitance.\n{err}")
                    except RuntimeError:
                        pass

                if not self.parent.running:
                    break

                try:
                    self.update.emit({"type": "flashlamp_counter", "success": True, "value": str(self.yag.flashlamp.counter)})
                except Exception as err:
                    try:
                        self.update.emit({"type": "flashlamp_counter", "success": False, "value": "Fail to read"})
                        # self.update_event_log.emit(f"Ununable to read YAG flashlamp counter.\n{err}")
                    except RuntimeError:
                        pass

                if not self.parent.running:
                    break

                try:
                    self.update.emit({"type": "flashlamp_user_counter", "success": True, "value": str(self.yag.flashlamp.counter)})
                except Exception as err:
                    try:
                        self.update.emit({"type": "flashlamp_user_counter", "success": False, "value": "Fail to read"})
                        # self.update_event_log.emit(f"Ununable to read YAG flashlamp user counter.\n{err}")
                    except RuntimeError:
                        pass

                if not self.parent.running:
                    break

                try:
                    self.update.emit({"type": "flashlamp_intlk", "success": True, "value": self.yag.flashlamp.interlock})
                except Exception as err:
                    try:
                        self.update.emit({"type": "flashlamp_intlk", "success": False, "value": "Fail to read"})
                    except RuntimeError:
                        pass

                if not self.parent.running:
                    break

                try:
                    self.update.emit({"type": "qswitch_status", "success": True, "value": "ON" if self.yag.qswitch.status else "OFF"})
                except Exception as err:
                    try:
                        self.update.emit({"type": "qswitch_status", "success": False, "value": "Fail to read"})
                        # self.update_event_log.emit(f"Ununable to read YAG qswitch status.\n{err}")
                    except RuntimeError:
                        pass

                if not self.parent.running:
                    break

                try:
                    self.update.emit({"type": "qswitch_mode", "success": True, "value": self.yag.qswitch.mode.name})
                except Exception as err:
                    try:
                        self.update.emit({"type": "qswitch_mode", "success": False, "value": "Fail to read"})
                        # self.update_event_log.emit(f"Ununable to read YAG qswitch mode.\n{err}")
                    except RuntimeError:
                        pass

                if not self.parent.running:
                    break

                try:
                    self.update.emit({"type": "qswitch_delay_us", "success": True, "value": str(self.yag.qswitch.delay)})
                except Exception as err:
                    try:
                        self.update.emit({"type": "qswitch_delay_us", "success": False, "value": "Fail to read"})
                        # self.update_event_log.emit(f"Ununable to read YAG qswitch delay.\n{err}")
                    except RuntimeError:
                        pass

                if not self.parent.running:
                    break

                try:
                    self.update.emit({"type": "qswitch_freq_divider", "success": True, "value": str(self.yag.qswitch.frequency_divider)})
                except Exception as err:
                    try:
                        self.update.emit({"type": "qswitch_freq_divider", "success": False, "value": "Fail to read"})
                        # self.update_event_log.emit(f"Ununable to read YAG qswitch frequency divider.\n{err}")
                    except RuntimeError:
                        pass

                if not self.parent.running:
                    break

                try:
                    self.update.emit({"type": "qswitch_burst_pulses", "success": True, "value": str(self.yag.qswitch.pulses)})
                except Exception as err:
                    try:
                        self.update.emit({"type": "qswitch_burst_pulses", "success": False, "value": "Fail to read"})
                        # self.update_event_log.emit(f"Ununable to read YAG qswitch burst pulse number.\n{err}")
                    except RuntimeError:
                        pass

                if not self.parent.running:
                    break

                try:
                    self.update.emit({"type": "qswitch_counter", "success": True, "value": str(self.yag.qswitch.counter)})
                except Exception as err:
                    try:
                        self.update.emit({"type": "qswitch_counter", "success": False, "value": "Fail to read"})
                        # self.update_event_log.emit(f"Ununable to read YAG qswitch counter.\n{err}")
                    except RuntimeError:
                        pass

                if not self.parent.running:
                    break

                try:
                    self.update.emit({"type": "qswitch_user_counter", "success": True, "value": str(self.yag.qswitch.user_counter)})
                except Exception as err:
                    try:
                        self.update.emit({"type": "qswitch_user_counter", "success": False, "value": "Fail to read"})
                        # self.update_event_log.emit(f"Ununable to read YAG qswitch user counter.\n{err}")
                    except RuntimeError:
                        pass

                if not self.parent.running:
                    break

                try:
                    self.update.emit({"type": "qswitch_intlk", "success": True, "value":self.yag.qswitch.interlock})
                except Exception as err:
                    try: 
                        self.update.emit({"type": "qswitch_intlk", "success": False, "value": "Fail to read"})
                    except RuntimeError:
                        pass

            time.sleep(0.05)

        try:
            self.yag.instrument.clear()
        except pyvisa.errors.VisaIOError as err:
            pass

        try:
            self.yag.instrument.close()
        except pyvisa.errors.VisaIOError as err:
            pass

        self.finished.emit()


class mainWindow(qt.QMainWindow):
    """GUI main window, including all device boxes."""

    def __init__(self, app):
        super().__init__()
        self.app = app
        self.running = True
        self.event_log_deque = deque(maxlen=10000)
        # logging.getLogger().setLevel("INFO")

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

        self.box.frame.addWidget(self.place_activation_button(), 0, 0)

        self.tab = qt.QTabWidget()
        self.box.frame.addWidget(self.tab, 1, 0)

        ctrl_box = self.place_general_controls()
        self.tab.addTab(ctrl_box, "General")

        ctrl_box = self.place_flashlamp_controls()
        self.tab.addTab(ctrl_box, "Flashlamp")

        ctrl_box = self.place_qswitch_controls()
        self.tab.addTab(ctrl_box, "QSwitch")

        event_log_box = self.place_event_log_controls()
        self.box.frame.addWidget(event_log_box, 2, 0)

        self.show()

        self.update_event_log("This program controls Big Sky/Quantel YAG Laser.")
        self.update_event_log("Starting GUI...")

        self.start_control()

    def place_activation_button(self):
        ctrl_box = widgets.NewBox("grid")
        ctrl_box.setTitle("")
        ctrl_box.setStyleSheet("QGroupBox{border-width: 4px; font-size: 15pt; font-weight: Normal}QPushButton{font: 10pt}QLabel{font: 10pt}QLineEdit{font: 10pt}QCheckBox{font: 10pt}")

        self.activate_yag_pb = qt.QPushButton("\nActivate/Deactivate YAG\n")
        self.activate_yag_pb.setStyleSheet("QPushButton{font: 15pt;}")
        self.activate_yag_pb.setToolTip("Activate: shutter-->Qswitch-->flashlamp\nDeactivate: flashlamp-->Qswitch")
        self.activate_yag_pb.clicked[bool].connect(lambda val, config_type="activate_yag": self.update_config(config_type))
        ctrl_box.frame.addWidget(self.activate_yag_pb, 0, 0)

        return ctrl_box

    def place_general_controls(self):
        """Place general control widgets."""

        ctrl_box = widgets.NewBox("grid")
        ctrl_box.setTitle("")
        ctrl_box.setStyleSheet("QGroupBox{border-width: 4px; padding-top: 18px; font-size: 15pt; font-weight: Normal}QPushButton{font: 10pt}QLabel{font: 10pt}QLineEdit{font: 10pt}QCheckBox{font: 10pt}")

        ctrl_box.frame.addWidget(qt.QLabel("COM port:"), 0, 0, alignment=PyQt5.QtCore.Qt.AlignRight)
        self.com_port_cb = widgets.NewComboBox(item_list=self.get_com_port_list(), current_item=self.config.get("setting", "com_port"))
        self.com_port_cb = widgets.NewComboBox(item_list=[self.config.get("setting", "com_port")], current_item=self.config.get("setting", "com_port"))
        self.com_port_cb.currentTextChanged[str].connect(lambda val, config_type="com_port": self.update_config(config_type, val))
        ctrl_box.frame.addWidget(self.com_port_cb, 0, 1)
        self.reconnect_com_pb = qt.QPushButton("Reconnect COM")
        self.reconnect_com_pb.clicked[bool].connect(lambda val: self.reconnect_com())
        ctrl_box.frame.addWidget(self.reconnect_com_pb, 1, 1)
        self.refresh_com_pb = qt.QPushButton("Refresh COM list")
        self.refresh_com_pb.clicked[bool].connect(lambda val: self.refresh_com())
        ctrl_box.frame.addWidget(self.refresh_com_pb, 1, 2)

        ctrl_box.frame.addWidget(qt.QLabel("loop cycle (s):"), 2, 0, alignment=PyQt5.QtCore.Qt.AlignRight)
        self.loop_cycle_dsb = widgets.NewDoubleSpinBox(range=(0, 600), decimals=1)
        self.loop_cycle_dsb.setValue(self.config.getfloat("setting", "loop_cycle_seconds"))
        # self.loop_cycle_dsb.valueChanged[float].connect(lambda val, config_type="loop_cycle_seconds": self.update_config(config_type, val))
        # self.loop_cycle_dsb.editingFinished.connect(lambda dsb=self.loop_cycle_dsb, config_type="loop_cycle_seconds": self.update_config(config_type, dsb.value()))
        self.loop_cycle_dsb.editingFinished.connect(lambda val="": self.update_config("loop_cycle_seconds", self.loop_cycle_dsb.value()))
        ctrl_box.frame.addWidget(self.loop_cycle_dsb, 2, 1)

        ctrl_box.frame.addWidget(qt.QLabel("Configurations:"), 3, 0, alignment=PyQt5.QtCore.Qt.AlignRight)
        self.save_config_pb = qt.QPushButton("Save config")
        self.save_config_pb.setEnabled(False)
        ctrl_box.frame.addWidget(self.save_config_pb, 3, 1)
        self.load_config_pb = qt.QPushButton("Load config")
        self.load_config_pb.setEnabled(False)
        ctrl_box.frame.addWidget(self.load_config_pb, 3, 2)

        ctrl_box.frame.addWidget(qt.QLabel("Send custom command:"), 4, 0, alignment=PyQt5.QtCore.Qt.AlignRight)
        self.message_le = widgets.NewLineEdit("Enter cmd here...")
        self.message_le.returnPressed.connect(lambda le=self.message_le, config_type="custom_command": self.update_config(config_type, le.text()))
        self.message_le.setCursorPosition(0)
        ctrl_box.frame.addWidget(self.message_le, 4, 1)

        ctrl_box.frame.addWidget(qt.QLabel("--------------------------"), 5, 0, alignment=PyQt5.QtCore.Qt.AlignRight)

        ctrl_box.frame.addWidget(qt.QLabel("Serial number:"), 6, 0, alignment=PyQt5.QtCore.Qt.AlignRight)
        self.serial_number_la = qt.QLabel("N/A")
        ctrl_box.frame.addWidget(self.serial_number_la, 6, 1)

        ctrl_box.frame.addWidget(qt.QLabel("Pump status:"), 7, 0, alignment=PyQt5.QtCore.Qt.AlignRight)
        self.pump_status_la = qt.QLabel("N/A")
        ctrl_box.frame.addWidget(self.pump_status_la, 7, 1)
        self.toggle_pump_pb = qt.QPushButton("Toggle pump status")
        self.toggle_pump_pb.clicked[bool].connect(lambda val, config_type="toggle_pump": self.update_config(config_type))
        ctrl_box.frame.addWidget(self.toggle_pump_pb, 7, 2)

        ctrl_box.frame.addWidget(qt.QLabel("Cooling group temperature (C):"), 8, 0, alignment=PyQt5.QtCore.Qt.AlignRight)
        self.temp_la = qt.QLabel("N/A")
        ctrl_box.frame.addWidget(self.temp_la, 8, 1)

        ctrl_box.frame.addWidget(qt.QLabel("Shutter status:"), 9, 0, alignment=PyQt5.QtCore.Qt.AlignRight)
        self.shutter_status_la = qt.QLabel("N/A")
        ctrl_box.frame.addWidget(self.shutter_status_la, 9, 1)
        self.toggle_shutter_pb = qt.QPushButton("Toggle shutter status")
        self.toggle_shutter_pb.clicked[bool].connect(lambda val, config_type="toggle_shutter": self.update_config(config_type))
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

        ctrl_box.frame.addWidget(qt.QLabel("Flashlamp status:"), 0, 0, alignment=PyQt5.QtCore.Qt.AlignRight)
        self.flashlamp_status_la = qt.QLabel("N/A")
        ctrl_box.frame.addWidget(self.flashlamp_status_la, 0, 1)
        self.toggle_flashlamp_pb = qt.QPushButton("Toggle flashlamp status")
        self.toggle_flashlamp_pb.clicked[bool].connect(lambda val, config_type="toggle_flashlamp": self.update_config(config_type))
        ctrl_box.frame.addWidget(self.toggle_flashlamp_pb, 0, 2)

        ctrl_box.frame.addWidget(qt.QLabel("Flashlamp simmer:"), 1, 0, alignment=PyQt5.QtCore.Qt.AlignRight)
        self.flashlamp_simmer_la = qt.QLabel("N/A")
        ctrl_box.frame.addWidget(self.flashlamp_simmer_la, 1, 1)
        self.turn_on_simmer_pb = qt.QPushButton("Turn on flashlamp simmer")
        self.turn_on_simmer_pb.setToolTip("Turn off flashlamp to turn off simmer.")
        self.turn_on_simmer_pb.clicked[bool].connect(lambda val, config_type="turn_on_simmer": self.update_config(config_type))
        ctrl_box.frame.addWidget(self.turn_on_simmer_pb, 1, 2)

        ctrl_box.frame.addWidget(qt.QLabel("Flashlamp trigger:"), 2, 0, alignment=PyQt5.QtCore.Qt.AlignRight)
        self.flashlamp_trigger_la = qt.QLabel("N/A")
        ctrl_box.frame.addWidget(self.flashlamp_trigger_la, 2, 1)
        self.flashlamp_trigger_cb = widgets.NewComboBox(item_list=["internal", "external"], current_item=self.config.get("setting", "flashlamp_trigger"))
        self.flashlamp_trigger_cb.currentTextChanged[str].connect(lambda val, config_type="flashlamp_trigger": self.update_config(config_type, val))
        self.flashlamp_trigger_cb.setToolTip("Choose trigger mode here.")
        ctrl_box.frame.addWidget(self.flashlamp_trigger_cb, 2, 2)

        ctrl_box.frame.addWidget(qt.QLabel("Flashlamp frequency (Hz):"), 3, 0, alignment=PyQt5.QtCore.Qt.AlignRight)
        self.flashlamp_frequency_la = qt.QLabel("N/A")
        ctrl_box.frame.addWidget(self.flashlamp_frequency_la, 3, 1)
        self.flashlamp_frequency_dsb = widgets.NewDoubleSpinBox(range=(1, 99.99), decimals=2)
        self.flashlamp_frequency_dsb.setValue(self.config.getfloat("setting", "flashlamp_frequency_Hz"))
        # self.flashlamp_frequency_dsb.valueChanged[float].connect(lambda val, config_type="flashlamp_frequency_Hz": self.update_config(config_type, val))
        self.flashlamp_frequency_dsb.editingFinished.connect(lambda dsb=self.flashlamp_frequency_dsb, config_type="flashlamp_frequency_Hz": self.update_config(config_type, dsb.value()))
        self.flashlamp_frequency_dsb.setToolTip("Change flashlamp frequency here.")
        ctrl_box.frame.addWidget(self.flashlamp_frequency_dsb, 3, 2)

        ctrl_box.frame.addWidget(qt.QLabel("Flashlamp voltage (V):"), 4, 0, alignment=PyQt5.QtCore.Qt.AlignRight)
        self.flashlamp_voltage_la = qt.QLabel("N/A")
        ctrl_box.frame.addWidget(self.flashlamp_voltage_la, 4, 1)
        self.flashlamp_voltage_sb = widgets.NewSpinBox(range=(500, 1800))
        self.flashlamp_voltage_sb.setValue(self.config.getint("setting", "flashlamp_voltage_V"))
        # self.flashlamp_voltage_sb.valueChanged[int].connect(lambda val, config_type="flashlamp_voltage_V": self.update_config(config_type, val))
        self.flashlamp_voltage_sb.editingFinished.connect(lambda sb=self.flashlamp_voltage_sb, config_type="flashlamp_voltage_V": self.update_config(config_type, sb.value()))
        self.flashlamp_voltage_sb.setToolTip("Change flashlamp voltage here.")
        ctrl_box.frame.addWidget(self.flashlamp_voltage_sb, 4, 2)

        ctrl_box.frame.addWidget(qt.QLabel("Flashlamp energy (J):"), 5, 0, alignment=PyQt5.QtCore.Qt.AlignRight)
        self.flashlamp_energy_la = qt.QLabel("N/A")
        ctrl_box.frame.addWidget(self.flashlamp_energy_la, 5, 1)
        self.flashlamp_energy_dsb = widgets.NewDoubleSpinBox(range=(7, 23), decimals=1)
        self.flashlamp_energy_dsb.setValue(self.config.getfloat("setting", "flashlamp_energy_J"))
        # self.flashlamp_energy_dsb.valueChanged[float].connect(lambda val, config_type="flashlamp_energy_J": self.update_config(config_type, val))
        self.flashlamp_energy_dsb.editingFinished.connect(lambda dsb=self.flashlamp_energy_dsb, config_type="flashlamp_energy_J": self.update_config(config_type, dsb.value()))
        self.flashlamp_energy_dsb.setToolTip("Change flashlamp energy here.")
        ctrl_box.frame.addWidget(self.flashlamp_energy_dsb, 5, 2)

        ctrl_box.frame.addWidget(qt.QLabel("Flashlamp capacitance (uF):"), 6, 0, alignment=PyQt5.QtCore.Qt.AlignRight)
        self.flashlamp_capacitance_la = qt.QLabel("N/A")
        ctrl_box.frame.addWidget(self.flashlamp_capacitance_la, 6, 1)
        self.flashlamp_capacitance_dsb = widgets.NewDoubleSpinBox(range=(27, 33), decimals=1)
        self.flashlamp_capacitance_dsb.setValue(self.config.getfloat("setting", "flashlamp_capacitance_uF"))
        # self.flashlamp_capacitance_dsb.valueChanged[float].connect(lambda val, config_type="flashlamp_capacitance_uF": self.update_config(config_type, val))
        self.flashlamp_capacitance_dsb.editingFinished.connect(lambda dsb=self.flashlamp_capacitance_dsb, config_type="flashlamp_capacitance_uF": self.update_config(config_type, dsb.value()))
        self.flashlamp_capacitance_dsb.setToolTip("Change flashlamp capacitance here.")
        ctrl_box.frame.addWidget(self.flashlamp_capacitance_dsb, 6, 2)

        ctrl_box.frame.addWidget(qt.QLabel("Flashlamp counter:"), 7, 0, alignment=PyQt5.QtCore.Qt.AlignRight)
        self.flashlamp_counter_la = qt.QLabel("N/A")
        ctrl_box.frame.addWidget(self.flashlamp_counter_la, 7, 1)

        ctrl_box.frame.addWidget(qt.QLabel("Flashlamp user counter:"), 8, 0, alignment=PyQt5.QtCore.Qt.AlignRight)
        self.flashlamp_user_counter_la = qt.QLabel("N/A")
        ctrl_box.frame.addWidget(self.flashlamp_user_counter_la, 8, 1)
        self.flashlamp_user_counter_pb = qt.QPushButton("Reset user counter")
        self.flashlamp_user_counter_pb.clicked[bool].connect(lambda val, config_type="reset_flashlamp_user_counter": self.update_config(config_type))
        ctrl_box.frame.addWidget(self.flashlamp_user_counter_pb, 8, 2)

        ctrl_box.frame.addWidget(qt.QLabel("-"*30+"  interloack  "+"-"*30), 9, 0, 1, 3, alignment=PyQt5.QtCore.Qt.AlignCenter)

        self.flashlamp_intlk_water_flow_la = qt.QLabel("N/A")
        ctrl_box.frame.addWidget(self.flashlamp_intlk_water_flow_la, 10, 0, alignment=PyQt5.QtCore.Qt.AlignCenter)
        self.flashlamp_intlk_water_level_la = qt.QLabel("N/A")
        ctrl_box.frame.addWidget(self.flashlamp_intlk_water_level_la, 10, 1, alignment=PyQt5.QtCore.Qt.AlignCenter)
        self.flashlamp_intlk_lamp_head_la = qt.QLabel("N/A")
        ctrl_box.frame.addWidget(self.flashlamp_intlk_lamp_head_la, 10, 2, alignment=PyQt5.QtCore.Qt.AlignCenter)

        self.flashlamp_intlk_auxiliary_la = qt.QLabel("N/A")
        ctrl_box.frame.addWidget(self.flashlamp_intlk_auxiliary_la, 11, 0, alignment=PyQt5.QtCore.Qt.AlignCenter)
        self.flashlamp_intlk_external_la = qt.QLabel("N/A")
        ctrl_box.frame.addWidget(self.flashlamp_intlk_external_la, 11, 1, alignment=PyQt5.QtCore.Qt.AlignCenter)
        self.flashlamp_intlk_cover_la = qt.QLabel("N/A")
        ctrl_box.frame.addWidget(self.flashlamp_intlk_cover_la, 11, 2, alignment=PyQt5.QtCore.Qt.AlignCenter)

        self.flashlamp_intlk_capacitor_la = qt.QLabel("N/A")
        ctrl_box.frame.addWidget(self.flashlamp_intlk_capacitor_la, 12, 0, alignment=PyQt5.QtCore.Qt.AlignCenter)
        self.flashlamp_intlk_simmer_la = qt.QLabel("N/A")
        ctrl_box.frame.addWidget(self.flashlamp_intlk_simmer_la, 12, 1, alignment=PyQt5.QtCore.Qt.AlignCenter)
        self.flashlamp_intlk_water_temp_la = qt.QLabel("N/A")
        ctrl_box.frame.addWidget(self.flashlamp_intlk_water_temp_la, 12, 2, alignment=PyQt5.QtCore.Qt.AlignCenter)
 
        # let column 100 grow if there are extra space (row index start from 0, default stretch is 0)
        ctrl_box.frame.setRowStretch(100, 1)

        ctrl_box.frame.setColumnStretch(1, 1)
        ctrl_box.frame.setColumnStretch(2, 1)

        return ctrl_box

    def place_qswitch_controls(self):
        ctrl_box = widgets.NewBox("grid")
        ctrl_box.setTitle("")
        ctrl_box.setStyleSheet("QGroupBox{border-width: 4px; padding-top: 18px; font-size: 15pt; font-weight: Normal}QPushButton{font: 10pt}QLabel{font: 10pt}QLineEdit{font: 10pt}QCheckBox{font: 10pt}")

        ctrl_box.frame.addWidget(qt.QLabel("QSwitch status:"), 0, 0, alignment=PyQt5.QtCore.Qt.AlignRight)
        self.qswitch_status_la = qt.QLabel("N/A")
        ctrl_box.frame.addWidget(self.qswitch_status_la, 0, 1)
        self.toggle_qswitch_pb = qt.QPushButton("Toggle qswitch status")
        self.toggle_qswitch_pb.clicked[bool].connect(lambda val, config_type="toggle_qswitch": self.update_config(config_type))
        ctrl_box.frame.addWidget(self.toggle_qswitch_pb, 0, 2)

        ctrl_box.frame.addWidget(qt.QLabel("QSwitch mode:"), 1, 0, alignment=PyQt5.QtCore.Qt.AlignRight)
        self.qswitch_mode_la = qt.QLabel("N/A")
        ctrl_box.frame.addWidget(self.qswitch_mode_la, 1, 1)
        self.qswitch_mode_cb = widgets.NewComboBox(item_list=["auto", "burst", "external"], current_item=self.config.get("setting", "qswitch_mode"))
        self.qswitch_mode_cb.currentTextChanged[str].connect(lambda val, config_type="qswitch_mode": self.update_config(config_type, val))
        self.qswitch_mode_cb.setToolTip("Choose trigger mode here.")
        ctrl_box.frame.addWidget(self.qswitch_mode_cb, 1, 2)

        ctrl_box.frame.addWidget(qt.QLabel("QSwitch delay (us):"), 2, 0, alignment=PyQt5.QtCore.Qt.AlignRight)
        self.qswitch_delay_la = qt.QLabel("N/A")
        ctrl_box.frame.addWidget(self.qswitch_delay_la, 2, 1)
        self.qswitch_delay_sb = widgets.NewSpinBox(range=(10, 999))
        self.qswitch_delay_sb.setValue(self.config.getint("setting", "qswitch_delay_us"))
        # self.qswitch_delay_sb.valueChanged[int].connect(lambda val, config_type="qswitch_delay_us": self.update_config(config_type, val))
        self.qswitch_delay_sb.editingFinished.connect(lambda sb=self.qswitch_delay_sb, config_type="qswitch_delay_us": self.update_config(config_type, sb.value()))
        self.qswitch_delay_sb.setToolTip("Change QSwitch delay here.")
        ctrl_box.frame.addWidget(self.qswitch_delay_sb, 2, 2)

        ctrl_box.frame.addWidget(qt.QLabel("QSwitch freq divider:"), 3, 0, alignment=PyQt5.QtCore.Qt.AlignRight)
        self.qswitch_freq_divider_la = qt.QLabel("N/A")
        ctrl_box.frame.addWidget(self.qswitch_freq_divider_la, 3, 1)
        self.qswitch_freq_divider_sb = widgets.NewSpinBox(range=(1, 99))
        self.qswitch_freq_divider_sb.setValue(self.config.getint("setting", "qswitch_freq_divider"))
        # self.qswitch_freq_divider_sb.valueChanged[int].connect(lambda val, config_type="qswitch_freq_divider": self.update_config(config_type, val))
        self.qswitch_freq_divider_sb.editingFinished.connect(lambda sb=self.qswitch_freq_divider_sb, config_type="qswitch_freq_divider": self.update_config(config_type, sb.value()))
        self.qswitch_freq_divider_sb.setToolTip("Change QSwitch frequency divider here.")
        ctrl_box.frame.addWidget(self.qswitch_freq_divider_sb, 3, 2)

        ctrl_box.frame.addWidget(qt.QLabel("QSwitch burst pulses:"), 4, 0, alignment=PyQt5.QtCore.Qt.AlignRight)
        self.qswitch_burst_pulses_la = qt.QLabel("N/A")
        ctrl_box.frame.addWidget(self.qswitch_burst_pulses_la, 4, 1)
        self.qswitch_burst_pulses_sb = widgets.NewSpinBox(range=(1, 999))
        self.qswitch_burst_pulses_sb.setValue(self.config.getint("setting", "qswitch_burst_pulses"))
        # self.qswitch_burst_pulses_sb.valueChanged[int].connect(lambda val, config_type="qswitch_vurst_pulses": self.update_config(config_type, val))
        self.qswitch_burst_pulses_sb.editingFinished.connect(lambda sb=self.qswitch_burst_pulses_sb, config_type="qswitch_vurst_pulses": self.update_config(config_type, sb.value()))
        self.qswitch_burst_pulses_sb.setToolTip("Change QSwitch burst pulse number here.")
        ctrl_box.frame.addWidget(self.qswitch_burst_pulses_sb, 4, 2)

        ctrl_box.frame.addWidget(qt.QLabel("QSwitch counter:"), 5, 0, alignment=PyQt5.QtCore.Qt.AlignRight)
        self.qswitch_counter_la = qt.QLabel("N/A")
        ctrl_box.frame.addWidget(self.qswitch_counter_la, 5, 1)

        ctrl_box.frame.addWidget(qt.QLabel("QSwitch user counter:"), 6, 0, alignment=PyQt5.QtCore.Qt.AlignRight)
        self.qswitch_user_counter_la = qt.QLabel("N/A")
        ctrl_box.frame.addWidget(self.qswitch_user_counter_la, 6, 1)
        self.qswitch_user_counter_pb = qt.QPushButton("Reset user counter")
        self.qswitch_user_counter_pb.clicked[bool].connect(lambda val, config_type="reset_qswitch_user_counter": self.update_config(config_type))
        ctrl_box.frame.addWidget(self.qswitch_user_counter_pb, 6, 2)

        ctrl_box.frame.addWidget(qt.QLabel("-"*30+"  interloack  "+"-"*30), 7, 0, 1, 3, alignment=PyQt5.QtCore.Qt.AlignCenter)

        self.qswitch_intlk_emission_la = qt.QLabel("N/A")
        ctrl_box.frame.addWidget(self.qswitch_intlk_emission_la, 8, 0, alignment=PyQt5.QtCore.Qt.AlignCenter)
        self.qswitch_intlk_water_temp_la = qt.QLabel("N/A")
        ctrl_box.frame.addWidget(self.qswitch_intlk_water_temp_la, 8, 1, alignment=PyQt5.QtCore.Qt.AlignCenter)
        self.qswitch_intlk_shutter_la = qt.QLabel("N/A")
        ctrl_box.frame.addWidget(self.qswitch_intlk_shutter_la, 8, 2, alignment=PyQt5.QtCore.Qt.AlignCenter)

        # let column 100 grow if there are extra space (row index start from 0, default stretch is 0)
        ctrl_box.frame.setRowStretch(100, 1)

        ctrl_box.frame.setColumnStretch(1, 1)
        ctrl_box.frame.setColumnStretch(2, 1)

        return ctrl_box

    def place_event_log_controls(self):
        """Place event log widgets."""

        event_log_box = widgets.NewBox("grid")
        event_log_box.setTitle("Event Log")
        event_log_box.setStyleSheet("QGroupBox{border-width: 4px; padding-top: 18px; font-size: 11pt; font-weight: Normal}QPushButton{font: 10pt}QLabel{font: 10pt}QLineEdit{font: 10pt}QCheckBox{font: 10pt}")

        self.clear_log_pb = qt.QPushButton('Clear event log')
        event_log_box.frame.addWidget(self.clear_log_pb, 0, 0)

        self.event_log_tb = qt.QTextBrowser()
        self.clear_log_pb.clicked[bool].connect(lambda val: self.clear_event_log())
        event_log_box.frame.addWidget(self.event_log_tb, 1, 0)

        return event_log_box

    def update_event_log(self, msg=None):
        if msg is not None:
            msg = f"{time.strftime('%Y/%m/%d %H:%M:%S')}: {msg}"
            self.event_log_deque.append(msg)
            filename = "logging/log_" + time.strftime("%b%Y") + ".txt"
            with open(filename, "a") as f:
                f.write("\n"+msg)

            
        self.event_log_tb.setText("\n".join(self.event_log_deque))
        self.event_log_tb.moveCursor(PyQt5.QtGui.QTextCursor.End)

    def clear_event_log(self):
        self.event_log_tb.clear()
        self.event_log_deque.clear()

    # for a really nice tutorial for QThread(), see https://realpython.com/python-pyqt-qthread/
    def start_control(self):
        """Start a worker thread. Be called when the class instantiates."""

        self.thread = PyQt5.QtCore.QThread()

        self.worker = Worker(self)
        self.worker.moveToThread(self.thread)

        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.thread.wait)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.worker.update[dict].connect(self.update_labels)
        self.worker.update_event_log[str].connect(self.update_event_log)

        self.thread.start()

    def update_config(self, config_type, val=None):
        # print((config_type, val))

        if config_type in self.config["setting"].keys():
            self.config["setting"][config_type] = str(val)

        if config_type == "com_port":
            self.reconnect_com()
        elif config_type == "loop_cycle_seconds":
            return
        else:
            self.worker.cmd_queue.put((config_type, val))

    # @PyQt5.QtCore.pyqtSlot(dict)
    def update_labels(self, info_dict):
        if info_dict["type"] == "serial_number":
            self.serial_number_la.setText(info_dict["value"])
            self.serial_number_la.setStyleSheet("QLabel{background: transparent}" if info_dict["success"] else "QLabel{background: red}")

        elif info_dict["type"] == "temperature_C":
            self.temp_la.setText(info_dict["value"])
            self.temp_la.setStyleSheet("QLabel{background: transparent}" if info_dict["success"] else "QLabel{background: red}")

        elif info_dict["type"] == "pump_status":
            self.pump_status_la.setText(info_dict["value"])
            if info_dict["success"]:
                self.pump_status_la.setStyleSheet("QLabel{background: green}" if info_dict["value"] == "ON" else "QLabel{background: transparent}")
            else:
                self.pump_status_la.setStyleSheet("QLabel{background: red}")

        elif info_dict["type"] == "shutter_status":
            self.shutter_status_la.setText(info_dict["value"])
            if info_dict["success"]:
                self.shutter_status_la.setStyleSheet("QLabel{background: green}" if info_dict["value"] == "OPEN" else "QLabel{background: transparent}")
            else:
                self.shutter_status_la.setStyleSheet("QLabel{background: red}")

        elif info_dict["type"] == "flashlamp_status":
            self.flashlamp_status_la.setText(info_dict["value"])
            if info_dict["success"]:
                self.flashlamp_status_la.setStyleSheet("QLabel{background: green}" if info_dict["value"] in ["START", "SINGLE"] else "QLabel{background: Transparent}")
            else:
                self.flashlamp_status_la.setStyleSheet("QLabel{background: red}")

        elif info_dict["type"] == "simmer_status":
            self.flashlamp_simmer_la.setText(info_dict["value"])
            if info_dict["success"]:
                self.flashlamp_simmer_la.setStyleSheet("QLabel{background: green}" if info_dict["value"] == "ON" else "QLabel{background: transparent}")
            else:
                self.flashlamp_simmer_la.setStyleSheet("QLabel{background: red}")

        elif info_dict["type"] == "flashlamp_trigger":
            self.flashlamp_trigger_la.setText(info_dict["value"])
            self.flashlamp_trigger_la.setStyleSheet("QLabel{background: transparent}" if info_dict["success"] else "QLabel{background: red}")

        elif info_dict["type"] == "flashlamp_frequency_Hz":
            self.flashlamp_frequency_la.setText(info_dict["value"])
            self.flashlamp_frequency_la.setStyleSheet("QLabel{background: transparent}" if info_dict["success"] else "QLabel{background: red}")

        elif info_dict["type"] == "flashlamp_voltage_V":
            self.flashlamp_voltage_la.setText(info_dict["value"])
            self.flashlamp_voltage_la.setStyleSheet("QLabel{background: transparent}" if info_dict["success"] else "QLabel{background: red}")

        elif info_dict["type"] == "flashlamp_energy_J":
            self.flashlamp_energy_la.setText(info_dict["value"])
            self.flashlamp_energy_la.setStyleSheet("QLabel{background: transparent}" if info_dict["success"] else "QLabel{background: red}")

        elif info_dict["type"] == "flashlamp_capacitance_uF":
            self.flashlamp_capacitance_la.setText(info_dict["value"])
            self.flashlamp_capacitance_la.setStyleSheet("QLabel{background: transparent}" if info_dict["success"] else "QLabel{background: red}")

        elif info_dict["type"] == "flashlamp_counter":
            self.flashlamp_counter_la.setText(info_dict["value"])
            self.flashlamp_counter_la.setStyleSheet("QLabel{background: transparent}" if info_dict["success"] else "QLabel{background: red}")

        elif info_dict["type"] == "flashlamp_user_counter":
            self.flashlamp_user_counter_la.setText(info_dict["value"])
            self.flashlamp_user_counter_la.setStyleSheet("QLabel{background: transparent}" if info_dict["success"] else "QLabel{background: red}")

        elif info_dict["type"] == "flashlamp_intlk":
            if info_dict["success"]:
                self.flashlamp_intlk_water_flow_la.setText("Water flow: Failed" if info_dict["value"].WATER_FLOW else "Water flow: Pass")
                self.flashlamp_intlk_water_flow_la.setStyleSheet("QLabel{background: red}" if info_dict["value"].WATER_FLOW else "QLabel{background: transparent}")
                self.flashlamp_intlk_water_level_la.setText("Water level: Failed" if info_dict["value"].WATER_LEVEL else "Water level: Pass")
                self.flashlamp_intlk_water_level_la.setStyleSheet("QLabel{background: red}" if info_dict["value"].WATER_LEVEL else "QLabel{background: transparent}")
                self.flashlamp_intlk_lamp_head_la.setText("Lamp head conn: Failed" if info_dict["value"].LAMP_HEAD_CONN else "Lamp head conn: Pass")
                self.flashlamp_intlk_lamp_head_la.setStyleSheet("QLabel{background: red}" if info_dict["value"].LAMP_HEAD_CONN else "QLabel{background: transparent}")
                self.flashlamp_intlk_auxiliary_la.setText("Auxiliary conn: Failed" if info_dict["value"].AUXILIARY_CONN else "Auxiliary conn: Pass")
                self.flashlamp_intlk_auxiliary_la.setStyleSheet("QLabel{background: red}" if info_dict["value"].AUXILIARY_CONN else "QLabel{background: transparent}")
                self.flashlamp_intlk_external_la.setText("External intlk: Failed" if info_dict["value"].EXT_INTERLOCK else "External intlk: Pass")
                self.flashlamp_intlk_external_la.setStyleSheet("QLabel{background: red}" if info_dict["value"].EXT_INTERLOCK else "QLabel{background: transparent}")
                self.flashlamp_intlk_cover_la.setText("Cover status: Failed" if info_dict["value"].COVER_OPEN else "Cover status: Pass")
                self.flashlamp_intlk_cover_la.setStyleSheet("QLabel{background: red}" if info_dict["value"].COVER_OPEN else "QLabel{background: transparent}")
                self.flashlamp_intlk_capacitor_la.setText("Capacitor status: Failed" if info_dict["value"].CAPACITOR_LOAD_FAIL else "Capacitor status: Pass")
                self.flashlamp_intlk_capacitor_la.setStyleSheet("QLabel{background: red}" if info_dict["value"].CAPACITOR_LOAD_FAIL else "QLabel{background: transparent}")
                self.flashlamp_intlk_simmer_la.setText("Simmer status: Failed" if info_dict["value"].SIMMER_FAIL else "Simmer status: Pass")
                self.flashlamp_intlk_simmer_la.setStyleSheet("QLabel{background: red}" if info_dict["value"].SIMMER_FAIL else "QLabel{background: transparent}")
                self.flashlamp_intlk_water_temp_la.setText("Water temp: Failed" if info_dict["value"].WATER_TEMP else "Water temp: Pass")
                self.flashlamp_intlk_water_temp_la.setStyleSheet("QLabel{background: red}" if info_dict["value"].WATER_TEMP else "QLabel{background: transparent}")
            else:
                self.flashlamp_intlk_water_flow_la.setText(info_dict["value"])
                self.flashlamp_intlk_water_flow_la.setStyleSheet("QLabel{background: red}")
                self.flashlamp_intlk_water_level_la.setText(info_dict["value"])
                self.flashlamp_intlk_water_level_la.setStyleSheet("QLabel{background: red}")
                self.flashlamp_intlk_lamp_head_la.setText(info_dict["value"])
                self.flashlamp_intlk_lamp_head_la.setStyleSheet("QLabel{background: red}")
                self.flashlamp_intlk_auxiliary_la.setText(info_dict["value"])
                self.flashlamp_intlk_auxiliary_la.setStyleSheet("QLabel{background: red}")
                self.flashlamp_intlk_external_la.setText(info_dict["value"])
                self.flashlamp_intlk_external_la.setStyleSheet("QLabel{background: red}")
                self.flashlamp_intlk_cover_la.setText(info_dict["value"])
                self.flashlamp_intlk_cover_la.setStyleSheet("QLabel{background: red}")
                self.flashlamp_intlk_capacitor_la.setText(info_dict["value"])
                self.flashlamp_intlk_capacitor_la.setStyleSheet("QLabel{background: red}")
                self.flashlamp_intlk_simmer_la.setText(info_dict["value"])
                self.flashlamp_intlk_simmer_la.setStyleSheet("QLabel{background: red}")
                self.flashlamp_intlk_water_temp_la.setText(info_dict["value"])
                self.flashlamp_intlk_water_temp_la.setStyleSheet("QLabel{background: red}")
        
        elif info_dict["type"] == "qswitch_status":
            self.qswitch_status_la.setText(info_dict["value"])
            if info_dict["success"]:
                self.qswitch_status_la.setStyleSheet("QLabel{background: green}" if info_dict["value"] == "ON" else "QLabel{background: transparent}")
            else:
                self.qswitch_status_la.setStyleSheet("QLabel{background: red}")

        elif info_dict["type"] == "qswitch_mode":
            self.qswitch_mode_la.setText(info_dict["value"])
            self.qswitch_mode_la.setStyleSheet("QLabel{background: transparent}" if info_dict["success"] else "QLabel{background: red}")

        elif info_dict["type"] == "qswitch_delay_us":
            self.qswitch_delay_la.setText(info_dict["value"])
            self.qswitch_delay_la.setStyleSheet("QLabel{background: transparent}" if info_dict["success"] else "QLabel{background: red}")

        elif info_dict["type"] == "qswitch_freq_divider":
            self.qswitch_freq_divider_la.setText(info_dict["value"])
            self.qswitch_freq_divider_la.setStyleSheet("QLabel{background: transparent}" if info_dict["success"] else "QLabel{background: red}")

        elif info_dict["type"] == "qswitch_burst_pulses":
            self.qswitch_burst_pulses_la.setText(info_dict["value"])
            self.qswitch_burst_pulses_la.setStyleSheet("QLabel{background: transparent}" if info_dict["success"] else "QLabel{background: red}")

        elif info_dict["type"] == "qswitch_counter":
            self.qswitch_counter_la.setText(info_dict["value"])
            self.qswitch_counter_la.setStyleSheet("QLabel{background: transparent}" if info_dict["success"] else "QLabel{background: red}")

        elif info_dict["type"] == "qswitch_user_counter":
            self.qswitch_user_counter_la.setText(info_dict["value"])
            self.qswitch_user_counter_la.setStyleSheet("QLabel{background: transparent}" if info_dict["success"] else "QLabel{background: red}")

        elif info_dict["type"] == "qswitch_intlk":
            if info_dict["success"]:
                self.qswitch_intlk_emission_la.setText("Emission allowed: Failed" if info_dict["value"].EMISSION_INHIBITED else "Emission allowed: Pass")
                self.qswitch_intlk_emission_la.setStyleSheet("QLabel{background: red}" if info_dict["value"].EMISSION_INHIBITED else "QLabel{background: transparent}")
                self.qswitch_intlk_water_temp_la.setText("Water temp: Failed" if info_dict["value"].WATER_TEMP else "Water temp: Pass")
                self.qswitch_intlk_water_temp_la.setStyleSheet("QLabel{background: red}" if info_dict["value"].WATER_TEMP else "QLabel{background: transparent}")
                self.qswitch_intlk_shutter_la.setText("Shutter status: Failed" if info_dict["value"].SHUTTER_CLOSED else "Shutter status: Pass")
                self.qswitch_intlk_shutter_la.setStyleSheet("QLabel{background: red}" if info_dict["value"].SHUTTER_CLOSED else "QLabel{background: transparent}")
            else:
                self.qswitch_intlk_emission_la.setText(info_dict["value"])
                self.qswitch_intlk_emission_la.setStyleSheet("QLabel{background: red}")
                self.qswitch_intlk_water_temp_la.setText(info_dict["value"])
                self.qswitch_intlk_water_temp_la.setStyleSheet("QLabel{background: red}")
                self.qswitch_intlk_shutter_la.setText(info_dict["value"])
                self.qswitch_intlk_shutter_la.setStyleSheet("QLabel{background: red}")

        else:
            self.update_event_log(f"Unrecognized command: {info_dict['type']}, {info_dict['success']}, {info_dict['value']}")


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
            self.config["setting"]["com_port"] = com_new
            self.reconnect_com()

    def reconnect_com(self):
        self.update_event_log(f"Reconnecting to {self.config['setting']['com_port']}...")

        self.running = False
        try:
            self.thread.quit()
            self.thread.wait()
        except RuntimeError as err:
            pass
        time.sleep(0.05)

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

        self.update_event_log("Program shut down...")

        super().closeEvent(event)


if __name__ == '__main__':
    app = qt.QApplication(sys.argv)
    # screen = app.screens()
    # monitor_dpi = screen[0].physicalDotsPerInch()
    monitor_dpi = 72
    # palette = {"dark":qdarkstyle.dark.palette.DarkPalette, "light":qdarkstyle.light.palette.LightPalette}
    # app.setStyleSheet(qdarkstyle._load_stylesheet(qt_api='pyqt5', palette=palette["light"]))
    prog = mainWindow(app)
    
    try:
        sys.exit(app.exec())
    except SystemExit:
        print("\nApp is closing...")