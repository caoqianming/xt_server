from apps.wf.models import Workflow, Ticket, State
from rest_framework.exceptions import ParseError
from apps.wf.services import WfService

class TicketMixin:
    workflow_key = None
    ticket_auto_submit_on_update = True
    ticket_data_save_keys = []

    def get_workflow_key(self, instance):
        return self.workflow_key
    
    def should_create_ticket(self, instance):
        return True
    
    def perform_create(self, serializer):
        ins = serializer.save()
        if self.workflow_key:
            try:
                wf = Workflow.objects.get(key=self.workflow_key)
            except Exception as e:
                raise ParseError(f'工作流{self.workflow_key}异常:{e}')
            source_state: State = WfService.get_workflow_start_state(wf)
            transitions = WfService.get_state_transitions(source_state)
            if transitions.count() == 1:
                transition = transitions.first()
                
            else:
                raise ParseError(f'工作流{self.workflow_key}异常:起始状态{source_state}有多个后续状态;不可直接创建')

            