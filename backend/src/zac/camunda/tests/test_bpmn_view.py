from django.urls import reverse

import requests_mock
from rest_framework.test import APITestCase

from zac.accounts.tests.factories import UserFactory

DOCUMENTS_ROOT = "http://documents.nl/api/v1/"
ZAKEN_ROOT = "http://zaken.nl/api/v1/"
CATALOGI_ROOT = "https://open-zaak.nl/catalogi/api/v1/"
PI_URL = "https://camunda.example.com/engine-rest/process-instance"

# Taken from https://docs.camunda.org/manual/7.13/reference/rest/task/get/
TASK_DATA = {
    "id": "598347ee-62fc-46a2-913a-6e0788bc1b8c",
    "name": "aName",
    "assignee": None,
    "created": "2013-01-23T13:42:42.000+0200",
    "due": "2013-01-23T13:49:42.576+0200",
    "followUp": "2013-01-23T13:44:42.437+0200",
    "delegationState": "RESOLVED",
    "description": "aDescription",
    "executionId": "anExecution",
    "owner": "anOwner",
    "parentTaskId": None,
    "priority": 42,
    "processDefinitionId": "Adhoc_vergaderen:1:2ee97bc4-a370-11eb-970c-6a0042b17f4a",
    "processInstanceId": "87a88170-8d5c-4dec-8ee2-972a0be1b564",
    "caseDefinitionId": "aCaseDefId",
    "caseInstanceId": "aCaseInstId",
    "caseExecutionId": "aCaseExecution",
    "taskDefinitionKey": "aTaskDefinitionKey",
    "suspended": False,
    "formKey": None,
    "tenantId": "aTenantId",
}

