# -*- coding: utf-8 -*-
"""Very basic implementation of the Pipeline/Filters pattern."""

class Context (object):
    pass

class Stage (object):
    """Interface

        An atomic unit of work for the pipeline"""

    def execute(self, context):
        """Perform an unit of work with the given context.

           This method should return True to pass the context to the next
           stage. If False is returned, the execution of the pipeline is
           stopped (usefull to implment filters)."""
        raise NotImplementedError


class Pipeline (Stage):
    """Sequencial pipeline.

        Execute the stages in order

    """

    def __init__(self):
        self._stages = []

    def append_stage(self, stage):
        """Append a stage to the pipeline"""
        self._stages.append(stage)

    def execute(self, context):
        """Execute the pipeline"""
        for stage in self._stages:
            if not stage.execute(context):
                break

