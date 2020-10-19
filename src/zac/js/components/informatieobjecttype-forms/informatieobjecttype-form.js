import React from 'react';
import PropTypes from 'prop-types';
import {FormSet} from './formset';
import {Select, FormSetSelect} from '../forms/Select';
import {CheckboxInput, HiddenInput} from "../forms/Inputs";



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
                <FormSetSelect
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
            </div>
        );
    }
}


class InformatieobjecttypeForm extends React.Component {
    constructor(props) {
        super(props);

        this.state = {
            currentCatalog: '',
            displayFormset: false,
            existingFormData: [],
            emptyFormData: [],
            errors: "",
        };

        this.onCatalogChange = this.onCatalogChange.bind(this);
        this.fetchInformatieobjecttypen = this.fetchInformatieobjecttypen.bind(this);
    }

    componentDidMount() {
        if (this.props.existingFormData.length > 0) {
            this.fetchInformatieobjecttypen(this.props.existingFormData[0].catalogus);

            this.setState({
                currentCatalog: this.props.existingFormData[0].catalogus,
                displayFormset: true,
                existingFormData: this.props.existingFormData,
            })
        }
    }

    onCatalogChange(event) {
        this.setState({
            currentCatalog: event.target.value,
            displayFormset: event.target.value !== '',
            existingFormData: [],
        });

        // Fetch the informatieobjecttypen
        if (event.target.value !== '') {
            this.fetchInformatieobjecttypen(event.target.value);
        }
    }

    fetchInformatieobjecttypen (catalogUrl) {
        const apiURL = "/accounts/permission-sets/informatieobjecttypes?catalogus=" + catalogUrl;
        window.fetch(apiURL).then(
            response => response.json()
        ).then(
            result => {
                if (this.state.existingFormData.length > 0) {
                    //TODO Improve
                    var additionalInformatieobjecttypen = [];
                    for (var results_counter = 0; results_counter < result.emptyFormData.length; results_counter++) {
                        var inExistingData = false;
                        for (var existing_counter = 0; existing_counter < this.state.existingFormData.length; existing_counter++) {
                            if (
                                this.state.existingFormData[existing_counter].omschrijving === result.emptyFormData[results_counter].omschrijving &&
                                this.state.existingFormData[existing_counter].catalogus === result.emptyFormData[results_counter].catalogus
                            ) {
                                inExistingData = true;
                                break;
                            }
                        }
                        if (!inExistingData) {
                            additionalInformatieobjecttypen.push(result.emptyFormData[results_counter]);
                        }
                    }
                    this.setState({emptyFormData: additionalInformatieobjecttypen});
                } else {
                    this.setState({emptyFormData: result.emptyFormData});
                }
            },
            error => {
                this.setState({errors: error});
            }
        );
    }

    render() {
        return (
            <React.Fragment>
                 <Select
                    name='informatieobjecttype_catalogus'
                    id='id_informatieobjecttype_catalogus'
                    label='Catalogus'
                    helpText='Select the catalog containing the desired informatieobjecttype'
                    choices={this.props.catalogChoices}
                    value={this.state.currentCatalog}
                    onChange={this.onCatalogChange}
                />
                <FormSet
                    configuration={this.props.configuration}
                    renderForm={this.props.renderForm}
                    formData={this.state.existingFormData}
                    emptyFormData={this.state.emptyFormData}
                />
            </React.Fragment>
        );
    }
}

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

export { InformatieobjecttypeForm, InformatieobjecttypePermissionForm };
