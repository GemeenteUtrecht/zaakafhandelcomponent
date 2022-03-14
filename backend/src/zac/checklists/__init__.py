"""
A checklist can be created and followed up for a given ZAAK.

Checklists are related to checklisttypes which are are related 
to ZAAKTYPEs. Only one checklisttype can be assigned to a 
ZAAKTYPE based on the `omschrijving` and `catalogus` of the ZAAKTYPE. 

Checklist questions are related to checklisttypes. Questions can be 
both an open question as well as a multiple choice question.
The questions, related multiple choice answers and checklisttypes can all be 
configured in the Django admin of the checklisttype. If choices
are given for a question, this question is considered to be a multiple
choice question and the answers given to those questions will be validated 
against those values.

For audit trail purposes answers are never updated, instead 
new answers will be created if they are "updated".

Only one checklist can be assigned to any given ZAAK. This app allows 
you to register a checklist for a given ZAAK reference.

Eventually, the data/API should be moved into a standalone API, which is probably
going to be the (generic) objects API.

User story: TODO
Technical issue: TODO
"""
default_app_config = "zac.checklists.apps.ChecklistsConfig"
