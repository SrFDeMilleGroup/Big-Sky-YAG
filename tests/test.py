from big_sky_yag import BigSkyYag

resource_name = "ASRL7::INSTR"

# yag = BigSkyYag(resource_name = "COM7", serial_number=184)
yag = BigSkyYag(resource_name = "COM7")

# print the status of the laser
# print(yag.laser_status)
print(yag.temperature_cooling_group)

# # set the flashlamp frequency
# yag.flashlamp.frequency = 10 # Hz

# # set the flashlamp voltage
# yag.flashlamp.voltage = 900 # V

# # set the q-switch delay
# yag.qswitch.delay = 150 # ns

# # start the water pump
# yag.pump = True

# # open the shutter, activate the flashlamp and enable the q-switch
# yag.shutter = True
# yag.flashlamp.activate()
# yag.qswitch.start()

# # stop the yag from firing
# yag.qswitch.stop()
# yag.flashlamp.stop()