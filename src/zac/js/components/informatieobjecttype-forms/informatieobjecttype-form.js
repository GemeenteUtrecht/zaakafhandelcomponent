import React, {useState, useEffect} from 'react';
import PropTypes from 'prop-types';
import {FormSet} from './formset';
import {Select} from '../forms/Select';
import {CheckboxInput, HiddenInput} from "../forms/Inputs";
import {get} from "../../utils/fetch";


class InformatieobjecttypePermissionForm extends React.Component {
    constructor(props) {
        super(props);

        const formData = this.props.data;

        this.state = {
            selected: formData.selected,
            max_va: formData.max_va,
            catalogus: formData.catalogus,
            omschrijving: formData.omschrijving,
            id: formData.id
        };

        this.onCheckChange = this.onCheckChange.bind(this);
        this.onVAChange = this.onVAChange.bind(this);
    }

    onCheckChange(event) {
        this.setState(state => ({selected: !state.selected}));
    }

    onVAChange(event) {
        this.setState({max_va: event.target.value});
    }

    render() {
        return (
            <div className="form__field-group">
                <HiddenInput name='omschrijving' id='id_omschrijving' value={ this.state.omschrijving } />
                <HiddenInput name='id' id='id_id' value={ this.state.id } />
                <HiddenInput name='catalogus' id='id_catalogus' value={ this.state.catalogus } />
                <CheckboxInput
                    name='selected'
                    id={'id_selected'}
                    checked={this.state.selected}
                    initial={this.state.selected}
                    value={this.state.selected}
                    onChange={this.onCheckChange}
                />
                <label>{this.state.omschrijving}</label>
                <Select
                    name={'max_va'}
                    id={'id_max_va'}
                    choices={[
                        ['openbaar', 'Openbaar'],
                        ['beperkt_openbaar', 'Beperkt openbaar'],
                        ['intern', 'Intern'],
                        ['zaakvertrouwelijk', 'Zaakvertrouwelijk'],
                        ['vertrouwelijk', 'Vertrouwelijk'],
                        ['confidentieel', 'Confidentieel'],
                        ['geheim', 'Geheim'],
                        ['zeer_geheim', 'Zeer geheim'],
                    ]}
                    value={this.state.max_va}
                    onChange={this.onVAChange}
                />
                <CheckboxInput
                    name="DELETE"
                    checked={!this.state.selected}
                    value="true"
                    style={{display: 'none'}}
                />
            </div>
        );
    }
}


const InformatieobjecttypeDelete = ({index, data}) => {

    const getMaxVADisplay = (max_va) => {
        const choices = {
            'openbaar': 'Openbaar',
            'beperkt_openbaar': 'Beperkt openbaar',
            'intern': 'Intern',
            'zaakvertrouwelijk': 'Zaakvertrouwelijk',
            'vertrouwelijk': 'Vertrouwelijk',
            'confidentieel': 'Confidentieel',
            'geheim': 'Geheim',
            'zeer_geheim': 'Zeer geheim',
        };

        return choices[max_va];
    };

    return (
        <div className="form__field-group">
            <HiddenInput name='omschrijving' id='id_omschrijving' value={ data.omschrijving } />
            <HiddenInput name='id' id='id_id' value={ data.id } />
            <HiddenInput name='catalogus' id='id_catalogus' value={ data.catalogus } />
            <HiddenInput name='DELETE' id='id_DELETE' value={ true } />
            <li key={"permission_to_delete" + index}>{data.omschrijving} ({getMaxVADisplay(data.max_va)})</li>
        </div>
    );
};


const InformatieobjecttypeForm = ({configuration, catalogChoices, existingFormData}) => {

    var initialCatalogus = existingFormData.length > 0 ? existingFormData[0].catalogus : '';

    const [currentCatalog, setCurrentCatalog] = useState(initialCatalogus);
    const [emptyFormData, setEmptyFormData] = useState([]);
    const [formData, setFormData] = useState(existingFormData);
    const [dataToDelete, setDataToDelete] = useState([]);
    const [informatieobjecttypeErrors, setInformatieobjecttypeErrors] = useState("");

    const onCatalogChange = (event) => {
        if (formData.length > 0){
            setDataToDelete(formData);
            setFormData([]);
        } else if (dataToDelete.length > 0) {
            if (dataToDelete[0].catalogus === event.target.value){
                setFormData(dataToDelete);
                setDataToDelete([]);
            }
        }

        setCurrentCatalog(event.target.value);
    };

    const fetchInformatieobjecttypen = () => {
        get(
            "/accounts/api/informatieobjecttypen",
            {catalogus: currentCatalog}
        ).then(
            result => {
                if (formData.length > 0) {
                    //TODO Improve
                    var additionalInformatieobjecttypen = [];
                    for (var results_counter = 0; results_counter < result.emptyFormData.length; results_counter++) {
                        var inExistingData = false;
                        for (var existing_counter = 0; existing_counter < formData.length; existing_counter++) {
                            if (
                                formData[existing_counter].omschrijving === result.emptyFormData[results_counter].omschrijving &&
                                formData[existing_counter].catalogus === result.emptyFormData[results_counter].catalogus
                            ) {
                                inExistingData = true;
                                break;
                            }
                        }
                        if (!inExistingData) {
                            additionalInformatieobjecttypen.push(result.emptyFormData[results_counter]);
                        }
                    }
                    setEmptyFormData(additionalInformatieobjecttypen);
                } else {
                    setEmptyFormData(result.emptyFormData);
                }
            },
            error => {
                setInformatieobjecttypeErrors(error);
            }
        );
    };

    useEffect(() => {
        if (currentCatalog !== '') {
            fetchInformatieobjecttypen();
        } else {
            setFormData([]);
            setEmptyFormData([]);
        }
    }, [currentCatalog]);

    return (
        <React.Fragment>
             <Select
                name='informatieobjecttype_catalogus'
                id='id_informatieobjecttype_catalogus'
                label='Catalogus'
                helpText='Informatieobjecttypencatalogus waarin de informatieobjecttypen voorkomen'
                choices={catalogChoices}
                value={currentCatalog}
                onChange={onCatalogChange}
            />
            <FormSet
                configuration={configuration}
                renderForm={InformatieobjecttypePermissionForm}
                deleteForm={InformatieobjecttypeDelete}
                formData={formData}
                emptyFormData={emptyFormData}
                dataToDelete={dataToDelete}
            />
        </React.Fragment>
    );
};


InformatieobjecttypeForm.propTypes = {
    configuration: PropTypes.shape({
        prefix: PropTypes.string.isRequired,
        initial: PropTypes.number.isRequired,
        extra: PropTypes.number.isRequired,
        minNum: PropTypes.number.isRequired,
        maxNum: PropTypes.number.isRequired,
    }).isRequired,
    renderForm: PropTypes.func.isRequired, // a render prop
    catalogChoices: PropTypes.arrayOf(PropTypes.array).isRequired,
    existingFormData: PropTypes.arrayOf(PropTypes.shape({
        id: PropTypes.string,
        catalog: PropTypes.string,
        omschrijving: PropTypes.string,
        max_va: PropTypes.string,
        selected: PropTypes.string,
    }))
};

InformatieobjecttypePermissionForm.propTypes = {
    index: PropTypes.number,
    data: PropTypes.arrayOf(PropTypes.shape({
        id: PropTypes.string,
        catalog: PropTypes.string,
        omschrijving: PropTypes.string,
        max_va: PropTypes.string,
        selected: PropTypes.string,
    }))
};

export { InformatieobjecttypePermissionForm, InformatieobjecttypeForm, InformatieobjecttypeDelete };
