# coding=utf-8
#
# stepper_ drv8825.py - Output for DRV-8825 stepper controller
#
import copy

from flask_babel import lazy_gettext

from mycodo.outputs.base_output import AbstractOutput
from mycodo.utils.influx import add_measurements_influxdb


def constraints_pass_positive_value(mod_input, value):
    """
    Check if the user input is acceptable
    :param mod_input: SQL object with user-saved Input options
    :param value: float or int
    :return: tuple: (bool, list of strings)
    """
    errors = []
    all_passed = True
    # Ensure value is positive
    if value <= 0:
        all_passed = False
        errors.append("Must be a positive value")
    return all_passed, errors, mod_input


def constraints_pass_positive_or_zero_value(mod_input, value):
    """
    Check if the user input is acceptable
    :param mod_input: SQL object with user-saved Input options
    :param value: float or int
    :return: tuple: (bool, list of strings)
    """
    errors = []
    all_passed = True
    # Ensure value is positive
    if value < 0:
        all_passed = False
        errors.append("Must be zero or a positive value")
    return all_passed, errors, mod_input


# Measurements
measurements_dict = {
    0: {
        'measurement': 'rotation',
        'unit': 'steps'
    }
}

channels_dict = {
    0: {
        'types': ['value'],
        'measurements': [0]
    }
}

# Output information
OUTPUT_INFORMATION = {
    'output_name_unique': 'drv8825',
    'output_name': "{}: DRV8825".format(lazy_gettext('Stepper Motor Controller')),
    'measurements_dict': measurements_dict,
    'channels_dict': channels_dict,
    'output_types': ['value'],

    'url_manufacturer': 'https://www.ti.com/product/DRV8825',
    'url_datasheet': 'https://www.ti.com/lit/ds/symlink/drv8825.pdf',
    'url_product_purchase': 'https://www.pololu.com/product/2133',

    'options_enabled': [
        'button_send_value'
    ],
    'options_disabled': ['interface'],

    'dependencies_module': [
        ('pip-pypi', 'rpi_python_drv8825', 'rpi_python_drv8825')
    ],

    'interfaces': ['GPIO'],

    'custom_options': [
        {
            'id': 'pin_enable',
            'type': 'integer',
            'default_value': 0,
            'constraints_pass': constraints_pass_positive_or_zero_value,
            'name': 'Enable Pin',
            'phrase': 'The Enable pin of the controller (BCM numbering)'
        },
        {
            'id': 'pin_step',
            'type': 'integer',
            'default_value': 0,
            'constraints_pass': constraints_pass_positive_value,
            'name': 'Step Pin',
            'phrase': 'The Step pin of the controller (BCM numbering)'
        },
        {
            'id': 'pin_dir',
            'type': 'integer',
            'default_value': 0,
            'constraints_pass': constraints_pass_positive_value,
            'name': 'Direction Pin',
            'phrase': 'The Direction pin of the controller (BCM numbering)'
        },
        {
            'id': 'pin_mode_1',
            'type': 'integer',
            'default_value': 0,
            'constraints_pass': constraints_pass_positive_value,
            'name': 'Mode Pin 1',
            'phrase': 'The Mode Pin 1 of the controller (BCM numbering)'
        },
        {
            'id': 'pin_mode_2',
            'type': 'integer',
            'default_value': 0,
            'constraints_pass': constraints_pass_positive_value,
            'name': 'Mode Pin 2',
            'phrase': 'The Mode Pin 2 of the controller (BCM numbering)'
        },
        {
            'id': 'pin_mode_3',
            'type': 'integer',
            'default_value': 0,
            'constraints_pass': constraints_pass_positive_value,
            'name': 'Mode Pin 3',
            'phrase': 'The Mode Pin 3 of the controller (BCM numbering)'
        },
        {
            'id': 'full_step_delay',
            'type': 'float',
            'default_value': 0.005,
            'constraints_pass': constraints_pass_positive_value,
            'name': 'Full Step Delay',
            'phrase': 'The Full Step Delay of the controller'
        },
        {
            'id': 'step_resolution',
            'type': 'select',
            'default_value': '1/32',
            'options_select': [
                ('Full', 'Full'),
                ('Half', 'Half'),
                ('1/4', '1/4'),
                ('1/8', '1/8'),
                ('1/16', '1/16'),
                ('1/32', '1/32')
            ],
            'name': lazy_gettext('Step Resolution'),
            'phrase': lazy_gettext('The Step Resolution of the controller')
        },
    ]
}


class OutputModule(AbstractOutput):
    """
    An output support class that operates an output
    """
    def __init__(self, output, testing=False):
        super(OutputModule, self).__init__(output, testing=testing, name=__name__)

        self.stepper = None
        self.output_setup = False
        self.stepper_running = None

        self.pin_enable = None
        self.pin_step = None
        self.pin_dir = None
        self.pin_mode_1 = None
        self.pin_mode_2 = None
        self.pin_mode_3 = None
        self.full_step_delay = None
        self.step_resolution = None

        self.setup_custom_options(
            OUTPUT_INFORMATION['custom_options'], output)

    def setup_output(self):
        from rpi_python_drv8825.stepper import StepperMotor

        self.setup_on_off_output(OUTPUT_INFORMATION)

        if self.pin_step and self.pin_dir and self.pin_mode_1 and self.pin_mode_2 and self.pin_mode_3:
            try:
                self.stepper = StepperMotor(
                    self.pin_enable,
                    self.pin_step,
                    self.pin_dir,
                    (self.pin_mode_1, self.pin_mode_2, self.pin_mode_3),
                    self.step_resolution,
                    self.full_step_delay)
                self.output_setup = True
            except:
                self.output_setup = False

    def output_switch(self, state, output_type=None, amount=None, output_channel=None):
        measure_dict = copy.deepcopy(measurements_dict)

        if amount not in [None, 0]:
            if amount > 0:
                self.stepper_running = True
                self.stepper.enable(True)
                self.stepper.run(amount, True)
                self.stepper.enable(False)
                self.stepper_running = True
            else:
                self.stepper_running = True
                self.stepper.enable(True)
                self.stepper.run(abs(amount), False)
                self.stepper.enable(False)
                self.stepper_running = False
            measure_dict[0]['value'] = amount
        elif state == "off":
            self.stepper.enable(False)
            self.stepper_running = False
        else:
            self.logger.error(
                "Invalid parameters: State: {state}, Type: {ot}, Amount: {amt}".format(
                    state=state,
                    ot=output_type,
                    amt=amount))
            return

        add_measurements_influxdb(self.unique_id, measure_dict)

    def is_on(self, output_channel=None):
        if self.is_setup():
            return self.stepper_running

    def is_setup(self):
        if self.output_setup:
            return True
        return False
