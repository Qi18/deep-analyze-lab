"""Pause at a saved optimizer step without changing the full-run LR horizon."""
import os
from transformers import TrainerCallback
from swift.plugin import extra_callbacks
class RepairSegmentCallback(TrainerCallback):
    def on_step_end(self,args,state,control,**kwargs):
        limit=int(os.environ.get("REPAIR_STOP_STEP","1000000000"))
        if state.global_step>=limit:
            control.should_save=True
            control.should_training_stop=True
        return control
extra_callbacks.append(RepairSegmentCallback())
