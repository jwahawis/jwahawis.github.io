""" blinds.py -

    This is a mashup of the minimal fauxmo example and Adafruit DualStepperMotor
    example.
"""

import fauxmo
import logging
import sys
import time
import threading
import atexit

from debounce_handler import debounce_handler
from Adafruit_MotorHAT import Adafruit_MotorHAT, Adafruit_DCMotor, Adafruit_StepperMotor

logging.basicConfig(level=logging.DEBUG)

class stepper():
    def __init__(self):

        # create a default object, no changes to I2C address or frequency
        self.mh = Adafruit_MotorHAT()

        atexit.register(self.turnOffMotors)

        # 200 steps/rev, motor port #1
        self.r_blind = self.mh.getStepper(200, 1)
        self.r_thread = threading.Thread()

        self.l_blind = self.mh.getStepper(200, 2)
        self.l_thread = threading.Thread()

        # TODO: make this thread safe...
        self.blinds_are_open = False

    def stepper_worker(self, stepper, numsteps, direction, style):
        for i in range(numsteps):
            stepper.oneStep(direction, style)
        # hack given the right blind has to move further
        if stepper == self.r_blind:
            self.turnOffMotors()


    def turnOffMotors(self):
        """recommended for auto-disabling motors on shutdown"""
        self.mh.getMotor(1).run(Adafruit_MotorHAT.RELEASE)
        self.mh.getMotor(2).run(Adafruit_MotorHAT.RELEASE)
        self.mh.getMotor(3).run(Adafruit_MotorHAT.RELEASE)
        self.mh.getMotor(4).run(Adafruit_MotorHAT.RELEASE)

    def open_blinds(self):
        if not self.blinds_are_open:
            if not self.r_thread.isAlive():
                self.r_thread = threading.Thread(target=self.stepper_worker,
                                                 args=(self.r_blind,
                                                       2500,
                                                       Adafruit_MotorHAT.BACKWARD,
                                                       Adafruit_MotorHAT.MICROSTEP))
                self.r_thread.start()
            if not self.l_thread.isAlive():
                self.l_thread = threading.Thread(target=self.stepper_worker,
                                                 args=(self.l_blind,
                                                       2100,
                                                       Adafruit_MotorHAT.BACKWARD,
                                                       Adafruit_MotorHAT.MICROSTEP))
                self.l_thread.start()
            self.blinds_are_open = True

    def close_blinds(self):
        if self.blinds_are_open:
            if not self.r_thread.isAlive():
                self.r_thread = threading.Thread(target=self.stepper_worker,
                                                 args=(self.r_blind,
                                                       2500,
                                                       Adafruit_MotorHAT.FORWARD,
                                                       Adafruit_MotorHAT.MICROSTEP))
                self.r_thread.start()
            if not self.l_thread.isAlive():
                self.l_thread = threading.Thread(target=self.stepper_worker,
                                                 args=(self.l_blind,
                                                       2100,
                                                       Adafruit_MotorHAT.FORWARD,
                                                       Adafruit_MotorHAT.MICROSTEP))
                self.l_thread.start()
            self.blinds_are_open = False

    def step(self, l_value, r_value):
        """for debug and manual operation"""
        if l_value > 0:
            self.stepper_worker(self.l_blind, l_value, Adafruit_MotorHAT.FORWARD, Adafruit_MotorHAT.MICROSTEP)
        else:
            self.stepper_worker(self.l_blind, l_value*-1, Adafruit_MotorHAT.BACKWARD, Adafruit_MotorHAT.MICROSTEP)

        if r_value > 0:
            self.stepper_worker(self.r_blind, r_value, Adafruit_MotorHAT.FORWARD, Adafruit_MotorHAT.MICROSTEP)
        else:
            self.stepper_worker(self.r_blind, r_value*-1, Adafruit_MotorHAT.BACKWARD, Adafruit_MotorHAT.MICROSTEP)


class device_handler(debounce_handler):
    """Publishes the on/off state requested,
       and the IP address of the Echo making the request.
    """
    TRIGGERS = {"blinds": 52000}

    def __init__(self):
        logging.debug('initializing stepper driver')
        self.stepper_driver = stepper()
    self.lastEcho = time.time()

    def act(self, client_address, state):
        logging.debug('State ' + str(state) + ' from client @ ' + str(client_address))
        if not state:
            logging.debug('opening blinds')
            self.stepper_driver.open_blinds()
        else:
            logging.debug('closing blinds')
            self.stepper_driver.close_blinds()
        return True

def main():
    # Startup the fauxmo server
    fauxmo.DEBUG = True
    p = fauxmo.poller()
    u = fauxmo.upnp_broadcast_responder()
    u.init_socket()
    p.add(u)

    # Register the device callback as a fauxmo handler
    d = device_handler()
    for trig, port in d.TRIGGERS.items():
        fauxmo.fauxmo(trig, u, p, None, port, d)

    # Loop and poll for incoming Echo requests
    logging.debug("Entering fauxmo polling loop")
    while True:
        try:
            # Allow time for a ctrl-c to stop the process
            p.poll(100)
            time.sleep(0.1)
        except Exception, e:
            logging.critical("Critical exception: " + str(e))
            break


def debug(l_value, r_value):
    # Manual command line operation of steppers
    s = stepper()
    s.step(l_value, r_value)


if __name__ == "__main__":
    if len(sys.argv) > 2:
        debug(int(sys.argv[1]), int(sys.argv[2]))
    else:
        main()
