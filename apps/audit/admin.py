from django.contrib import admin
from apps.audit.models import (Standard, StandardItem, Company, 
                               Atask, AtaskItem, AtaskIssue, AtaskTeam)
# Register your models here.

@admin.register(StandardItem)
class StandardItemAdmin(admin.ModelAdmin):
    model = StandardItem
    list_display = ["id", "standard",  "number", "level", "risk_level", "full_score"]
    ordering = ["number"]
    
@admin.register(Standard)
class StandardAdmin(admin.ModelAdmin):
    list_display = ["id", "name", "to_type", "enabled", "total_score"]


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ["id", "name", "level", "types", "parent"]


@admin.register(Atask)
class AtaskAdmin(admin.ModelAdmin):
    list_display = ["id", "year", "state", "company", "score", "standard"]


@admin.register(AtaskTeam)
class AtaskTeamAdmin(admin.ModelAdmin):
    list_display = ["id", "atask", "member", "duty_type"]


@admin.register(AtaskItem)
class AtaskItemAdmin(admin.ModelAdmin):
    list_display = ["id", "atask", "standarditem", "is_suit", "checked", "score", "kill_score"]


@admin.register(AtaskIssue)
class AtaskIssueAdmin(admin.ModelAdmin):
    list_display = ["id", "ataskitem", "content"]