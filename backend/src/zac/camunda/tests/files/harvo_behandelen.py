HARVO_BEHANDELEN_BPMN = """<?xml version="1.0" encoding="UTF-8"?>
<bpmn:definitions xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL" xmlns:bpmndi="http://www.omg.org/spec/BPMN/20100524/DI" xmlns:dc="http://www.omg.org/spec/DD/20100524/DC" xmlns:camunda="http://camunda.org/schema/1.0/bpmn" xmlns:di="http://www.omg.org/spec/DD/20100524/DI" xmlns:bioc="http://bpmn.io/schema/bpmn/biocolor/1.0" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:color="http://www.omg.org/spec/BPMN/non-normative/color/1.0" xmlns:modeler="http://camunda.org/schema/modeler/1.0" id="Definitions_0ipgclx" targetNamespace="http://bpmn.io/schema/bpmn" exporter="Camunda Modeler" exporterVersion="4.11.1" modeler:executionPlatform="Camunda Platform" modeler:executionPlatformVersion="7.15.0">
  <bpmn:collaboration id="Collaboration_0srk2pw">
    <bpmn:participant id="Participant_0z4fwdy" name="HARVO" processRef="HARVO_behandelen" />
    <bpmn:group id="Group_0fltwtf" categoryValueRef="CategoryValue_1h5j2pl" />
    <bpmn:group id="Group_1225bi1" categoryValueRef="CategoryValue_19qqpvr" />
    <bpmn:group id="Group_06zq0hp" categoryValueRef="CategoryValue_10w1mc8" />
    <bpmn:group id="Group_0jba4vp" categoryValueRef="CategoryValue_0tr2p5y" />
    <bpmn:group id="Group_0zqfiyr" categoryValueRef="CategoryValue_0hjcpfp" />
  </bpmn:collaboration>
  <bpmn:process id="HARVO_behandelen" name="HARVO behandelen" isExecutable="true" camunda:versionTag="19-01-2022 MD">
    <bpmn:laneSet id="LaneSet_0rq6nu7">
      <bpmn:lane id="Lane_04ck49q" name="VGU">
        <bpmn:flowNodeRef>StartEvent_1</bpmn:flowNodeRef>
        <bpmn:flowNodeRef>Activity_0bkealj</bpmn:flowNodeRef>
        <bpmn:flowNodeRef>Gateway_0tzvt9v</bpmn:flowNodeRef>
        <bpmn:flowNodeRef>Activity_0fxwbso</bpmn:flowNodeRef>
        <bpmn:flowNodeRef>Activity_0grywz0</bpmn:flowNodeRef>
        <bpmn:flowNodeRef>Activity_017iqx5</bpmn:flowNodeRef>
        <bpmn:flowNodeRef>Activity_16vpuhy</bpmn:flowNodeRef>
        <bpmn:flowNodeRef>Activity_13icmu1</bpmn:flowNodeRef>
        <bpmn:flowNodeRef>Gateway_03jgpfx</bpmn:flowNodeRef>
        <bpmn:flowNodeRef>Activity_1ut09mg</bpmn:flowNodeRef>
        <bpmn:flowNodeRef>Activity_0s0z7jt</bpmn:flowNodeRef>
        <bpmn:flowNodeRef>Activity_1v4yshp</bpmn:flowNodeRef>
        <bpmn:flowNodeRef>Activity_17ccmxp</bpmn:flowNodeRef>
        <bpmn:flowNodeRef>Activity_08i2zn8</bpmn:flowNodeRef>
        <bpmn:flowNodeRef>Activity_1btxy4y</bpmn:flowNodeRef>
        <bpmn:flowNodeRef>Activity_1jk0div</bpmn:flowNodeRef>
        <bpmn:flowNodeRef>Gateway_1xdi8wj</bpmn:flowNodeRef>
        <bpmn:flowNodeRef>Activity_0qhhodi</bpmn:flowNodeRef>
        <bpmn:flowNodeRef>Activity_171qdm8</bpmn:flowNodeRef>
        <bpmn:flowNodeRef>Activity_0c29dnp</bpmn:flowNodeRef>
        <bpmn:flowNodeRef>Activity_1idplgj</bpmn:flowNodeRef>
        <bpmn:flowNodeRef>Activity_0p6s81e</bpmn:flowNodeRef>
        <bpmn:flowNodeRef>Activity_1p31jwi</bpmn:flowNodeRef>
        <bpmn:flowNodeRef>Activity_1kdm517</bpmn:flowNodeRef>
        <bpmn:flowNodeRef>Activity_0v3dnsk</bpmn:flowNodeRef>
        <bpmn:flowNodeRef>Activity_1o599km</bpmn:flowNodeRef>
        <bpmn:flowNodeRef>Activity_0m848pc</bpmn:flowNodeRef>
        <bpmn:flowNodeRef>Activity_0xy0pe7</bpmn:flowNodeRef>
        <bpmn:flowNodeRef>Activity_0sxjbys</bpmn:flowNodeRef>
        <bpmn:flowNodeRef>Event_0z0qrws</bpmn:flowNodeRef>
      </bpmn:lane>
    </bpmn:laneSet>
    <bpmn:startEvent id="StartEvent_1" name="Inkomend verzoek van adviseur">
      <bpmn:outgoing>Flow_1kjvxid</bpmn:outgoing>
    </bpmn:startEvent>
    <bpmn:sequenceFlow id="Flow_1kjvxid" sourceRef="StartEvent_1" targetRef="Activity_13icmu1" />
    <bpmn:sequenceFlow id="Flow_062y8jk" name="Nee" sourceRef="Gateway_1xdi8wj" targetRef="Activity_1btxy4y" />
    <bpmn:sequenceFlow id="Flow_0jobsq4" name="Ja" sourceRef="Gateway_1xdi8wj" targetRef="Activity_0c29dnp">
      <bpmn:conditionExpression xsi:type="bpmn:tFormalExpression">${approvalResult.prop("approved").boolValue()}</bpmn:conditionExpression>
    </bpmn:sequenceFlow>
    <bpmn:sequenceFlow id="Flow_1u4sa29" sourceRef="Activity_0qhhodi" targetRef="Activity_171qdm8" />
    <bpmn:sequenceFlow id="Flow_15ti8ru" sourceRef="Activity_1kdm517" targetRef="Activity_0p6s81e" />
    <bpmn:sequenceFlow id="Flow_0ttmpi0" sourceRef="Activity_0p6s81e" targetRef="Activity_1p31jwi" />
    <bpmn:sequenceFlow id="Flow_1cu7o4a" sourceRef="Activity_17ccmxp" targetRef="Activity_1btxy4y" />
    <bpmn:sequenceFlow id="Flow_10pumhr" sourceRef="Activity_1btxy4y" targetRef="Activity_08i2zn8" />
    <bpmn:sequenceFlow id="Flow_0unjhcl" sourceRef="Activity_13icmu1" targetRef="Gateway_03jgpfx" />
    <bpmn:sequenceFlow id="Flow_1bk1ygt" sourceRef="Activity_16vpuhy" targetRef="Activity_017iqx5" />
    <bpmn:userTask id="Activity_0bkealj" name="Inhoudelijk voorbereiden (= checkvragen)" camunda:formKey="checkvragenVoorbereiding" camunda:assignee="${nameProp.stringValue()}">
      <bpmn:extensionElements>
        <camunda:formData>
          <camunda:formField id="checkContract" label="Is er een fiscale check gedaan op het contract?" type="enum">
            <camunda:value id="Ja" name="Ja" />
            <camunda:value id="Nee" name="Nee" />
          </camunda:formField>
          <camunda:formField id="checkIntegriteit" label="Is de integriteit van de wederpartij getoetst?" type="enum">
            <camunda:value id="Ja" name="Ja" />
            <camunda:value id="Nee" name="Nee" />
          </camunda:formField>
          <camunda:formField id="checkBibob" label="Is er een Bibob-toets noodzakelijk of gewenst?" type="enum">
            <camunda:value id="Ja" name="Ja" />
            <camunda:value id="Nee" name="Nee" />
          </camunda:formField>
          <camunda:formField id="checkKrediet" label="Is de kredietwaardigheid van de wederpartij getoetst?" type="enum">
            <camunda:value id="Ja" name="Ja" />
            <camunda:value id="Nee" name="Nee" />
          </camunda:formField>
          <camunda:formField id="checkJuridisch" label="Is er een juridische check geweest?" type="enum">
            <camunda:value id="Ja" name="Ja" />
            <camunda:value id="Nee" name="Nee" />
          </camunda:formField>
        </camunda:formData>
      </bpmn:extensionElements>
      <bpmn:incoming>Flow_1d5b446</bpmn:incoming>
      <bpmn:outgoing>Flow_1ihju91</bpmn:outgoing>
    </bpmn:userTask>
    <bpmn:sequenceFlow id="Flow_1d5b446" sourceRef="Gateway_0tzvt9v" targetRef="Activity_0bkealj" />
    <bpmn:parallelGateway id="Gateway_0tzvt9v">
      <bpmn:incoming>Flow_0lam00p</bpmn:incoming>
      <bpmn:incoming>Flow_00va23k</bpmn:incoming>
      <bpmn:incoming>Flow_1o2qyoy</bpmn:incoming>
      <bpmn:incoming>Flow_00vrkkv</bpmn:incoming>
      <bpmn:outgoing>Flow_1d5b446</bpmn:outgoing>
    </bpmn:parallelGateway>
    <bpmn:serviceTask id="Activity_0fxwbso" name="Zet eigenschap" camunda:type="external" camunda:topic="zaak-eigenschap">
      <bpmn:incoming>Flow_17s2jk4</bpmn:incoming>
      <bpmn:outgoing>Flow_0lam00p</bpmn:outgoing>
      <bpmn:multiInstanceLoopCharacteristics camunda:collection="${eigenschappen.elements()}" camunda:elementVariable="eigenschap" />
    </bpmn:serviceTask>
    <bpmn:sequenceFlow id="Flow_17s2jk4" sourceRef="Gateway_03jgpfx" targetRef="Activity_0fxwbso" />
    <bpmn:sequenceFlow id="Flow_0lam00p" sourceRef="Activity_0fxwbso" targetRef="Gateway_0tzvt9v" />
    <bpmn:serviceTask id="Activity_0grywz0" name="Zet OO" camunda:type="external" camunda:topic="zaak-rol">
      <bpmn:extensionElements>
        <camunda:inputOutput>
          <camunda:inputParameter name="omschrijving">Organisatieonderdeel</camunda:inputParameter>
          <camunda:inputParameter name="betrokkene">${Organisatieonderdeel}</camunda:inputParameter>
        </camunda:inputOutput>
      </bpmn:extensionElements>
      <bpmn:incoming>Flow_0ffwvxf</bpmn:incoming>
      <bpmn:outgoing>Flow_1o2qyoy</bpmn:outgoing>
    </bpmn:serviceTask>
    <bpmn:serviceTask id="Activity_017iqx5" name="Zet Behandelaar" camunda:type="external" camunda:topic="zaak-rol">
      <bpmn:extensionElements>
        <camunda:inputOutput>
          <camunda:inputParameter name="omschrijving">Adviseur portefeuillemanager</camunda:inputParameter>
          <camunda:inputParameter name="betrokkene">
            <camunda:script scriptFormat="javascript">var betrokkeneData = {
                  "betrokkeneType": "medewerker",
                  "roltoelichting": "Adviseur portefeuillemanager",
                  "betrokkeneIdentificatie": {
                    "identificatie": nameProp.stringValue()
                    }
                  };
            
                  var encoded = JSON.stringify(betrokkeneData);
            
                  processVar = S(encoded);</camunda:script>
          </camunda:inputParameter>
        </camunda:inputOutput>
      </bpmn:extensionElements>
      <bpmn:incoming>Flow_1bk1ygt</bpmn:incoming>
      <bpmn:outgoing>Flow_00va23k</bpmn:outgoing>
    </bpmn:serviceTask>
    <bpmn:serviceTask id="Activity_16vpuhy" name="Ophalen username behandelaar met mailadres" camunda:type="external" camunda:topic="fetch-users-details">
      <bpmn:extensionElements>
        <camunda:inputOutput>
          <camunda:outputParameter name="nameProp">${userData.elements().get(0).prop("username")}</camunda:outputParameter>
        </camunda:inputOutput>
      </bpmn:extensionElements>
      <bpmn:incoming>Flow_1qbom66</bpmn:incoming>
      <bpmn:outgoing>Flow_1bk1ygt</bpmn:outgoing>
    </bpmn:serviceTask>
    <bpmn:serviceTask id="Activity_13icmu1" name="Aanmaken zaak" camunda:type="external" camunda:topic="initialize-zaak">
      <bpmn:extensionElements>
        <camunda:inputOutput>
          <camunda:inputParameter name="organisatieRSIN">002220647</camunda:inputParameter>
          <camunda:inputParameter name="catalogusDomein">UTRE</camunda:inputParameter>
          <camunda:inputParameter name="zaaktypeIdentificatie">ZAAKTYPE-2021-0000000008</camunda:inputParameter>
        </camunda:inputOutput>
      </bpmn:extensionElements>
      <bpmn:incoming>Flow_1kjvxid</bpmn:incoming>
      <bpmn:outgoing>Flow_0unjhcl</bpmn:outgoing>
    </bpmn:serviceTask>
    <bpmn:parallelGateway id="Gateway_03jgpfx">
      <bpmn:incoming>Flow_0unjhcl</bpmn:incoming>
      <bpmn:outgoing>Flow_17s2jk4</bpmn:outgoing>
      <bpmn:outgoing>Flow_1qbom66</bpmn:outgoing>
      <bpmn:outgoing>Flow_0ffwvxf</bpmn:outgoing>
      <bpmn:outgoing>Flow_1v3hdfl</bpmn:outgoing>
    </bpmn:parallelGateway>
    <bpmn:sequenceFlow id="Flow_0s72343" sourceRef="Activity_1v4yshp" targetRef="Activity_1jk0div" />
    <bpmn:sequenceFlow id="Flow_0djfsgi" sourceRef="Activity_171qdm8" targetRef="Activity_1idplgj" />
    <bpmn:sequenceFlow id="Flow_1qbom66" sourceRef="Gateway_03jgpfx" targetRef="Activity_16vpuhy" />
    <bpmn:sequenceFlow id="Flow_00va23k" sourceRef="Activity_017iqx5" targetRef="Gateway_0tzvt9v" />
    <bpmn:sequenceFlow id="Flow_0ffwvxf" sourceRef="Gateway_03jgpfx" targetRef="Activity_0grywz0" />
    <bpmn:sequenceFlow id="Flow_1o2qyoy" sourceRef="Activity_0grywz0" targetRef="Gateway_0tzvt9v" />
    <bpmn:sequenceFlow id="Flow_10zdg6h" sourceRef="Activity_0c29dnp" targetRef="Activity_0qhhodi" />
    <bpmn:sequenceFlow id="Flow_19igvbl" sourceRef="Activity_08i2zn8" targetRef="Activity_1o599km" />
    <bpmn:sequenceFlow id="Flow_1ixtmvy" sourceRef="Activity_1jk0div" targetRef="Activity_17ccmxp" />
    <bpmn:sequenceFlow id="Flow_1ihju91" sourceRef="Activity_0bkealj" targetRef="Activity_0m848pc" />
    <bpmn:sequenceFlow id="Flow_1hj6gf1" sourceRef="Activity_0m848pc" targetRef="Activity_0s0z7jt" />
    <bpmn:serviceTask id="Activity_1ut09mg" name="Relateren bijlage(n)" camunda:type="external" camunda:topic="zaak-relate-document">
      <bpmn:incoming>Flow_1v3hdfl</bpmn:incoming>
      <bpmn:outgoing>Flow_00vrkkv</bpmn:outgoing>
      <bpmn:multiInstanceLoopCharacteristics camunda:collection="${bijlagen.elements()}" camunda:elementVariable="informatieobject" />
    </bpmn:serviceTask>
    <bpmn:sequenceFlow id="Flow_1v3hdfl" sourceRef="Gateway_03jgpfx" targetRef="Activity_1ut09mg" />
    <bpmn:sequenceFlow id="Flow_00vrkkv" sourceRef="Activity_1ut09mg" targetRef="Gateway_0tzvt9v" />
    <bpmn:userTask id="Activity_0s0z7jt" name="Aanvullen routing informatie" camunda:formKey="Routinginformatie" camunda:assignee="${nameProp.stringValue()}">
      <bpmn:extensionElements>
        <camunda:formData>
          <camunda:formField id="dekking" label="Dekking" type="enum">
            <camunda:value id="IO" name="IO" />
            <camunda:value id="WBP" name="WBP" />
            <camunda:value id="KP" name="KP" />
          </camunda:formField>
          <camunda:formField id="bedragExBtw" label="Bedrag ex. BTW" type="string" />
          <camunda:formField id="typeVerhuring " label="Type verhuring" type="enum">
            <camunda:value id="Kostprijs" name="Kostprijs" />
            <camunda:value id="Marktconform" name="Marktconform" />
            <camunda:value id="Afwijking" name="Afwijking van beleid" />
            <camunda:value id="Nvt" name="Niet van toepassing" />
          </camunda:formField>
          <camunda:formField id="btwPlichtig" label="BTW plichtig?" type="enum">
            <camunda:value id="Ja" name="Ja" />
            <camunda:value id="Nee" name="Nee" />
          </camunda:formField>
          <camunda:formField id="toelichtingType" label="Toelichting type" type="string" />
          <camunda:formField id="financieleGevolgen" label="Financiële gevolgen" type="string" />
          <camunda:formField id="bedragInclBtw" label="Bedrag incl. BTW" type="string" />
          <camunda:formField id="toelichtingaanvraag" label="Toelichting op routingsformulier" type="string" />
        </camunda:formData>
        <camunda:taskListener event="complete">
          <camunda:script scriptFormat="javascript">var formService = task.execution.getProcessEngineServices().getFormService();
var taskFormData = formService.getTaskFormData(task.getId());
var fields = taskFormData.getFormFields();
var eigenschappen = new Array(fields.length);

for(var i=0; i&lt;fields.length;i++){
  var waarde = task.execution.getVariable(fields[i].getId());
  eigenschappen[i] = {
    "naam": fields[i].getLabel(),
    "waarde": waarde
  };
};

var eigenschappen = JSON.stringify(eigenschappen);
task.execution.setVariable('routingFormEigenschappen', S(eigenschappen));</camunda:script>
        </camunda:taskListener>
      </bpmn:extensionElements>
      <bpmn:incoming>Flow_1hj6gf1</bpmn:incoming>
      <bpmn:outgoing>Flow_1rie6co</bpmn:outgoing>
    </bpmn:userTask>
    <bpmn:sequenceFlow id="Flow_1rie6co" sourceRef="Activity_0s0z7jt" targetRef="Activity_1v4yshp" />
    <bpmn:callActivity id="Activity_1v4yshp" name="Starten bijdragezaak Routing" calledElement="Routingformulier_UVO">
      <bpmn:extensionElements>
        <camunda:in source="zaakUrl" target="hoofdZaakUrl" />
        <camunda:in source="bptlAppId" target="bptlAppId" />
        <camunda:in sourceExpression="ja" target="bijdragezaak" />
        <camunda:in source="emailaddresses" target="emailaddresses" />
        <camunda:in source="Organisatieonderdeel" target="Organisatieonderdeel" />
        <camunda:in source="eigenschappen" target="eigenschappen" />
        <camunda:in sourceExpression="ZAAKTYPE-2021-0000000001" target="zaaktypeIdentificatie" />
        <camunda:in sourceExpression="UTRE" target="catalogusDomein" />
        <camunda:in sourceExpression="002220647" target="organisatieRSIN" />
        <camunda:in source="routingFormEigenschappen" target="routingFormEigenschappen" />
        <camunda:in source="nameProp" target="nameProp" />
        <camunda:in source="toelichtingaanvraag" target="toelichtingaanvraag" />
        <camunda:in source="zaakDetails" target="zaakDetails" />
      </bpmn:extensionElements>
      <bpmn:incoming>Flow_1rie6co</bpmn:incoming>
      <bpmn:outgoing>Flow_0s72343</bpmn:outgoing>
    </bpmn:callActivity>
    <bpmn:userTask id="Activity_17ccmxp" name="Ondertekenen met ValidSign" camunda:assignee="${nameProp.stringValue()}">
      <bpmn:incoming>Flow_1ixtmvy</bpmn:incoming>
      <bpmn:outgoing>Flow_1cu7o4a</bpmn:outgoing>
    </bpmn:userTask>
    <bpmn:userTask id="Activity_08i2zn8" name="Accorderings vraag hoofdgebied econoom configureren" camunda:formKey="zac:configureApprovalRequest" camunda:assignee="${nameProp.stringValue()}">
      <bpmn:extensionElements>
        <camunda:taskListener expression="${execution.setVariable(&#39;kownslAkkoordUsersList&#39;, execution.getVariable(&#39;kownslUsersList&#39;))}" event="complete" />
      </bpmn:extensionElements>
      <bpmn:incoming>Flow_10pumhr</bpmn:incoming>
      <bpmn:outgoing>Flow_19igvbl</bpmn:outgoing>
    </bpmn:userTask>
    <bpmn:userTask id="Activity_1btxy4y" name="Opstellen advies mandaatbesluit" camunda:assignee="${nameProp.stringValue()}">
      <bpmn:incoming>Flow_062y8jk</bpmn:incoming>
      <bpmn:incoming>Flow_1cu7o4a</bpmn:incoming>
      <bpmn:outgoing>Flow_10pumhr</bpmn:outgoing>
    </bpmn:userTask>
    <bpmn:serviceTask id="Activity_1jk0div" name="Status wijzigen" camunda:type="external" camunda:topic="set-status">
      <bpmn:extensionElements>
        <camunda:inputOutput>
          <camunda:inputParameter name="statusVolgnummer">3</camunda:inputParameter>
        </camunda:inputOutput>
      </bpmn:extensionElements>
      <bpmn:incoming>Flow_0s72343</bpmn:incoming>
      <bpmn:outgoing>Flow_1ixtmvy</bpmn:outgoing>
    </bpmn:serviceTask>
    <bpmn:exclusiveGateway id="Gateway_1xdi8wj" name="Akkoord?" default="Flow_062y8jk">
      <bpmn:incoming>Flow_01tpx07</bpmn:incoming>
      <bpmn:outgoing>Flow_062y8jk</bpmn:outgoing>
      <bpmn:outgoing>Flow_0jobsq4</bpmn:outgoing>
    </bpmn:exclusiveGateway>
    <bpmn:userTask id="Activity_0qhhodi" name="Toevoegen notariële akte en transport" camunda:assignee="${nameProp.stringValue()}">
      <bpmn:incoming>Flow_10zdg6h</bpmn:incoming>
      <bpmn:outgoing>Flow_1u4sa29</bpmn:outgoing>
    </bpmn:userTask>
    <bpmn:userTask id="Activity_171qdm8" name="Invoeren contractgegevens" camunda:formKey="" camunda:assignee="${nameProp.stringValue()}">
      <bpmn:extensionElements>
        <camunda:formData>
          <camunda:formField id="Startdatum" label="Startdatum" type="string" />
          <camunda:formField id="Einddatum" label="Einddatum" type="string" />
        </camunda:formData>
        <camunda:taskListener event="complete">
          <camunda:script scriptFormat="javascript">var formService = task.execution.getProcessEngineServices().getFormService();
var taskFormData = formService.getTaskFormData(task.getId());
var fields = taskFormData.getFormFields();
var eigenschappen = new Array(fields.length);

for(var i=0; i&lt;fields.length;i++){
  var waarde = task.execution.getVariable(fields[i].getId());
  eigenschappen[i] = {
    "naam": fields[i].getLabel(),
    "waarde": waarde
  };
};

var eigenschappen = JSON.stringify(eigenschappen);
task.execution.setVariable('contractEigenschappen', S(eigenschappen));</camunda:script>
        </camunda:taskListener>
      </bpmn:extensionElements>
      <bpmn:incoming>Flow_1u4sa29</bpmn:incoming>
      <bpmn:outgoing>Flow_0djfsgi</bpmn:outgoing>
    </bpmn:userTask>
    <bpmn:serviceTask id="Activity_0c29dnp" name="Status wijzigen" camunda:type="external" camunda:topic="set-status">
      <bpmn:extensionElements>
        <camunda:inputOutput>
          <camunda:inputParameter name="statusVolgnummer">4</camunda:inputParameter>
        </camunda:inputOutput>
      </bpmn:extensionElements>
      <bpmn:incoming>Flow_0jobsq4</bpmn:incoming>
      <bpmn:outgoing>Flow_10zdg6h</bpmn:outgoing>
    </bpmn:serviceTask>
    <bpmn:serviceTask id="Activity_1idplgj" name="Zet contract eigenschappen" camunda:type="external" camunda:topic="zaak-eigenschap">
      <bpmn:incoming>Flow_0djfsgi</bpmn:incoming>
      <bpmn:outgoing>Flow_1wnlyxd</bpmn:outgoing>
      <bpmn:multiInstanceLoopCharacteristics camunda:collection="${contractEigenschappen.elements()}" camunda:elementVariable="eigenschap" />
    </bpmn:serviceTask>
    <bpmn:sequenceFlow id="Flow_1wnlyxd" sourceRef="Activity_1idplgj" targetRef="Activity_1kdm517" />
    <bpmn:userTask id="Activity_0p6s81e" name="Versturen HARVO" camunda:assignee="${nameProp.stringValue()}">
      <bpmn:incoming>Flow_15ti8ru</bpmn:incoming>
      <bpmn:outgoing>Flow_0ttmpi0</bpmn:outgoing>
    </bpmn:userTask>
    <bpmn:userTask id="Activity_1p31jwi" name="Contract activeren in SAP (=check)" camunda:assignee="${nameProp.stringValue()}">
      <bpmn:extensionElements>
        <camunda:formData>
          <camunda:formField id="checkSAP" label="Het contract is geactiveerd in SAP" type="enum">
            <camunda:value id="Ja" name="Ja" />
          </camunda:formField>
        </camunda:formData>
      </bpmn:extensionElements>
      <bpmn:incoming>Flow_0ttmpi0</bpmn:incoming>
      <bpmn:outgoing>Flow_1098s5u</bpmn:outgoing>
    </bpmn:userTask>
    <bpmn:userTask id="Activity_1kdm517" name="Toevoegen eerste huurfactuur aan zaak" camunda:assignee="${nameProp.stringValue()}">
      <bpmn:incoming>Flow_1wnlyxd</bpmn:incoming>
      <bpmn:outgoing>Flow_15ti8ru</bpmn:outgoing>
    </bpmn:userTask>
    <bpmn:subProcess id="Activity_0v3dnsk" name="Annuleren" triggeredByEvent="true">
      <bpmn:serviceTask id="Activity_0kzkn15" name="Resultaat zetten en sluiten zaak" camunda:type="external" camunda:topic="close-zaak">
        <bpmn:extensionElements>
          <camunda:inputOutput>
            <camunda:inputParameter name="omschrijving">Ingetrokken</camunda:inputParameter>
          </camunda:inputOutput>
        </bpmn:extensionElements>
        <bpmn:incoming>Flow_0sw8gv9</bpmn:incoming>
        <bpmn:outgoing>Flow_1dv655f</bpmn:outgoing>
      </bpmn:serviceTask>
      <bpmn:startEvent id="Event_00viiiy" name="Annuleer behandeling">
        <bpmn:outgoing>Flow_0sw8gv9</bpmn:outgoing>
        <bpmn:messageEventDefinition id="MessageEventDefinition_1yccv7b" messageRef="Message_1v396f7" />
      </bpmn:startEvent>
      <bpmn:endEvent id="Event_1t8hxd8" name="Zaak afgesloten">
        <bpmn:incoming>Flow_1dv655f</bpmn:incoming>
      </bpmn:endEvent>
      <bpmn:sequenceFlow id="Flow_1dv655f" sourceRef="Activity_0kzkn15" targetRef="Event_1t8hxd8" />
      <bpmn:sequenceFlow id="Flow_0sw8gv9" sourceRef="Event_00viiiy" targetRef="Activity_0kzkn15" />
    </bpmn:subProcess>
    <bpmn:callActivity id="Activity_1o599km" name="Accorderen door hoofdgebied econoom" calledElement="accorderen">
      <bpmn:extensionElements>
        <camunda:in source="zaakUrl" target="zaakUrl" />
        <camunda:in source="bptlAppId" target="bptlAppId" />
        <camunda:in source="kownslUsers" target="kownslUsers" />
        <camunda:in source="kownslReviewRequestId" target="kownslReviewRequestId" />
        <camunda:out source="approvalResult" target="approvalResult" />
        <camunda:in source="kownslFrontendUrl" target="doReviewUrl" />
        <camunda:in source="kownslDocuments" target="kownslDocuments" />
        <camunda:in source="emailNotificationList" target="emailNotificationList" />
      </bpmn:extensionElements>
      <bpmn:incoming>Flow_19igvbl</bpmn:incoming>
      <bpmn:outgoing>Flow_01tpx07</bpmn:outgoing>
      <bpmn:multiInstanceLoopCharacteristics isSequential="true" camunda:collection="${kownslAkkoordUsersList.elements()}" camunda:elementVariable="kownslUsers">
        <bpmn:completionCondition xsi:type="bpmn:tFormalExpression">${approvalResult.prop("approved").boolValue() == false}</bpmn:completionCondition>
      </bpmn:multiInstanceLoopCharacteristics>
    </bpmn:callActivity>
    <bpmn:sequenceFlow id="Flow_01tpx07" sourceRef="Activity_1o599km" targetRef="Gateway_1xdi8wj" />
    <bpmn:serviceTask id="Activity_0m848pc" name="Status wijzigen" camunda:type="external" camunda:topic="set-status">
      <bpmn:extensionElements>
        <camunda:inputOutput>
          <camunda:inputParameter name="statusVolgnummer">2</camunda:inputParameter>
        </camunda:inputOutput>
      </bpmn:extensionElements>
      <bpmn:incoming>Flow_1ihju91</bpmn:incoming>
      <bpmn:outgoing>Flow_1hj6gf1</bpmn:outgoing>
    </bpmn:serviceTask>
    <bpmn:subProcess id="Activity_0xy0pe7" name="Adviseren" triggeredByEvent="true">
      <bpmn:callActivity id="Activity_1qh4p7f" name="Adviseren" calledElement="adviseren">
        <bpmn:extensionElements>
          <camunda:in source="zaakUrl" target="zaakUrl" />
          <camunda:in source="bptlAppId" target="bptlAppId" />
          <camunda:in source="kownslUsers" target="kownslUsers" />
          <camunda:in source="kownslReviewRequestId" target="kownslReviewRequestId" />
          <camunda:in source="kownslFrontendUrl" target="doReviewUrl" />
          <camunda:in source="kownslDocuments" target="kownslDocuments" />
          <camunda:in source="emailNotificationList" target="emailNotificationList" />
        </bpmn:extensionElements>
        <bpmn:incoming>Flow_0kb0k6s</bpmn:incoming>
        <bpmn:outgoing>Flow_1mbl4qw</bpmn:outgoing>
        <bpmn:multiInstanceLoopCharacteristics isSequential="true" camunda:collection="${kownslAdviesUsersList.elements()}" camunda:elementVariable="kownslUsers" />
      </bpmn:callActivity>
      <bpmn:userTask id="Activity_1lveufy" name="Adviesvraag configureren" camunda:formKey="zac:configureAdviceRequest">
        <bpmn:extensionElements>
          <camunda:taskListener expression="${execution.setVariable(&#39;kownslAdviesUsersList&#39;, execution.getVariable(&#39;kownslUsersList&#39;))}" event="complete" />
        </bpmn:extensionElements>
        <bpmn:incoming>Flow_1k932lk</bpmn:incoming>
        <bpmn:outgoing>Flow_0kb0k6s</bpmn:outgoing>
      </bpmn:userTask>
      <bpmn:endEvent id="Event_1rr3qjp" name="Advies gegeven">
        <bpmn:incoming>Flow_1mbl4qw</bpmn:incoming>
      </bpmn:endEvent>
      <bpmn:sequenceFlow id="Flow_0kb0k6s" sourceRef="Activity_1lveufy" targetRef="Activity_1qh4p7f" />
      <bpmn:sequenceFlow id="Flow_1k932lk" sourceRef="Event_1r89eoq" targetRef="Activity_1lveufy" />
      <bpmn:sequenceFlow id="Flow_1mbl4qw" sourceRef="Activity_1qh4p7f" targetRef="Event_1rr3qjp" />
      <bpmn:startEvent id="Event_1r89eoq" name="Advies vragen" isInterrupting="false">
        <bpmn:outgoing>Flow_1k932lk</bpmn:outgoing>
        <bpmn:messageEventDefinition id="MessageEventDefinition_1jugo87" messageRef="Message_0kuyv0q" />
      </bpmn:startEvent>
    </bpmn:subProcess>
    <bpmn:sequenceFlow id="Flow_1098s5u" sourceRef="Activity_1p31jwi" targetRef="Event_0z0qrws" />
    <bpmn:serviceTask id="Activity_0sxjbys" name="Resultaat zetten en sluiten zaak" camunda:type="external" camunda:topic="close-zaak">
      <bpmn:extensionElements>
        <camunda:inputOutput>
          <camunda:inputParameter name="omschrijving">Afgehandeld</camunda:inputParameter>
        </camunda:inputOutput>
      </bpmn:extensionElements>
    </bpmn:serviceTask>
    <bpmn:endEvent id="Event_0z0qrws" name="Starten proces Beheren vastgoedobject">
      <bpmn:extensionElements>
        <camunda:inputOutput>
          <camunda:inputParameter name="bijdrageAard">vervolg</camunda:inputParameter>
          <camunda:inputParameter name="hoofdZaakUrl">${zaakUrl}</camunda:inputParameter>
          <camunda:inputParameter name="subprocessDefinition">Vastgoedobject-beheren</camunda:inputParameter>
        </camunda:inputOutput>
      </bpmn:extensionElements>
      <bpmn:incoming>Flow_1098s5u</bpmn:incoming>
      <bpmn:messageEventDefinition id="MessageEventDefinition_0lxc3gt" camunda:type="external" camunda:topic="start-process" />
    </bpmn:endEvent>
    <bpmn:textAnnotation id="TextAnnotation_0k5q26p">
      <bpmn:text>Terugzetten na indicatieGebruiksrecht fix</bpmn:text>
    </bpmn:textAnnotation>
    <bpmn:association id="Association_1q343ai" sourceRef="Activity_0sxjbys" targetRef="TextAnnotation_0k5q26p" />
  </bpmn:process>
  <bpmn:category id="Category_10g6zlp">
    <bpmn:categoryValue id="CategoryValue_1h5j2pl" value="Afstemmen en onderhandelen" />
  </bpmn:category>
  <bpmn:category id="Category_0rjf8d2">
    <bpmn:categoryValue id="CategoryValue_19qqpvr" value="Ondertekenen" />
  </bpmn:category>
  <bpmn:category id="Category_00cqp70">
    <bpmn:categoryValue id="CategoryValue_10w1mc8" value="Notarieel inschrijven" />
  </bpmn:category>
  <bpmn:category id="Category_1d980dk">
    <bpmn:categoryValue id="CategoryValue_0tr2p5y" value="Versturen HARVO" />
  </bpmn:category>
  <bpmn:category id="Category_0kmiwtn">
    <bpmn:categoryValue id="CategoryValue_0hjcpfp" value="Inhoudelijk behandelen" />
  </bpmn:category>
  <bpmn:message id="Message_1v396f7" name="Annuleer behandeling" />
  <bpmn:message id="Message_0kuyv0q" name="Advies vragen" />
  <bpmn:message id="Message_1asd38g" name="_some_secret_message" />
  <bpmndi:BPMNDiagram id="BPMNDiagram_1">
    <bpmndi:BPMNPlane id="BPMNPlane_1" bpmnElement="Collaboration_0srk2pw">
      <bpmndi:BPMNShape id="Participant_0z4fwdy_di" bpmnElement="Participant_0z4fwdy" isHorizontal="true">
        <dc:Bounds x="129" y="80" width="3211" height="640" />
      </bpmndi:BPMNShape>
      <bpmndi:BPMNShape id="Lane_04ck49q_di" bpmnElement="Lane_04ck49q" isHorizontal="true">
        <dc:Bounds x="159" y="80" width="3181" height="640" />
      </bpmndi:BPMNShape>
      <bpmndi:BPMNEdge id="Flow_1098s5u_di" bpmnElement="Flow_1098s5u">
        <di:waypoint x="2830" y="380" />
        <di:waypoint x="3122" y="380" />
      </bpmndi:BPMNEdge>
      <bpmndi:BPMNEdge id="Flow_01tpx07_di" bpmnElement="Flow_01tpx07">
        <di:waypoint x="1830" y="380" />
        <di:waypoint x="1865" y="380" />
      </bpmndi:BPMNEdge>
      <bpmndi:BPMNEdge id="Flow_1wnlyxd_di" bpmnElement="Flow_1wnlyxd">
        <di:waypoint x="2420" y="380" />
        <di:waypoint x="2460" y="380" />
      </bpmndi:BPMNEdge>
      <bpmndi:BPMNEdge id="Flow_1rie6co_di" bpmnElement="Flow_1rie6co">
        <di:waypoint x="1050" y="380" />
        <di:waypoint x="1070" y="380" />
      </bpmndi:BPMNEdge>
      <bpmndi:BPMNEdge id="Flow_00vrkkv_di" bpmnElement="Flow_00vrkkv">
        <di:waypoint x="580" y="575" />
        <di:waypoint x="640" y="575" />
        <di:waypoint x="640" y="405" />
      </bpmndi:BPMNEdge>
      <bpmndi:BPMNEdge id="Flow_1v3hdfl_di" bpmnElement="Flow_1v3hdfl">
        <di:waypoint x="400" y="405" />
        <di:waypoint x="400" y="575" />
        <di:waypoint x="480" y="575" />
      </bpmndi:BPMNEdge>
      <bpmndi:BPMNEdge id="Flow_1hj6gf1_di" bpmnElement="Flow_1hj6gf1">
        <di:waypoint x="900" y="380" />
        <di:waypoint x="950" y="380" />
      </bpmndi:BPMNEdge>
      <bpmndi:BPMNEdge id="Flow_1ihju91_di" bpmnElement="Flow_1ihju91">
        <di:waypoint x="790" y="380" />
        <di:waypoint x="800" y="380" />
      </bpmndi:BPMNEdge>
      <bpmndi:BPMNEdge id="Flow_1ixtmvy_di" bpmnElement="Flow_1ixtmvy">
        <di:waypoint x="1320" y="380" />
        <di:waypoint x="1350" y="380" />
      </bpmndi:BPMNEdge>
      <bpmndi:BPMNEdge id="Flow_19igvbl_di" bpmnElement="Flow_19igvbl">
        <di:waypoint x="1710" y="380" />
        <di:waypoint x="1730" y="380" />
      </bpmndi:BPMNEdge>
      <bpmndi:BPMNEdge id="Flow_10zdg6h_di" bpmnElement="Flow_10zdg6h">
        <di:waypoint x="2050" y="380" />
        <di:waypoint x="2090" y="380" />
      </bpmndi:BPMNEdge>
      <bpmndi:BPMNEdge id="Flow_1o2qyoy_di" bpmnElement="Flow_1o2qyoy">
        <di:waypoint x="580" y="480" />
        <di:waypoint x="640" y="480" />
        <di:waypoint x="640" y="405" />
      </bpmndi:BPMNEdge>
      <bpmndi:BPMNEdge id="Flow_0ffwvxf_di" bpmnElement="Flow_0ffwvxf">
        <di:waypoint x="400" y="405" />
        <di:waypoint x="400" y="480" />
        <di:waypoint x="480" y="480" />
      </bpmndi:BPMNEdge>
      <bpmndi:BPMNEdge id="Flow_00va23k_di" bpmnElement="Flow_00va23k">
        <di:waypoint x="630" y="290" />
        <di:waypoint x="640" y="290" />
        <di:waypoint x="640" y="355" />
      </bpmndi:BPMNEdge>
      <bpmndi:BPMNEdge id="Flow_1qbom66_di" bpmnElement="Flow_1qbom66">
        <di:waypoint x="400" y="355" />
        <di:waypoint x="400" y="290" />
        <di:waypoint x="420" y="290" />
      </bpmndi:BPMNEdge>
      <bpmndi:BPMNEdge id="Flow_0djfsgi_di" bpmnElement="Flow_0djfsgi">
        <di:waypoint x="2300" y="380" />
        <di:waypoint x="2320" y="380" />
      </bpmndi:BPMNEdge>
      <bpmndi:BPMNEdge id="Flow_0s72343_di" bpmnElement="Flow_0s72343">
        <di:waypoint x="1170" y="380" />
        <di:waypoint x="1220" y="380" />
      </bpmndi:BPMNEdge>
      <bpmndi:BPMNEdge id="Flow_0lam00p_di" bpmnElement="Flow_0lam00p">
        <di:waypoint x="580" y="380" />
        <di:waypoint x="615" y="380" />
      </bpmndi:BPMNEdge>
      <bpmndi:BPMNEdge id="Flow_17s2jk4_di" bpmnElement="Flow_17s2jk4">
        <di:waypoint x="425" y="380" />
        <di:waypoint x="480" y="380" />
      </bpmndi:BPMNEdge>
      <bpmndi:BPMNEdge id="Flow_1d5b446_di" bpmnElement="Flow_1d5b446">
        <di:waypoint x="665" y="380" />
        <di:waypoint x="690" y="380" />
      </bpmndi:BPMNEdge>
      <bpmndi:BPMNEdge id="Flow_1bk1ygt_di" bpmnElement="Flow_1bk1ygt">
        <di:waypoint x="520" y="290" />
        <di:waypoint x="530" y="290" />
      </bpmndi:BPMNEdge>
      <bpmndi:BPMNEdge id="Flow_0unjhcl_di" bpmnElement="Flow_0unjhcl">
        <di:waypoint x="370" y="380" />
        <di:waypoint x="375" y="380" />
      </bpmndi:BPMNEdge>
      <bpmndi:BPMNEdge id="Flow_10pumhr_di" bpmnElement="Flow_10pumhr">
        <di:waypoint x="1580" y="380" />
        <di:waypoint x="1610" y="380" />
      </bpmndi:BPMNEdge>
      <bpmndi:BPMNEdge id="Flow_1cu7o4a_di" bpmnElement="Flow_1cu7o4a">
        <di:waypoint x="1450" y="380" />
        <di:waypoint x="1480" y="380" />
      </bpmndi:BPMNEdge>
      <bpmndi:BPMNEdge id="Flow_0ttmpi0_di" bpmnElement="Flow_0ttmpi0">
        <di:waypoint x="2680" y="380" />
        <di:waypoint x="2730" y="380" />
      </bpmndi:BPMNEdge>
      <bpmndi:BPMNEdge id="Flow_15ti8ru_di" bpmnElement="Flow_15ti8ru">
        <di:waypoint x="2560" y="380" />
        <di:waypoint x="2580" y="380" />
      </bpmndi:BPMNEdge>
      <bpmndi:BPMNEdge id="Flow_1u4sa29_di" bpmnElement="Flow_1u4sa29">
        <di:waypoint x="2190" y="380" />
        <di:waypoint x="2200" y="380" />
      </bpmndi:BPMNEdge>
      <bpmndi:BPMNEdge id="Flow_0jobsq4_di" bpmnElement="Flow_0jobsq4" bioc:stroke="#000000" color:border-color="#000000">
        <di:waypoint x="1915" y="380" />
        <di:waypoint x="1950" y="380" />
        <bpmndi:BPMNLabel>
          <dc:Bounds x="1923" y="362" width="13" height="14" />
        </bpmndi:BPMNLabel>
      </bpmndi:BPMNEdge>
      <bpmndi:BPMNEdge id="Flow_062y8jk_di" bpmnElement="Flow_062y8jk" bioc:stroke="#000000" color:border-color="#000000">
        <di:waypoint x="1890" y="405" />
        <di:waypoint x="1890" y="450" />
        <di:waypoint x="1530" y="450" />
        <di:waypoint x="1530" y="420" />
        <bpmndi:BPMNLabel>
          <dc:Bounds x="1823" y="432" width="21" height="14" />
        </bpmndi:BPMNLabel>
      </bpmndi:BPMNEdge>
      <bpmndi:BPMNEdge id="Flow_1kjvxid_di" bpmnElement="Flow_1kjvxid">
        <di:waypoint x="248" y="380" />
        <di:waypoint x="270" y="380" />
      </bpmndi:BPMNEdge>
      <bpmndi:BPMNShape id="_BPMNShape_StartEvent_2" bpmnElement="StartEvent_1">
        <dc:Bounds x="212" y="362" width="36" height="36" />
        <bpmndi:BPMNLabel>
          <dc:Bounds x="201" y="405" width="59" height="40" />
        </bpmndi:BPMNLabel>
      </bpmndi:BPMNShape>
      <bpmndi:BPMNShape id="Activity_09ohcsq_di" bpmnElement="Activity_0bkealj">
        <dc:Bounds x="690" y="340" width="100" height="80" />
      </bpmndi:BPMNShape>
      <bpmndi:BPMNShape id="Gateway_0bqx4qv_di" bpmnElement="Gateway_0tzvt9v">
        <dc:Bounds x="615" y="355" width="50" height="50" />
      </bpmndi:BPMNShape>
      <bpmndi:BPMNShape id="Activity_0fxwbso_di" bpmnElement="Activity_0fxwbso">
        <dc:Bounds x="480" y="340" width="100" height="80" />
      </bpmndi:BPMNShape>
      <bpmndi:BPMNShape id="Activity_0grywz0_di" bpmnElement="Activity_0grywz0">
        <dc:Bounds x="480" y="440" width="100" height="80" />
      </bpmndi:BPMNShape>
      <bpmndi:BPMNShape id="Activity_017iqx5_di" bpmnElement="Activity_017iqx5">
        <dc:Bounds x="530" y="250" width="100" height="80" />
      </bpmndi:BPMNShape>
      <bpmndi:BPMNShape id="Activity_16vpuhy_di" bpmnElement="Activity_16vpuhy">
        <dc:Bounds x="420" y="250" width="100" height="80" />
      </bpmndi:BPMNShape>
      <bpmndi:BPMNShape id="Activity_13icmu1_di" bpmnElement="Activity_13icmu1">
        <dc:Bounds x="270" y="340" width="100" height="80" />
      </bpmndi:BPMNShape>
      <bpmndi:BPMNShape id="Gateway_1m3wjn8_di" bpmnElement="Gateway_03jgpfx">
        <dc:Bounds x="375" y="355" width="50" height="50" />
      </bpmndi:BPMNShape>
      <bpmndi:BPMNShape id="Activity_1ut09mg_di" bpmnElement="Activity_1ut09mg">
        <dc:Bounds x="480" y="535" width="100" height="80" />
      </bpmndi:BPMNShape>
      <bpmndi:BPMNShape id="Activity_0s0z7jt_di" bpmnElement="Activity_0s0z7jt" bioc:stroke="#000000" bioc:fill="#ffffff" color:background-color="#ffffff" color:border-color="#000000">
        <dc:Bounds x="950" y="340" width="100" height="80" />
      </bpmndi:BPMNShape>
      <bpmndi:BPMNShape id="Activity_1v4yshp_di" bpmnElement="Activity_1v4yshp" bioc:stroke="black" bioc:fill="white">
        <dc:Bounds x="1070" y="340" width="100" height="80" />
      </bpmndi:BPMNShape>
      <bpmndi:BPMNShape id="Activity_1c080tt_di" bpmnElement="Activity_17ccmxp">
        <dc:Bounds x="1350" y="340" width="100" height="80" />
      </bpmndi:BPMNShape>
      <bpmndi:BPMNShape id="Activity_08i2zn8_di" bpmnElement="Activity_08i2zn8" bioc:stroke="#000000" bioc:fill="#ffffff" color:background-color="#ffffff" color:border-color="#000000">
        <dc:Bounds x="1610" y="340" width="100" height="80" />
      </bpmndi:BPMNShape>
      <bpmndi:BPMNShape id="Activity_1l07p79_di" bpmnElement="Activity_1btxy4y">
        <dc:Bounds x="1480" y="340" width="100" height="80" />
      </bpmndi:BPMNShape>
      <bpmndi:BPMNShape id="Activity_1jk0div_di" bpmnElement="Activity_1jk0div">
        <dc:Bounds x="1220" y="340" width="100" height="80" />
      </bpmndi:BPMNShape>
      <bpmndi:BPMNShape id="Gateway_1xdi8wj_di" bpmnElement="Gateway_1xdi8wj" isMarkerVisible="true">
        <dc:Bounds x="1865" y="355" width="50" height="50" />
        <bpmndi:BPMNLabel>
          <dc:Bounds x="1867" y="331" width="46" height="14" />
        </bpmndi:BPMNLabel>
      </bpmndi:BPMNShape>
      <bpmndi:BPMNShape id="Activity_1qjuwk1_di" bpmnElement="Activity_0qhhodi">
        <dc:Bounds x="2090" y="340" width="100" height="80" />
      </bpmndi:BPMNShape>
      <bpmndi:BPMNShape id="Activity_1mdobhc_di" bpmnElement="Activity_171qdm8">
        <dc:Bounds x="2200" y="340" width="100" height="80" />
      </bpmndi:BPMNShape>
      <bpmndi:BPMNShape id="Activity_0c29dnp_di" bpmnElement="Activity_0c29dnp">
        <dc:Bounds x="1950" y="340" width="100" height="80" />
      </bpmndi:BPMNShape>
      <bpmndi:BPMNShape id="Activity_1idplgj_di" bpmnElement="Activity_1idplgj">
        <dc:Bounds x="2320" y="340" width="100" height="80" />
      </bpmndi:BPMNShape>
      <bpmndi:BPMNShape id="Activity_0j6tegp_di" bpmnElement="Activity_0p6s81e">
        <dc:Bounds x="2580" y="340" width="100" height="80" />
      </bpmndi:BPMNShape>
      <bpmndi:BPMNShape id="Activity_1a2o7x7_di" bpmnElement="Activity_1p31jwi">
        <dc:Bounds x="2730" y="340" width="100" height="80" />
      </bpmndi:BPMNShape>
      <bpmndi:BPMNShape id="Activity_0cs6pq4_di" bpmnElement="Activity_1kdm517">
        <dc:Bounds x="2460" y="340" width="100" height="80" />
      </bpmndi:BPMNShape>
      <bpmndi:BPMNShape id="Activity_0v3dnsk_di" bpmnElement="Activity_0v3dnsk" isExpanded="true">
        <dc:Bounds x="2740" y="505" width="380" height="140" />
      </bpmndi:BPMNShape>
      <bpmndi:BPMNEdge id="Flow_0sw8gv9_di" bpmnElement="Flow_0sw8gv9">
        <di:waypoint x="2811" y="577" />
        <di:waypoint x="2861" y="577" />
      </bpmndi:BPMNEdge>
      <bpmndi:BPMNEdge id="Flow_1dv655f_di" bpmnElement="Flow_1dv655f">
        <di:waypoint x="2961" y="577" />
        <di:waypoint x="3002" y="577" />
      </bpmndi:BPMNEdge>
      <bpmndi:BPMNShape id="Activity_0kzkn15_di" bpmnElement="Activity_0kzkn15">
        <dc:Bounds x="2861" y="537" width="100" height="80" />
      </bpmndi:BPMNShape>
      <bpmndi:BPMNShape id="Event_00viiiy_di" bpmnElement="Event_00viiiy" bioc:stroke="#000" bioc:fill="#fff">
        <dc:Bounds x="2775" y="559" width="36" height="36" />
        <bpmndi:BPMNLabel>
          <dc:Bounds x="2763" y="602" width="60" height="27" />
        </bpmndi:BPMNLabel>
      </bpmndi:BPMNShape>
      <bpmndi:BPMNShape id="Event_1t8hxd8_di" bpmnElement="Event_1t8hxd8" bioc:stroke="#000" bioc:fill="#fff">
        <dc:Bounds x="3002" y="559" width="36" height="36" />
        <bpmndi:BPMNLabel>
          <dc:Bounds x="2982" y="602" width="79" height="14" />
        </bpmndi:BPMNLabel>
      </bpmndi:BPMNShape>
      <bpmndi:BPMNShape id="Activity_1o599km_di" bpmnElement="Activity_1o599km">
        <dc:Bounds x="1730" y="340" width="100" height="80" />
      </bpmndi:BPMNShape>
      <bpmndi:BPMNShape id="Activity_0m848pc_di" bpmnElement="Activity_0m848pc">
        <dc:Bounds x="800" y="340" width="100" height="80" />
      </bpmndi:BPMNShape>
      <bpmndi:BPMNShape id="Activity_0xy0pe7_di" bpmnElement="Activity_0xy0pe7" isExpanded="true">
        <dc:Bounds x="2740" y="120" width="430" height="150" />
      </bpmndi:BPMNShape>
      <bpmndi:BPMNEdge id="Flow_1mbl4qw_di" bpmnElement="Flow_1mbl4qw">
        <di:waypoint x="3070" y="202" />
        <di:waypoint x="3102" y="202" />
      </bpmndi:BPMNEdge>
      <bpmndi:BPMNEdge id="Flow_1k932lk_di" bpmnElement="Flow_1k932lk">
        <di:waypoint x="2816" y="202" />
        <di:waypoint x="2840" y="202" />
      </bpmndi:BPMNEdge>
      <bpmndi:BPMNEdge id="Flow_0kb0k6s_di" bpmnElement="Flow_0kb0k6s">
        <di:waypoint x="2940" y="202" />
        <di:waypoint x="2970" y="202" />
      </bpmndi:BPMNEdge>
      <bpmndi:BPMNShape id="Activity_1qh4p7f_di" bpmnElement="Activity_1qh4p7f">
        <dc:Bounds x="2970" y="162" width="100" height="80" />
      </bpmndi:BPMNShape>
      <bpmndi:BPMNShape id="Activity_1lveufy_di" bpmnElement="Activity_1lveufy">
        <dc:Bounds x="2840" y="162" width="100" height="80" />
      </bpmndi:BPMNShape>
      <bpmndi:BPMNShape id="Event_1rr3qjp_di" bpmnElement="Event_1rr3qjp">
        <dc:Bounds x="3102" y="184" width="36" height="36" />
        <bpmndi:BPMNLabel>
          <dc:Bounds x="3081" y="227" width="78" height="14" />
        </bpmndi:BPMNLabel>
      </bpmndi:BPMNShape>
      <bpmndi:BPMNShape id="Event_1dxbiyp_di" bpmnElement="Event_1r89eoq">
        <dc:Bounds x="2780" y="184" width="36" height="36" />
        <bpmndi:BPMNLabel>
          <dc:Bounds x="2766" y="227" width="70" height="14" />
        </bpmndi:BPMNLabel>
      </bpmndi:BPMNShape>
      <bpmndi:BPMNShape id="Activity_0sxjbys_di" bpmnElement="Activity_0sxjbys" bioc:stroke="#fb8c00" bioc:fill="#ffe0b2" color:background-color="#ffe0b2" color:border-color="#fb8c00">
        <dc:Bounds x="2970" y="410" width="100" height="80" />
      </bpmndi:BPMNShape>
      <bpmndi:BPMNShape id="Event_1uivw50_di" bpmnElement="Event_0z0qrws" bioc:stroke="#000000" bioc:fill="#ffffff" color:background-color="#ffffff" color:border-color="#000000">
        <dc:Bounds x="3122" y="362" width="36" height="36" />
        <bpmndi:BPMNLabel>
          <dc:Bounds x="3103" y="405" width="74" height="40" />
        </bpmndi:BPMNLabel>
      </bpmndi:BPMNShape>
      <bpmndi:BPMNShape id="TextAnnotation_0k5q26p_di" bpmnElement="TextAnnotation_0k5q26p">
        <dc:Bounds x="2840" y="423" width="100" height="54" />
      </bpmndi:BPMNShape>
      <bpmndi:BPMNEdge id="Association_1q343ai_di" bpmnElement="Association_1q343ai">
        <di:waypoint x="2970" y="445" />
        <di:waypoint x="2940" y="443" />
      </bpmndi:BPMNEdge>
      <bpmndi:BPMNShape id="Group_0fltwtf_di" bpmnElement="Group_0fltwtf">
        <dc:Bounds x="930" y="240" width="270" height="230" />
        <bpmndi:BPMNLabel>
          <dc:Bounds x="1028" y="247" width="74" height="27" />
        </bpmndi:BPMNLabel>
      </bpmndi:BPMNShape>
      <bpmndi:BPMNShape id="Group_1225bi1_di" bpmnElement="Group_1225bi1">
        <dc:Bounds x="1210" y="240" width="850" height="230" />
        <bpmndi:BPMNLabel>
          <dc:Bounds x="1573" y="247" width="70" height="14" />
        </bpmndi:BPMNLabel>
      </bpmndi:BPMNShape>
      <bpmndi:BPMNShape id="Group_06zq0hp_di" bpmnElement="Group_06zq0hp">
        <dc:Bounds x="2070" y="240" width="360" height="230" />
        <bpmndi:BPMNLabel>
          <dc:Bounds x="2224" y="247" width="52" height="27" />
        </bpmndi:BPMNLabel>
      </bpmndi:BPMNShape>
      <bpmndi:BPMNShape id="Group_0jba4vp_di" bpmnElement="Group_0jba4vp">
        <dc:Bounds x="2440" y="240" width="270" height="230" />
        <bpmndi:BPMNLabel>
          <dc:Bounds x="2530" y="247" width="89" height="14" />
        </bpmndi:BPMNLabel>
      </bpmndi:BPMNShape>
      <bpmndi:BPMNShape id="Group_0zqfiyr_di" bpmnElement="Group_0zqfiyr">
        <dc:Bounds x="670" y="240" width="250" height="230" />
        <bpmndi:BPMNLabel>
          <dc:Bounds x="766" y="247" width="58" height="27" />
        </bpmndi:BPMNLabel>
      </bpmndi:BPMNShape>
    </bpmndi:BPMNPlane>
  </bpmndi:BPMNDiagram>
</bpmn:definitions>
"""
