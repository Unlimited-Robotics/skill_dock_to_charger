from raya.application_base import RayaApplicationBase
from raya.skills import RayaSkillHandler
from skills.dock_to_charger import SkillDockToCharger

class RayaApplication(RayaApplicationBase):

    async def setup(self):
        self.log.warn(f'Registering skill')
        self.skill_dock:RayaSkillHandler = \
                self.register_skill(SkillDockToCharger)
        self.log.warn('Executing setup')
        await self.skill_dock.execute_setup(
            setup_args={
                'working_cameras': ['nav_bottom', 'head_front'],
                'tags_size': 0.09,
            }
        )

    async def loop(self):
        self.log.warn(f'Executing skill')
        execute_result = await self.skill_dock.execute_main(
            execute_args={
                'identifier': [0, 1]
            },
            callback_feedback=self.cb_feedback
        )
        self.log.debug(f'result: {execute_result}')


    async def finish(self):
        self.log.info(f'Finishing skill')
        await self.skill_dock.execute_finish(
            callback_feedback=self.cb_feedback
        )
        self.log.info(f'App finished')


    async def cb_feedback(self, feedback):
        self.log.debug(feedback)