BPMN_DATA = {
    "id": "Adhoc_vergaderen:1:2ee97bc4-a370-11eb-970c-6a0042b17f4a",
    "bpmn20_xml": '<?xml version="1.0" encoding="UTF-8"?>\n<bpmn:definitions xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL" xmlns:bpmndi="http://www.omg.org/spec/BPMN/20100524/DI" xmlns:dc="http://www.omg.org/spec/DD/20100524/DC" xmlns:camunda="http://camunda.org/schema/1.0/bpmn" xmlns:di="http://www.omg.org/spec/DD/20100524/DI" xmlns:bioc="http://bpmn.io/schema/bpmn/biocolor/1.0" id="Definitions_0ukdc2m" targetNamespace="http://bpmn.io/schema/bpmn" exporter="Camunda Modeler" exporterVersion="4.6.0">\n  <bpmn:collaboration id="Collaboration_02wzhhk">\n    <bpmn:participant id="adhoc-vergaderen" name="Ad Hoc vergaderen" processRef="Adhoc_vergaderen" />\n  </bpmn:collaboration>\n  <bpmn:process id="Adhoc_vergaderen" isExecutable="true">\n    <bpmn:startEvent id="StartEvent_1">\n      <bpmn:outgoing>Flow_04j4duh</bpmn:outgoing>\n    </bpmn:startEvent>\n    <bpmn:subProcess id="Activity_0hs06x4" name="Aanmaken zaak">\n      <bpmn:incoming>Flow_04j4duh</bpmn:incoming>\n      <bpmn:outgoing>Flow_1geb3l5</bpmn:outgoing>\n      <bpmn:parallelGateway id="Gateway_0irp3dd">\n        <bpmn:incoming>Flow_0e1qs13</bpmn:incoming>\n        <bpmn:outgoing>Flow_0k2y56u</bpmn:outgoing>\n        <bpmn:outgoing>Flow_0b3uli4</bpmn:outgoing>\n        <bpmn:outgoing>Flow_03dqpsa</bpmn:outgoing>\n      </bpmn:parallelGateway>\n      <bpmn:parallelGateway id="Gateway_1fk4sdd">\n        <bpmn:incoming>Flow_1imwypd</bpmn:incoming>\n        <bpmn:incoming>Flow_0iru6gy</bpmn:incoming>\n        <bpmn:incoming>Flow_10co35r</bpmn:incoming>\n        <bpmn:outgoing>Flow_010fgho</bpmn:outgoing>\n      </bpmn:parallelGateway>\n      <bpmn:endEvent id="Event_10rrikb">\n        <bpmn:incoming>Flow_1uqc2f6</bpmn:incoming>\n      </bpmn:endEvent>\n      <bpmn:serviceTask id="Activity_0n3ico3" name="Relateer bijlage" camunda:type="external" camunda:topic="zaak-relate-document">\n        <bpmn:incoming>Flow_03dqpsa</bpmn:incoming>\n        <bpmn:outgoing>Flow_10co35r</bpmn:outgoing>\n        <bpmn:multiInstanceLoopCharacteristics camunda:collection="${bijlagen.elements()}" camunda:elementVariable="informatieobject" />\n      </bpmn:serviceTask>\n      <bpmn:serviceTask id="Activity_0evaud6" name="Zet eigenschap" camunda:type="external" camunda:topic="zaak-eigenschap">\n        <bpmn:incoming>Flow_0b3uli4</bpmn:incoming>\n        <bpmn:outgoing>Flow_0iru6gy</bpmn:outgoing>\n        <bpmn:multiInstanceLoopCharacteristics camunda:collection="${eigenschappen.elements()}" camunda:elementVariable="eigenschap" />\n      </bpmn:serviceTask>\n      <bpmn:startEvent id="Event_0nng048">\n        <bpmn:outgoing>Flow_09x26k9</bpmn:outgoing>\n      </bpmn:startEvent>\n      <bpmn:serviceTask id="Activity_16podmr" name="Aanmaken zaak" camunda:type="external" camunda:topic="initialize-zaak">\n        <bpmn:extensionElements>\n          <camunda:inputOutput>\n            <camunda:inputParameter name="zaaktype">https://openzaak.utrechtproeftuin.nl/catalogi/api/v1/zaaktypen/e7ed876a-6626-42a5-b63f-a06c6a5c2da2</camunda:inputParameter>\n            <camunda:inputParameter name="organisatieRSIN">002220647</camunda:inputParameter>\n          </camunda:inputOutput>\n        </bpmn:extensionElements>\n        <bpmn:incoming>Flow_09x26k9</bpmn:incoming>\n        <bpmn:outgoing>Flow_0e1qs13</bpmn:outgoing>\n      </bpmn:serviceTask>\n      <bpmn:serviceTask id="Activity_1wwizjg" name="Relateren aan andere zaak" camunda:type="external" camunda:topic="gerelateerde-zaak">\n        <bpmn:extensionElements>\n          <camunda:inputOutput>\n            <camunda:inputParameter name="bijdrageAard">bijdrage</camunda:inputParameter>\n          </camunda:inputOutput>\n        </bpmn:extensionElements>\n        <bpmn:incoming>Flow_0k2y56u</bpmn:incoming>\n        <bpmn:outgoing>Flow_1imwypd</bpmn:outgoing>\n      </bpmn:serviceTask>\n      <bpmn:sequenceFlow id="Flow_1imwypd" sourceRef="Activity_1wwizjg" targetRef="Gateway_1fk4sdd" />\n      <bpmn:sequenceFlow id="Flow_0k2y56u" sourceRef="Gateway_0irp3dd" targetRef="Activity_1wwizjg" />\n      <bpmn:sequenceFlow id="Flow_0e1qs13" sourceRef="Activity_16podmr" targetRef="Gateway_0irp3dd" />\n      <bpmn:sequenceFlow id="Flow_09x26k9" sourceRef="Event_0nng048" targetRef="Activity_16podmr" />\n      <bpmn:sequenceFlow id="Flow_010fgho" sourceRef="Gateway_1fk4sdd" targetRef="Activity_0exo4cy" />\n      <bpmn:sequenceFlow id="Flow_0iru6gy" sourceRef="Activity_0evaud6" targetRef="Gateway_1fk4sdd" />\n      <bpmn:sequenceFlow id="Flow_10co35r" sourceRef="Activity_0n3ico3" targetRef="Gateway_1fk4sdd" />\n      <bpmn:sequenceFlow id="Flow_0b3uli4" sourceRef="Gateway_0irp3dd" targetRef="Activity_0evaud6" />\n      <bpmn:sequenceFlow id="Flow_03dqpsa" sourceRef="Gateway_0irp3dd" targetRef="Activity_0n3ico3" />\n      <bpmn:sequenceFlow id="Flow_00r3dvx" sourceRef="Event_0qrifrb" targetRef="Activity_0rt69rq" />\n      <bpmn:intermediateCatchEvent id="Event_0qrifrb" name="Besluit uit iBabs ontvangen">\n        <bpmn:incoming>Flow_1ohq7e9</bpmn:incoming>\n        <bpmn:outgoing>Flow_00r3dvx</bpmn:outgoing>\n        <bpmn:messageEventDefinition id="MessageEventDefinition_1xsg777" messageRef="Message_0o69ss6" />\n      </bpmn:intermediateCatchEvent>\n      <bpmn:userTask id="Activity_1ns1o7b" name="iBabs openen" camunda:formKey="zac:doRedirect">\n        <bpmn:extensionElements>\n          <camunda:inputOutput>\n            <camunda:inputParameter name="openInNewWindow">${true}</camunda:inputParameter>\n            <camunda:inputParameter name="redirectTo">https://portaltest.ibabs.eu/Dossier/Add/${zaakIdentificatie}</camunda:inputParameter>\n          </camunda:inputOutput>\n        </bpmn:extensionElements>\n        <bpmn:incoming>Flow_1l59wnk</bpmn:incoming>\n        <bpmn:outgoing>Flow_1ohq7e9</bpmn:outgoing>\n      </bpmn:userTask>\n      <bpmn:sequenceFlow id="Flow_1ohq7e9" sourceRef="Activity_1ns1o7b" targetRef="Event_0qrifrb" />\n      <bpmn:serviceTask id="Activity_0rt69rq" name="Resultaat zetten en sluiten zaak" camunda:type="external" camunda:topic="close-zaak">\n        <bpmn:extensionElements>\n          <camunda:inputOutput>\n            <camunda:inputParameter name="resultaattype">https://openzaak.utrechtproeftuin.nl/catalogi/api/v1/resultaattypen/68bdb629-5126-40b1-84a3-1025e21456b8</camunda:inputParameter>\n          </camunda:inputOutput>\n        </bpmn:extensionElements>\n        <bpmn:incoming>Flow_00r3dvx</bpmn:incoming>\n        <bpmn:outgoing>Flow_1uqc2f6</bpmn:outgoing>\n      </bpmn:serviceTask>\n      <bpmn:sequenceFlow id="Flow_1uqc2f6" sourceRef="Activity_0rt69rq" targetRef="Event_10rrikb" />\n      <bpmn:userTask id="Activity_0exo4cy" name="Voorstel maken (Xential)" camunda:formKey="zac:doRedirect">\n        <bpmn:extensionElements>\n          <camunda:inputOutput>\n            <camunda:inputParameter name="openInNewWindow">${true}</camunda:inputParameter>\n            <camunda:inputParameter name="redirectTo">http://xential.domstad.org/xential</camunda:inputParameter>\n          </camunda:inputOutput>\n          <camunda:formData>\n            <camunda:formField id="FormField_3hm476t" type="string" defaultValue="http://xential.domstad.org/xential" />\n          </camunda:formData>\n        </bpmn:extensionElements>\n        <bpmn:incoming>Flow_010fgho</bpmn:incoming>\n        <bpmn:outgoing>Flow_1l59wnk</bpmn:outgoing>\n      </bpmn:userTask>\n      <bpmn:sequenceFlow id="Flow_1l59wnk" sourceRef="Activity_0exo4cy" targetRef="Activity_1ns1o7b" />\n    </bpmn:subProcess>\n    <bpmn:sequenceFlow id="Flow_04j4duh" sourceRef="StartEvent_1" targetRef="Activity_0hs06x4" />\n    <bpmn:sequenceFlow id="Flow_1geb3l5" sourceRef="Activity_0hs06x4" targetRef="Event_09x04tp" />\n    <bpmn:endEvent id="Event_09x04tp">\n      <bpmn:incoming>Flow_1geb3l5</bpmn:incoming>\n    </bpmn:endEvent>\n  </bpmn:process>\n  <bpmn:message id="Message_0o69ss6" name="Besluitvorming_ontvangen" />\n  <bpmndi:BPMNDiagram id="BPMNDiagram_1">\n    <bpmndi:BPMNPlane id="BPMNPlane_1" bpmnElement="Collaboration_02wzhhk">\n      <bpmndi:BPMNShape id="Participant_07pvcn9_di" bpmnElement="adhoc-vergaderen" isHorizontal="true">\n        <dc:Bounds x="127" y="86" width="1353" height="584" />\n      </bpmndi:BPMNShape>\n      <bpmndi:BPMNEdge id="Flow_1geb3l5_di" bpmnElement="Flow_1geb3l5">\n        <di:waypoint x="1350" y="320" />\n        <di:waypoint x="1402" y="320" />\n      </bpmndi:BPMNEdge>\n      <bpmndi:BPMNEdge id="Flow_04j4duh_di" bpmnElement="Flow_04j4duh">\n        <di:waypoint x="215" y="277" />\n        <di:waypoint x="280" y="277" />\n      </bpmndi:BPMNEdge>\n      <bpmndi:BPMNShape id="_BPMNShape_StartEvent_2" bpmnElement="StartEvent_1">\n        <dc:Bounds x="179" y="259" width="36" height="36" />\n      </bpmndi:BPMNShape>\n      <bpmndi:BPMNShape id="Activity_0hs06x4_di" bpmnElement="Activity_0hs06x4" isExpanded="true">\n        <dc:Bounds x="280" y="210" width="1070" height="390" />\n      </bpmndi:BPMNShape>\n      <bpmndi:BPMNEdge id="Flow_1l59wnk_di" bpmnElement="Flow_1l59wnk">\n        <di:waypoint x="940" y="322" />\n        <di:waypoint x="960" y="322" />\n      </bpmndi:BPMNEdge>\n      <bpmndi:BPMNEdge id="Flow_1uqc2f6_di" bpmnElement="Flow_1uqc2f6">\n        <di:waypoint x="1240" y="322" />\n        <di:waypoint x="1272" y="322" />\n      </bpmndi:BPMNEdge>\n      <bpmndi:BPMNEdge id="Flow_1ohq7e9_di" bpmnElement="Flow_1ohq7e9">\n        <di:waypoint x="1060" y="322" />\n        <di:waypoint x="1082" y="322" />\n      </bpmndi:BPMNEdge>\n      <bpmndi:BPMNEdge id="Flow_00r3dvx_di" bpmnElement="Flow_00r3dvx">\n        <di:waypoint x="1118" y="322" />\n        <di:waypoint x="1140" y="322" />\n      </bpmndi:BPMNEdge>\n      <bpmndi:BPMNEdge id="Flow_03dqpsa_di" bpmnElement="Flow_03dqpsa">\n        <di:waypoint x="581" y="322" />\n        <di:waypoint x="630" y="322" />\n      </bpmndi:BPMNEdge>\n      <bpmndi:BPMNEdge id="Flow_0b3uli4_di" bpmnElement="Flow_0b3uli4">\n        <di:waypoint x="556" y="347" />\n        <di:waypoint x="556" y="420" />\n        <di:waypoint x="630" y="420" />\n      </bpmndi:BPMNEdge>\n      <bpmndi:BPMNEdge id="Flow_10co35r_di" bpmnElement="Flow_10co35r">\n        <di:waypoint x="730" y="322" />\n        <di:waypoint x="775" y="322" />\n      </bpmndi:BPMNEdge>\n      <bpmndi:BPMNEdge id="Flow_0iru6gy_di" bpmnElement="Flow_0iru6gy">\n        <di:waypoint x="730" y="420" />\n        <di:waypoint x="800" y="420" />\n        <di:waypoint x="800" y="347" />\n      </bpmndi:BPMNEdge>\n      <bpmndi:BPMNEdge id="Flow_010fgho_di" bpmnElement="Flow_010fgho">\n        <di:waypoint x="825" y="322" />\n        <di:waypoint x="840" y="322" />\n      </bpmndi:BPMNEdge>\n      <bpmndi:BPMNEdge id="Flow_09x26k9_di" bpmnElement="Flow_09x26k9">\n        <di:waypoint x="347" y="322" />\n        <di:waypoint x="380" y="322" />\n      </bpmndi:BPMNEdge>\n      <bpmndi:BPMNEdge id="Flow_0e1qs13_di" bpmnElement="Flow_0e1qs13">\n        <di:waypoint x="480" y="322" />\n        <di:waypoint x="531" y="322" />\n      </bpmndi:BPMNEdge>\n      <bpmndi:BPMNEdge id="Flow_0k2y56u_di" bpmnElement="Flow_0k2y56u">\n        <di:waypoint x="556" y="347" />\n        <di:waypoint x="556" y="520" />\n        <di:waypoint x="630" y="520" />\n      </bpmndi:BPMNEdge>\n      <bpmndi:BPMNEdge id="Flow_1imwypd_di" bpmnElement="Flow_1imwypd">\n        <di:waypoint x="730" y="520" />\n        <di:waypoint x="800" y="520" />\n        <di:waypoint x="800" y="347" />\n      </bpmndi:BPMNEdge>\n      <bpmndi:BPMNShape id="Gateway_0irp3dd_di" bpmnElement="Gateway_0irp3dd">\n        <dc:Bounds x="531" y="297" width="50" height="50" />\n      </bpmndi:BPMNShape>\n      <bpmndi:BPMNShape id="Gateway_1fk4sdd_di" bpmnElement="Gateway_1fk4sdd">\n        <dc:Bounds x="775" y="297" width="50" height="50" />\n      </bpmndi:BPMNShape>\n      <bpmndi:BPMNShape id="Event_10rrikb_di" bpmnElement="Event_10rrikb">\n        <dc:Bounds x="1272" y="304" width="36" height="36" />\n      </bpmndi:BPMNShape>\n      <bpmndi:BPMNShape id="Activity_0n3ico3_di" bpmnElement="Activity_0n3ico3">\n        <dc:Bounds x="630" y="282" width="100" height="80" />\n      </bpmndi:BPMNShape>\n      <bpmndi:BPMNShape id="Activity_0evaud6_di" bpmnElement="Activity_0evaud6">\n        <dc:Bounds x="630" y="380" width="100" height="80" />\n      </bpmndi:BPMNShape>\n      <bpmndi:BPMNShape id="Event_0nng048_di" bpmnElement="Event_0nng048">\n        <dc:Bounds x="311" y="304" width="36" height="36" />\n      </bpmndi:BPMNShape>\n      <bpmndi:BPMNShape id="Activity_16podmr_di" bpmnElement="Activity_16podmr">\n        <dc:Bounds x="380" y="282" width="100" height="80" />\n      </bpmndi:BPMNShape>\n      <bpmndi:BPMNShape id="Activity_1wwizjg_di" bpmnElement="Activity_1wwizjg">\n        <dc:Bounds x="630" y="480" width="100" height="80" />\n      </bpmndi:BPMNShape>\n      <bpmndi:BPMNShape id="Event_0nthkaz_di" bpmnElement="Event_0qrifrb">\n        <dc:Bounds x="1082" y="304" width="36" height="36" />\n        <bpmndi:BPMNLabel>\n          <dc:Bounds x="1061" y="347" width="79" height="27" />\n        </bpmndi:BPMNLabel>\n      </bpmndi:BPMNShape>\n      <bpmndi:BPMNShape id="Activity_1ns1o7b_di" bpmnElement="Activity_1ns1o7b">\n        <dc:Bounds x="960" y="282" width="100" height="80" />\n      </bpmndi:BPMNShape>\n      <bpmndi:BPMNShape id="Activity_0rt69rq_di" bpmnElement="Activity_0rt69rq" bioc:stroke="black" bioc:fill="white">\n        <dc:Bounds x="1140" y="282" width="100" height="80" />\n      </bpmndi:BPMNShape>\n      <bpmndi:BPMNShape id="Activity_0exo4cy_di" bpmnElement="Activity_0exo4cy">\n        <dc:Bounds x="840" y="282" width="100" height="80" />\n      </bpmndi:BPMNShape>\n      <bpmndi:BPMNShape id="Event_09x04tp_di" bpmnElement="Event_09x04tp">\n        <dc:Bounds x="1402" y="302" width="36" height="36" />\n      </bpmndi:BPMNShape>\n    </bpmndi:BPMNPlane>\n  </bpmndi:BPMNDiagram>\n</bpmn:definitions>',
}


