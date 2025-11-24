from apps.wf.models import Workflow, Ticket, State
from rest_framework.exceptions import ParseError
from apps.wf.services import WfService
from apps.system.models import User

class TicketMixin:
    """
    可挂载到正常model,使其支持工作流
    model添加ticket字段
    serializer添加ticket_
    该处会修改perform_create和perform_update方法,注意!
    """
    workflow_key = None
    ticket_auto_submit_on_update = True
    ticket_data_save_fields = []

    def get_workflow_key(self, instance):
        return self.workflow_key
    
    def should_create_ticket(self, instance):
        return True
    
    def gen_ticket_data(self, instance):
        ticket_data = {"t_model": instance.__class__.__name__, "t_id": str(instance.id)}
        if self.ticket_data_save_fields:
            for field in self.ticket_data_save_fields:
                if '.' in field:
                    attr_list  = field.split('.')
                    expr = instance
                    for a in attr_list:
                        expr = getattr(expr, a)
                    ticket_data[field] = expr
                else:
                    ticket_data[field] = getattr(instance, field)
        return ticket_data

    def perform_update(self, serializer):
        ins = serializer.save()
        ruser = self.request.user
        if ins.ticket and self.ticket_auto_submit_on_update:
            source_state:State = ins.ticket.state
            if source_state.type != State.STATE_TYPE_START:
                raise ParseError('该工单已开始流转,不可修改')
            if ruser != ins.ticket.create_by:
                raise ParseError('非工单创建人不可修改')
            transition = WfService.get_state_transitions(source_state).first()
            ticket_data = self.gen_ticket_data(ins)
            WfService.handle_ticket(ticket=ins.ticket, transition=transition, new_ticket_data=ticket_data, 
                                    handler=self.request.user, oinfo=self.request.data)
    
    def perform_create(self, serializer):
        ins = serializer.save()
        handler:User = self.request.user
        if self.should_create_ticket(ins):
            workflow_key = self.get_workflow_key(ins)
            if not workflow_key:
                raise ParseError('工作流异常:必须赋值workflow_key')
            try:
                wf = Workflow.objects.get(key=workflow_key)
            except Exception as e:
                raise ParseError(f'工作流{workflow_key}异常:{e}')
            
            # 开始创建工单
            source_state: State = WfService.get_workflow_start_state(wf)
            transitions = WfService.get_state_transitions(source_state)
            if transitions.count() == 1:
                transition = transitions.first()
                ticket_data = self.gen_ticket_data(ins)
                WfService.handle_ticket(ticket=None, transition=transition, new_ticket_data=ticket_data, 
                                        handler=handler, oinfo=self.request.data)
            else:
                raise ParseError(f'工作流{workflow_key}异常:有多个后续状态;不可处理')

    def perform_destroy(self, instance):
        ticket = instance.ticket
        if ticket and ticket.state.type != State.STATE_TYPE_START:
            raise ParseError('该工单已开始流转,不可删除')
        instance.delete()
        ticket.delete()
        