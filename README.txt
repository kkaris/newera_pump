The pump control programs are entirely based on pumping programs from the Abate Lab at UC San Francisco:
https://github.com/AbateLab/Pump-Control-Program

The original code is written in python 2, and it has been translated, partially by using the script 2to3.py


###
Summary of included Python programs:

new_era_vp.py - contains basic functions that communicate with the pump(s)
pump_control.py - Basic GUI for running pumps at different rates
pump_control_auto_image.py - Program for pumping a set volume per new image detected
pump_control_auto_extrude.py - (Still under construction) program that runs a given number of extrusion cycles: infusing and withdrawing a set sample volume through syringes.


###
Homepage, manuals, technical specifications etc:
www.syringepump.com/
www.syringepump.com/download/index.html
www.syringepump.com/download/NE-1010Brochure.pdf
www.syringepump.com/download/NE-1010-510-511%20Rates%20and%20Specifications.pdf
www.syringepump.com/download/NE-1000%20Syringe%20Pump%20User%20Manual.pdf


###
Detailed Description of new_era_vp.py:

Contains the functions that communicate with the pump. The functions are accessed by other programs through "import new_era_vp as new_era" ("as new_era" to work with the inherited code).

For future reference:
As a rule of thumb, the functions in "new_era_vp.py" should be kept as simple as possible and would typically only send a single command to the pump or some trivial combination of commands. This makes it easier track where potential problems arise. Any non-trivial combinations of functions and/or commands should either be placed in the file of the program that uses them or in a separate file.

Some of the functions included:
 - "run_all": for sending a 'RUN' command to all pumps (network command burst).
 - "stop_all": for sending a 'STP' command to all pumps (network command burst).
 - "run_pump": for sending a 'RUN' command to a specific pump.
 - "stop_pump": for sending a 'STP' command to a specific pump.
 - "error_handler": Checks response packets to see if they contain any error (see manual page 36/pdf page 41).
 - "prime": Infuses the pump at 10 ml/h
 - "get_dispensed": returns the volume that has been dispensed or withdrawn (or both).
 
 
###
Detailed Description of pump_control.py:

The program gives the user a simple graphical user interface (GUI) to control one or a set of pumps simulataneously.

The user can control the following:
 - Syringe model:   A pull-down menu will let the user pick a syringe model.
 - Pump rate:       A textbox lets the user enter a rate.
 - Label:           A textbox lets the user enter what is in the syringe (this textbox does not affect the functionality of the program).
 
Other interface items:
Pump number: If multiple pumps are connected in a network, this will show the number of the pump currently under control.
Current flow rate: This shows what flow rate last sent to the pump.


###
Detailed Description of pump_control_auto_image.py

This program is intended to be used together with microscope image acquisition.
It detects if a new image file has been added to a selected folder and then pumps a set volume once an image has been added. If the total volume pumped reaches either the maximum of the syringe or the set sample volume, the program will automatically reverse the pumping direction.

NOTES:
The program runs the pump for 0.5 seconds, assuming that the fastest anyone would like to take an image is about once every second.

The user controls the following:
 - Image folder:            Sets the directory to detect new images in.
 - Syringe model:           A pull-down menu will let the user pick a syringe model.
 - Sample volume:           The total volume of the sample. Cannot be larger than the maximum volume of the syringe.
 - Pump volume per iamge:   The volume to pump for each image taken.

Other interface items:

Current volume: Shows what volume was last used in deciding the currently used pump rate.
Volume inf:     Shows the total volume infused. This will show how much of the sample that has been pumped out from the syringe. Once this is equal to the sample volume or the maximum syringe volume, the pump automatically reverses direction and starts to withdraw the sample again and the volume infused will start to decrease.
Pump count:     Shows a count of the number of times the pump has pumped (this number will keep increasing even when the pump switches direction).







