### DEFAULTS ARGUMENTS ###

APPROACH_SKILL_ARGS = {
    'setup': {
        'fsm_log_transitions':True,
        'enable_obstacles': True,
    },
    'execute': {
        'distance_to_goal': 0.6,
        'angle_to_goal': 0.0,
        'max_angle_error_allowed': 0.1,
        'max_y_error_allowed': 0.02,
        'angular_velocity': 1.0,
        'linear_velocity': 0.05,
        'enable_final_reverse_adjust': True,
        'max_allowed_correction_tries': 3,
        'step_size': 0.05,
    }
} 

LIDAR_OPTIONS = {
    'center_angle':180,
    'angle_range':15,
}

TOUCH_CHARGER_ARGS = {
    'approach_velocity': 0.05,
    'approach_duration': 0.5,
    'slow_at': 0.5, #where is going to move slowly to dock in meters
    'minimum_distance': 0.375, #in meters
    'dock_velocity': 0.01
}

TRIES_ON_STATES = {
    'MOVE_TO_PRECHARGE': 2,
    'MOVE_BACKWARDS_TO_APPROACH_POINT': 2
}

### CAN DATA ###
CAN_DATA_TURN_ON_CHARGER_PAD = {
    'data': 
        [0x43, 0x52, 0xFF, 0x00, 0x00, 0x00, 0x00, 0x00]
    }

CAN_DATA_TURN_OFF_CHARGER_PAD = {
    'data': 
        [0x43, 0x52, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]
    }

### TIMEOUTS ###

WAIT_FOR_CHARGE_DETECTED_TIMEOUT = 5.0
TOUCH_CHARGER_TIMEOUT = 5.0

### ERROR MESSAGES ###
ERROR_COULD_NOT_LOCALIZE = (1, 'Robot could not get localized')
ERROR_INITIAL_POSITION = (2, 'Initial position should be bigger than self.target_distance')
ERROR_TARGET_MOVED = (3, 'Target position is quite far from initial position')
ERROR_TARGET_LOST = (4, 'Not predictions were got')
ERROR_ROBOT_NOT_LOCALIZED = (5, 'Robot is no localized')
ERROR_MIN_DISTANCE_REACHED = (6, 'The robot reached the minimun distace approach')
ERROR_BAT_CHARGE_NOT_DETECTED = (7, 'The robot touch the charging pad but no charge is detected')
ERROR_APPROACH_TAG_MAX_ATTEMPS_REACHED = (8, 'The approach to tags is not posible, max attemps reached')
ERROR_NO_CHARGER_BUTTON_REACHED =  (9, 'The robot is close to the wall, and the the charger pad was not detected.')
ERROR_NO_CHARGING_PAD =  (10, 'The robot did not detect the charging pad on the sensors list.')