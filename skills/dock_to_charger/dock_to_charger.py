import numpy as np
import time

from raya.skills import RayaSkillHandler, RayaFSMSkill
from skills.approach_to_tags import SkillApproachToTags

from raya.enumerations import POSITION_UNIT, ANGLE_UNIT, STATUS_BATTERY
from raya.controllers import MotionController
from raya.controllers import LidarController
from raya.controllers import SensorsController
from raya.controllers import StatusController
from raya.enumerations import SKILL_STATE
from raya.exceptions import *
from .constants import *

class SkillDockToCharger(RayaFSMSkill):
    ### Arguments ###
    
    DEFAULT_SETUP_ARGS = {
        'approach_to_tags_args': APPROACH_SKILL_ARGS['setup'],
    }
    
    REQUIRED_SETUP_ARGS = {
        'working_cameras',
        'tags_size',
    }
    
    DEFAULT_EXECUTE_ARGS = {
        'approach_to_tags_args': APPROACH_SKILL_ARGS['execute'],
        'lidar': LIDAR_OPTIONS,
        'touch_charger_args': TOUCH_CHARGER_ARGS,
        'tries_on_states': TRIES_ON_STATES,
    }
    
    REQUIRED_EXECUTE_ARGS = {
        'identifier'
    }

    
    ### FSM States ###
    
    
    STATES = [
        'APPROACH_TO_CHARGER',
        'MOVE_FOWARD_TO_CHARGER',
        'TOUCH_CHARGER',
        'WAIT_FOR_CHARGE_DETECTED',
        'MOVE_BACKWARDS_TO_APPROACH_POINT',
        'MOVE_TO_PRECHARGE',
        'END',
    ]

    INITIAL_STATE = 'APPROACH_TO_CHARGER'

    END_STATES = [
        'END'
    ]
    
    STATES_TIMEOUTS = {}
    
    ### SKILL METHODS ###


    async def setup(self):
        self.motion:MotionController = await self.get_controller('motion')
        self.lidar:LidarController = await self.get_controller('lidar')
        self.sensors:SensorsController = await self.get_controller('sensors')
        self.status:StatusController = await self.get_controller('status')
        self.skill_apr2tags:RayaSkillHandler = \
                self.register_skill(SkillApproachToTags)
        
        # Updates the setup args with the default ones
        setup_args = {
            'working_cameras': self.setup_args['working_cameras'],
            'tags_size': self.setup_args['tags_size']
        }
        setup_args.update(self.setup_args['approach_to_tags_args'])
        await self.skill_apr2tags.execute_setup(setup_args=setup_args)
        
    
    async def finish(self):
        self.skill_apr2tags.wait_finish()
    
    ### HELPERS ###
    
    
    async def _move_fowards_until(self, distance, velocity):
        distace_lidar = await self._get_lidar_distance()
        try:
            await self.motion.set_velocity(
                x_velocity=velocity,
                y_velocity=0.0,
                angular_velocity=0.0,
                duration=3.0,
                enable_obstacles=False,
                wait=False,
            )
        except RayaRobotNotMoving:
            pass
        if distace_lidar < distance:
            await self.send_feedback({
                'status_msg': 
                    f'Distance reached: goal \'{distance}\','
                    f' measured \'{distace_lidar}\''
            })
            await self.motion.cancel_motion()


    async def _get_lidar_distance(self):
        raw_data = self.lidar.get_raw_data()
        average_distance = np.mean(raw_data[-10:] + raw_data[:10])
        await self.send_feedback({
            'status_msg': 
                f'Distance measured: \'{average_distance}\''
        })
        return average_distance


    async def _get_charging_button_state(self):
        sensors = self.sensors.get_all_sensors_values()
        is_charging = int(sensors['charger_pad']) != 0
        await self.send_feedback({
            'status_msg': 
                f'Charging button state: \'{is_charging}\''
        })
        if is_charging:
            await self.send_feedback({
                'status_msg': 'The robot is in the dock'
            })
            await self.motion.cancel_motion()
        return is_charging


    async def _get_charging_battery_state(self):
        sensors = await self.status.get_battery_status()
        battery_charging = sensors['status'] == STATUS_BATTERY.CHARGING
  
        if battery_charging:
            await self.send_feedback({
                'status_msg': 'The battery is charging'
            })
            pass
        return battery_charging


    async def _change_relay_charge(self, state=False):
        if state:
            # turn on
            await self.sensors.specific_robot_command(
                'package_to_microcontrollers',
                parameters=CAN_DATA_TURN_ON_CHARGER_PAD
            )
        else:
            #turn off
            await self.sensors.specific_robot_command(
                'package_to_microcontrollers',
                parameters=CAN_DATA_TURN_OFF_CHARGER_PAD
            )

     
    async def _move_backwards_to_point(self, distance, velocity):
        distace_lidar = await self._get_lidar_distance()
        try:
            await self.motion.set_velocity(
                x_velocity=-velocity,
                y_velocity=0.0,
                angular_velocity=0.0,
                duration=3.0,
                enable_obstacles=False,
                wait=False,
            )
        except RayaRobotNotMoving:
            pass
        if distace_lidar > distance:
            await self.send_feedback({
                'status_msg': 
                    f'Distance reached: goal \'{distance}\','
                    f' measured \'{distace_lidar}\''
            })
            await self.motion.cancel_motion()

    ### ACTIONS ###
    
    async def setup_actions(self):
        self._errors_MOVE_BACKWARDS_TO_APPROACH_POINT = 0
        self._errors_MOVE_TO_PRECHARGE = 0
    
    
    async def enter_APPROACH_TO_CHARGER(self):
        self._distance_approach_to_charger = await self._get_lidar_distance()
        # TODO run Approach Skill
        execute_args={
            'identifier': self.execute_args['identifier']
        }
        execute_args.update(self.execute_args['approach_to_tags_args'])
        try:
            approach_result = await self.skill_apr2tags.execute_main(
                execute_args=execute_args,
                callback_feedback=self.cb_approach_feedback
            )
            await self.send_feedback(approach_result)
        except Exception as error:
            self.log.error('approach execute failed, Exception type:'
                            f'{type(error)}, Exception: {error}')
            self.abort(*error)
        await self.skill_apr2tags.execute_finish(
            wait=False
        )


    async def leave_MOVE_FOWARD_TO_CHARGER(self):
        await self._change_relay_charge(state=True)
        self._errors_MOVE_TO_PRECHARGE = 0


    async def enter_TOUCH_CHARGER(self):
        self._distance_prep_to_charge = \
            await self._get_lidar_distance()
        self.timer_TOUCH_CHARGER = time.time()
        await self.send_feedback({
            'status_msg': 
                'SET _distance_prep_to_charge:'
                f'{self._distance_prep_to_charge}'
        })


    async def enter_WAIT_FOR_CHARGE_DETECTED(self):
        self.timer_WAIT_FOR_CHARGE_DETECTED = time.time()


    async def enter_MOVE_BACKWARDS_TO_APPROACH_POINT(self):
        self._errors_MOVE_BACKWARDS_TO_APPROACH_POINT += 1
    
    
    async def enter_MOVE_TO_PRECHARGE(self):
        self._errors_MOVE_TO_PRECHARGE += 1
    
    
    ### TRANSITIONS ###
    
    
    async def transition_from_APPROACH_TO_CHARGER(self):
        if await self.skill_apr2tags.get_execution_state() == SKILL_STATE.FINISHED:
            self.set_state('MOVE_FOWARD_TO_CHARGER')


    async def transition_from_MOVE_FOWARD_TO_CHARGER(self):
        if await self._get_charging_button_state():
            self.set_state('END')
  
        if await self._get_lidar_distance() <= \
            self.execute_args['touch_charger_args']['slow_at']:
            self.set_state('TOUCH_CHARGER')

        await self._move_fowards_until(
            distance=self.execute_args['touch_charger_args']['slow_at'],
            velocity=self.execute_args['touch_charger_args']['approach_velocity']
        )


    async def transition_from_TOUCH_CHARGER(self):
        if await self._get_charging_button_state():
            self.set_state('WAIT_FOR_CHARGE_DETECTED')
        
        time_left = TOUCH_CHARGER_TIMEOUT - (
              time.time() - self.timer_TOUCH_CHARGER
        )
        await self.send_feedback({
            'status_msg': 
                f'Time left to pass to MOVE_BACKWARDS_TO_APPROACH_POINT state: '
                f'{time_left}'
        })
        
        reached_min_distance = await self._get_lidar_distance() <= \
            self.execute_args['touch_charger_args']['minimum_distance']
        if time_left < 0 or (reached_min_distance and \
            not await self._get_charging_button_state()):
            self.set_state('MOVE_BACKWARDS_TO_APPROACH_POINT')
	
        await self._move_fowards_until(
            distance=self.execute_args['touch_charger_args']['minimum_distance'],
            velocity=self.execute_args['touch_charger_args']['dock_velocity']
        )


    async def transition_from_MOVE_BACKWARDS_TO_APPROACH_POINT(self):
        if self._errors_MOVE_BACKWARDS_TO_APPROACH_POINT == \
                self.execute_args['tries_on_states']['MOVE_BACKWARDS_TO_APPROACH_POINT']:
            self.abort(*ERROR_NO_CHARGER_BUTTON_REACHED)

        if await self._get_lidar_distance() >= \
                self._distance_approach_to_charger:
            self.set_state('APPROACH_TO_CHARGER')
        
        await self._move_backwards_to_point(
            distance=self._distance_approach_to_charger,
            velocity=self.execute_args['touch_charger_args']['approach_velocity']
        )


    async def transition_from_WAIT_FOR_CHARGE_DETECTED(self):
        if await self._get_charging_battery_state():
            self.set_state('END')
        
        time_left = WAIT_FOR_CHARGE_DETECTED_TIMEOUT - (
              time.time() - self.timer_WAIT_FOR_CHARGE_DETECTED
        )
        await self.send_feedback({
            'status_msg': 
                f'Time left to pass to MOVE_TO_PRECHARGE state: '
                f'{time_left}'
        })
        if time_left < 0:
            self.set_state('MOVE_TO_PRECHARGE')
   

    async def transition_from_MOVE_TO_PRECHARGE(self):
        await self.send_feedback({
            'status_msg': 
                f'Current tries on MOVE_TO_PRECHARGE state: '
                f'{self._errors_MOVE_TO_PRECHARGE}'
        })
        if self._errors_MOVE_TO_PRECHARGE == \
                self.execute_args['tries_on_states']['MOVE_TO_PRECHARGE']:
            if self.motion.is_moving():
                self.motion.cancel_motion()
            self.abort(*ERROR_BAT_CHARGE_NOT_DETECTED)
            
        if await self._get_lidar_distance() >= \
                self._distance_prep_to_charge:
            self.set_state('TOUCH_CHARGER')
        
        await self._move_backwards_to_point(
            distance=self._distance_prep_to_charge,
            velocity=self.execute_args['touch_charger_args']['dock_velocity']
        )

    ### CALLBACKS ###
    
    async def cb_approach_feedback(self, feedback):
        await self.send_feedback(feedback)
