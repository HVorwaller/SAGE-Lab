#Author: Hayden Vorwaller
#MFC Controll App
#This application generates a GUI that allows the user to control up to 4 Sensirion SFC5XXX Mass Flow Controllers via RS-485 communication
#The GUI offers two modes of Operation, manual mode, and excel mode. In Excel mode, preplanned step times and concentration can be set to run without
#the need for user supervision. Manual mode can only set one step at a time but does not need preplanned.

from gui import run_gui

run_gui()