@requests_mock.Mocker()
class GetBPMNViewTests(APITestCase):
    def test_get_bpmn_success(self, m):
        user = UserFactory.create()
        m.get(
            "https://camunda.example.com/engine-rest/process-definition/Adhoc_vergaderen:1:2ee97bc4-a370-11eb-970c-6a0042b17f4a/xml",
            json=BPMN_DATA,
        )
        self.client.force_authenticate(user=user)
        endpoint = reverse(
            "bpmn",
            kwargs={
                "process_definition_id": "Adhoc_vergaderen:1:2ee97bc4-a370-11eb-970c-6a0042b17f4a"
            },
        )
        response = self.client.get(endpoint)
        self.assertEqual(
            response.json(),
            {"id": BPMN_DATA["id"], "bpmn20Xml": BPMN_DATA["bpmn20_xml"]},
        )

    def test_get_bpmn_does_not_exist(self, m):
        user = UserFactory.create()
        m.get(
            "https://camunda.example.com/engine-rest/process-definition/Adhoc_vergaderen:1:2ee97bc4-a370-11eb-970c-6a0042b17f4a/xml",
            json={
                "type": "InvalidRequestException",
                "message": "No matching definition with id Adhoc_vergaderen:1:2ee97bc4-a370-11eb-970c-6a0042b17f4b",
            },
        )
        self.client.force_authenticate(user=user)
        endpoint = reverse(
            "bpmn",
            kwargs={
                "process_definition_id": "Adhoc_vergaderen:1:2ee97bc4-a370-11eb-970c-6a0042b17f4a"
            },
        )
        response = self.client.get(endpoint)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json(),
            {
                "type": "InvalidRequestException",
                "message": "No matching definition with id Adhoc_vergaderen:1:2ee97bc4-a370-11eb-970c-6a0042b17f4b",
            },
        )
