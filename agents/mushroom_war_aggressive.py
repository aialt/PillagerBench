from agents.mushroom_war_base import MushroomWarBase


class MushroomWarBalanced(MushroomWarBase):
    name = "mushroom_war_aggressive"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
